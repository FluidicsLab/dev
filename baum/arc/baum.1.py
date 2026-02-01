import neoapi
import os, time, sys
import cv2, base64

import pandas as pd
import numpy as np

import mqttools, json, asyncio

import threading
from threading import Event, Lock

import logging
logging.basicConfig(
    level=logging.ERROR,
    # format='%(levelname)-8s %(asctime)s %(threadName)-15s %(message)s'
    format='%(message)s'
    )

baumLogger = logging.getLogger(__name__)
baumLogger.setLevel(logging.DEBUG)
baumLogger.name = "__baumLogger__"
def loggingFilter(record: logging.Filter): return True
baumLogger.addFilter(loggingFilter)

WRK_FOLDER = r"C:\Develop\py\FluidicsLab\Drafts\baum\data"
WRK_DELAY = 1.

IMG_FORMAT = "Mono8"
IMG_QUALITY = 100
IMG_SHAPE_EMPTY = (0,0,1)

IMG_THUMB_SCALE = (0.1,0.1)
IMG_THUMB_DEFAULT = r"media\TestCard_PM5544.png"

PUB_HOST = 'localhost'
PUB_PORT = 10009
PUB_TOPIC = '/hot/ecat/baum/out'
PUB_ENABLED = 1
PUB_DELAY = 1.
PUB_STOP_ON_ERROR = 0
PUB_DEBUG = 0

PUB_STORE_FOLDER = r"C:\Develop\py\FluidicsLab\Drafts\baum\data"

SUB_HOST = 'localhost'
SUB_PORT = 10009
SUB_TOPIC = '/hot/ecat/baum/in'
SUB_ENABLED = 1
SUB_DELAY = 0.1
SUB_STOP_ON_ERROR = 0
SUB_DEBUG = 1

class baumNotConnected(Exception):
    pass


class baumNoContent(Exception):
    pass

class baumFeatureAccess(neoapi.neoapi.FeatureAccessException):
    pass


class baumTrace(neoapi.NeoTrace):
    
    def __init__(self):
        super().__init__()

        self.EnableLogCallback(self.callback)
        self.SetSeverity(neoapi.NeoTraceSeverity_Info)

    @staticmethod
    def parse(message:str):        
        columns = ['timestamp','address','type','unkown1','user','device','command','message']
        return dict(zip(columns, [s.strip() for s in message.split(";")]))

    def callback(self, message:str):
        items = baumTrace.parse(message)
        if "user" == items["user"]:
            baumLogger.debug(message)

    def disable(self):
        self.DisableLogCallback()

    def info(self, *args):
        for arg in args: 
            self.Info(str(arg))

    def error(self, *args):
        for arg in args: 
            self.Error(str(arg))


class baumDevice():

    _trace: baumTrace = None
    def _get_trace(self):
        if self._trace is None:
            self._trace = baumTrace()
        return self._trace
    Trace = property(fget=_get_trace)

    _name:str = None
    def _set_name(self, value): 
        self._name = value
    def _get_name(self): 
        return self._name
    Name = property(fset=_set_name,fget=_get_name)

    _camera: neoapi.Cam = None
    def _get_camera(self):
        if self._camera is None: 
            self.connect()
            self.setup()              
        return self._camera    
    Camera:neoapi.Cam = property(fget=_get_camera)

    def _get_connected(self):
        return self._name is not None and self._camera is not None and self._camera.IsConnected()
    Connected:bool = property(fget=_get_connected)

    def _get_id(self):
        return self._raw.GetImageID() if self.Available else '99'
    Id: str = property(fget=_get_id)

    def _set_step(self, value):
        self.Camera.f.FocusStepper.value = value
    def _get_step(self):
        return self.Camera.f.FocusStepper.value if self.Connected else None
    Step = property(fset=_set_step, fget=_get_step)

    _raw: neoapi.Image = None
    def _set_raw(self, value): 
        self._raw = value
        self.reset()
    def _get_raw(self): 
        return self._raw
    Raw: neoapi.Image = property(fset=_set_raw, fget=_get_raw)

    _image = None
    def _get_image(self):
        if self.Raw is None:
            return None
        if self._image is None:
            self._image = self.Raw.Convert(IMG_FORMAT)
            self._image = self._image.GetNPArray().copy()
            self._image = np.flipud(self._image)
            if len(self._image) == 0:
                self._image = None        
        return self._image
    Image = property(fget=_get_image)

    _shape = IMG_SHAPE_EMPTY
    def _get_shape(self):
        if self._shape == IMG_SHAPE_EMPTY:
            image = self.Image
            self._shape = image.shape if image is not None else IMG_SHAPE_EMPTY
    Shape = property(fget=_get_shape)

    def _get_scale(self):
        return IMG_THUMB_SCALE
    Scale = property(fget=_get_scale)

    def _get_available(self):
        return self.Raw is not None
    Available:bool = property(fget=_get_available)

    def _set_step(self, value):
         self.Camera.f.FocusStepper.value = int(value)
    def _get_step(self):
        return self.Camera.f.FocusStepper.value
    Step: int = property(fset=_set_step, fget=_get_step)

    def _get_blur(self):
        image = self.Image
        if image is not None:
            return cv2.Laplacian(image, cv2.CV_64F).var()
        return 0
    Blur = property(fget=_get_blur)

    _thumb = None
    def _get_thumb(self):
        if self._thumb is None:
            image = self.Image        
            if image is not None:
                self._thumb = cv2.resize(image,(0,0),
                                         fx=IMG_THUMB_SCALE[0],
                                         fy=IMG_THUMB_SCALE[1])
            else:
                self._thumb = cv2.imread(os.path.join(os.getcwd(), IMG_THUMB_DEFAULT))
        return self._thumb
    Thumb = property(fget=_get_thumb)

    _base64 = None
    def _get_base64(self):
        if self._base64 is None:
            thumb = self.Thumb        
            if thumb is not None:
                self._base64 = base64.b64encode(cv2.imencode('.jpg', thumb)[1]).decode()
        return self._base64
    Base64 = property(fget=_get_base64)

    def __init__(self) -> None:
        self._trace = baumTrace()

    def __del__(self):
        self.Trace.disable()

    def connect(self):
                
        models = neoapi.CamInfoList.Get()
        models.Refresh()
        
        for model in models:
            if model.IsConnectable():                
                self.Name = model.GetModelName()
                break

        if self.Name is not None:
            self._camera = neoapi.Cam()
            self.Camera.Connect(self.Name)
        
    def disconnect(self):
        if self.Connected:
            self.Camera.Disconnect()

    def reset(self):
        self._image = None
        self._thumb = None
        self._base64 = None
        self._shape = IMG_SHAPE_EMPTY

    def _get_ready(self):
        return self.Camera.f.OpticControllerStatus.value == neoapi.OpticControllerStatus_Ready \
            and self.Camera.f.FocusStatus.value == neoapi.FocusStatus_Ready
    Ready: bool = property(fget=_get_ready)

    def _get_status(self):
        return dict(
            connected=self.Connected,
            ready=self.Ready
        )
    Status = property(fget=_get_status)

    _region = None

    def _get_region(self):
        if self._region is None:
            self._region =  dict(
                x=self.Camera.f.OffsetX.value,
                y=self.Camera.f.OffsetY.value,
                width=self.Camera.f.Width.value,
                height=self.Camera.f.Height.value,
                widthMax=self.Camera.f.WidthMax.value,
                heightMax=self.Camera.f.HeightMax.value,
                autoAdjust=self.Camera.GetAdjustFeatureValueMode()
                )
        return self._region
    
    def _set_region(self,value:dict):
        
        if self._region is None:
            self._region = value.copy()
        
        self._region.update(value)

        self.Camera.SetAdjustFeatureValueMode(True)

        try:
            if self._region['x'] + self._region['width'] <= self._region['widthMax']:
                self.Camera.f.Width.value = int(self._region['width'])
                self.Camera.f.OffsetX.value = int(self._region['x'])    
            else:
                self.Camera.f.OffsetX.value = 0
                self.Camera.f.Width.value = int(self._region['width'])
                self.Camera.f.OffsetX.value = int(self._region['x'])    

            if self._region['y'] + self._region['height'] <= self._region['heightMax']:
                self.Camera.f.Height.value = int(self._region['height'])
                self.Camera.f.OffsetY.value = int(self._region['y'])
            else:
                self.Camera.f.OffsetY.value = 0
                self.Camera.f.Height.value = int(self._region['height'])
                self.Camera.f.OffsetY.value = int(self._region['y'])

        except neoapi.FeatureAccessException as ex:
            baumLogger.error(ex)
            baumLogger.error(sys.exc_info())

        self._region = None

    Region = property(fget=_get_region,fset=_set_region)

    def _get_binning(self):
        return (self.Camera.f.BinningHorizontal.value,
                self.Camera.f.BinningVertical.value)
    def _set_binning(self,value:int):
        self.Camera.f.BinningHorizontal.Set(value)
        self.Camera.f.BinningVertical.Set(value)
    Binning = property(fget=_get_binning,fset=_set_binning)

    def _get_binningMode(self):
        return (self.Camera.f.BinningHorizontalMode.value,
                self.Camera.f.BinningVerticalMode.value)
    def _set_binningMode(self,value:int):
        self.Camera.f.BinningHorizontalMode.SetInt(value)
        self.Camera.f.BinningVerticalMode.SetInt(value)
    """
    Sets the mode to use to combine photo-sensitive cells together when 
    Binning{Horizontal,Vertical} is used.    
    0: Average - The response from the combined cells will be averaged, 
                 resulting in increased signal/noise ratio.
    1: Sum - The response from the combined cells will be added, 
             resulting in increased sensitivity.
    """        
    BinningMode = property(fget=_get_binningMode, fset=_set_binningMode)

    def _get_decimation(self):
        return (self.Camera.f.DecimationHorizontal.value,
                self.Camera.f.DecimationVertical.value)
    def _set_decimation(self, value):        
        self.Camera.f.DecimationHorizontal.value = value
        self.Camera.f.DecimationVertical.value = value
    Decimation = property(fget=_get_decimation, fset=_set_decimation)

    def _get_decimationMode(self):
        return (self.Camera.f.DecimationHorizontalMode.value,
                self.Camera.f.DecimationVerticalMode.value)
    def _set_decimationMode(self, value:int):        
        self.Camera.f.DecimationHorizontalMode.SetInt(value)
        self.Camera.f.DecimationVerticalMode.SetInt(value)
    """
    Sets the mode used to reduce the resolution 
    when Decimation{Horizontal,Vertical} is used.
    0: Average - The values of a group of N adjacent pixels are averaged.
    1: Discard - The value of every Nth pixel is kept, others are discarded.
    """
    DecimationMode = property(fget=_get_decimationMode, fset=_set_decimationMode)

    def _get_sharpening(self):
        return dict(
            #enabled=self.Camera.f.SharpeningEnable.value,
            mode=self.Camera.f.SharpeningMode.value,
            factor=self.Camera.f.SharpeningFactor.value,
            threshold=self.Camera.f.SharpeningSensitivityThreshold.value
        )

    Sharpening = property(fget=_get_sharpening)

    def setup(self):

        try:

            self.Camera.f.ExposureAuto.value = neoapi.ExposureAuto_Off            
            self.Camera.f.ExposureTime.value = 4000. # 8000: 1.5v
            self.Camera.f.Gain.value = 1.

            #self.Camera.f.OpticControllerDisconnect.Execute()
            #self.Camera.f.OpticControllerInitialize.Execute()
            
            #self.Camera.f.TriggerMode.value = neoapi.TriggerMode_On
            #self.Camera.f.TriggerSoftware.Execute()

            self.Decimation = 2

            baumLogger.debug(f"{self.Decimation} {self.DecimationMode}")
            
            region = self.Region
            
            region['x'] = 0
            region['width'] = region['widthMax']

            region['y'] = 0
            region['height'] = region['heightMax']
            
            self.Region = region

            baumLogger.debug(self.Region)

            rgn_ = [
                self.Camera.f.RegionMode.value, 
                self.Camera.f.RegionConfigurationMode.value,
                self.Camera.f.RegionAcquisitionMode.value,
                self.Camera.f.RegionTransferMode.value,
                self.Camera.f.RegionSelector.value,
                ]

            baumLogger.debug(f"{','.join([str(v) for v in rgn_])}")

            baumLogger.debug(self.Sharpening)

            time.sleep(2.5)

        except Exception as ex:
            baumLogger.debug(ex)
            return False

        finally:
            return True

    def initialize(self, step:int=0):
        if self.Connected:
            if self.setup():
                self.Step = step
                return self.request()
        return False

    def request(self, step:int=None):
        if self.Connected:
            if step is not None:
                self.Step = step
            self.Raw = self.Camera.GetImage()
        return self.Available
        
    def store(self, filename:str=None):
        image = self.Image
        if image is not None:
            if filename is None:                                    
                filename = os.path.join(PUB_STORE_FOLDER, f"{self.Step}.jpg")                
            return cv2.imwrite(filename, image, [int(cv2.IMWRITE_JPEG_QUALITY), IMG_QUALITY])
        return False

    def info(self):

        if self.Connected:
            self.Trace.info(
                self.Name,
                self.Camera.f.DeviceSerialNumber.value,
                self.Camera.f.ExposureTime.value,
                self.Camera.f.Gain.value,
                self.Camera.f.PixelFormat.value,                
                )
        else:
            self.Trace.error("not connected")
        
        if self.Available:
            self.Trace.info(
                self.Raw.GetImageID(),
                self.Raw.GetTimestamp(), 
                self.Raw.GetSize(), 
                self.Raw.GetPixelFormat()
            )
        else:
            self.Trace.error("no content")


class baumWorker(threading.Thread):

    def _get_stopOnError(self):
        return True
    StopOnError = property(fget=_get_stopOnError)

    _delay = 1.
    def _get_delay(self): return self._delay
    Delay = property(fget=_get_delay)

    _exit = None
    def _get_exit(self): return self._exit
    def _set_exit(self,value): self._exit = value
    Exit = property(fget=_get_exit, fset=_set_exit)

    _device:baumDevice = None
    def _get_device(self): 
        return self._device
    def _set_device(self, value):
        self._device = value
    Device:baumDevice = property(fget=_get_device, fset=_set_device)    

    def _set_running(self, value):
        if not value and self.Exit is not None:
            self.Exit.set()
        if value and self.Exit is None:
            self.Exit = threading.Event()
    def _get_running(self):
        return self.Exit is not None and not self.Exit.is_set()
    Running = property(fset=_set_running,fget=_get_running)

    def _get_enabled(self):
        return self._device is not None and self._device.Connected
    Enabled = property(fget=_get_enabled)    

    def __init__(self, device:baumDevice):
       super().__init__()   
       self.daemon = True
       self.Device = device

    def run(self):
        pass

    def release(self):
        if self.Enabled:
            self.Device = None

    def exit(self):
        if self.Exit is not None:
            self.Exit.set()  

    def wait(self):
        self.Exit.wait(self.Delay)


class baumPublisher(baumWorker):

    _lock:threading.Lock = None
    
    def _get_stopOnError(self):
        return super().StopOnError and PUB_STOP_ON_ERROR
    StopOnError = property(fget=_get_stopOnError)
    
    def _get_enabled(self):
        return super().Enabled and PUB_ENABLED
    Enabled = property(fget=_get_enabled)

    def __init__(self, device: baumDevice):
       super().__init__(device)   
       self._delay = PUB_DELAY
       self._lock = threading.Lock()

    async def publish(self, topic, message, debug=False):
                    
        threading.current_thread().name = self._name
        
        client = mqttools.Client(PUB_HOST, PUB_PORT, connect_delays=[])            
        rc = client.client_id
        try:
            await client._start(resume_session=False)
            client.publish(mqttools.Message(topic, message))            
        except Exception as ex:                        
            baumLogger.error(ex)
            rc = -1             
        finally:
            await client.stop()            
        return rc
    
    class ComplexJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, bytes):
                return obj.decode()
            return json.JSONEncoder.default(self, obj) 

    def run(self):

        self.Running = True
        
        while(self.Running):            
            
            self._lock.acquire()

            try:
                                                
                if self.Enabled:

                    self.Device.request()

                    data:dict = dict(
                        
                        name=self.Device.Name,
                        id=self.Device.Id,
                        
                        step=self.Device.Step,                        
                        blur=self.Device.Blur,

                        image=dict(
                            thumb=self.Device.Base64,
                            shape=self.Device.Shape,
                            scale=self.Device.Scale,
                        ),

                        status=self.Device.Status,

                        decimation=dict(
                            value=self.Device.Decimation,
                            mode=self.Device.DecimationMode
                        ),
                        binning=dict(
                            value=self.Device.Binning,
                            mode=self.Device.BinningMode
                        ),
                        region=self.Device.Region,
                        
                        modified=time.time_ns()
                    )  

                    if PUB_DEBUG:
                        baumLogger.debug(f"{data['id']}: {data['step']} {data['blur']}")
                        baumLogger.debug(f"{data['status']}")

                    message = json.dumps(data, cls=baumPublisher.ComplexJSONEncoder).encode('ascii')
                    asyncio.run( self.publish(PUB_TOPIC, message), debug=True)

            except Exception as ee: 
                baumLogger.error(ee)
                if self.StopOnError:
                    self.Running = False
            finally:  
                self._lock.release()
                
            self.wait()

        self.release()        
        self.Running = False
    
    def release(self):
        if self.Enabled:
            super().release()

    def wait(self):
        self.Exit.wait(self.Delay)


class baumSubscriber(baumWorker):

    def _get_stopOnError(self):
        return super().StopOnError and SUB_STOP_ON_ERROR
    StopOnError = property(fget=_get_stopOnError)
    
    def _get_enabled(self):
        return super().Enabled and SUB_ENABLED
    Enabled = property(fget=_get_enabled)

    def __init__(self, device: baumDevice):
       super().__init__(device)   
       self._delay = SUB_DELAY
       self._lock = threading.Lock()

    def release(self):
        if self.Enabled:
            super().release()

    _event = None

    def run(self):

        self.Running = True

        async def subscribe(topics:list[str], callback):
        
            threading.current_thread().name = self._name
            
            client:mqttools.Client = mqttools.Client(SUB_HOST, SUB_PORT, 
                                                        connect_delays=[],
                                                        subscriptions=topics)
            rc = client.client_id
            
            try:
                await client._start(resume_session=False)
                
                while True:
                    
                    message:mqttools.client.Message = await client.messages.get() 
                
                    if message is not None:

                        message.retain = True

                        data = json.loads(message.message)
                    
                        self._event = asyncio.Event()
                        callback(data)
                        await self._event.wait()

                    if client.messages.empty():
                        break

                client.messages.task_done()

            except Exception as ex:                        
                baumLogger.error(ex)
                rc = -1            
            finally:
                await client.stop()                    
            return rc
        
        while(self.Running):
            
            try:

                if self.Enabled:        

                    rc = asyncio.run(subscribe([SUB_TOPIC], self.callback), 
                                     debug=True)                
                    
                    if -1 == rc and self.StopOnError:
                        self.Running = False

            except Exception as ee: 
                baumLogger.error(ee)
                if self.StopOnError:
                    self.Running = False

            finally:                
                pass

            self.wait()

        self.release()
        self.Running = False

    def callback(self, data):

        if SUB_DEBUG:
            baumLogger.debug('    ' + str(data))
        
        keys = list(data.keys())

        if 'connect' in keys:
            if not self.Device.Connected:
                self.Device.connect()

        if 'disconnect' in keys:
            if self.Device.Connected:
                self.Device.disconnect()

        if 'step' in keys:
            if self.Device.Connected:                
                self.Device.request(step=data['step'])

        if 'store' in keys:
            if self.Device.Connected:
                self.Device.store()
        
        if 'command' in keys:
            if 'release' == data['command']:
                self.Running = False

        asyncio.get_running_loop().call_soon_threadsafe(self._event.set)

    def wait(self):
        self.Exit.wait(self.Delay)


class baumControl(threading.Thread):

    _exit = None

    _delay = WRK_DELAY 
    _folder = os.path.join(WRK_FOLDER, "231220-001")

    _name = None
    _lock: Lock = Lock()

    _device = None
    def _get_device(self):
        if self._device is None:
            self._device = baumDevice()
        return self._device
    Device = property(fget=_get_device)

    def __init__(self):

       super().__init__()

       self._exit = Event()
       self.daemon = True

       self._name = self.__class__.__name__

    def run(self):
        
        while(not self._exit.is_set()):

            self._lock.acquire()
            try:

                device: baumDevice = self.Device
                if not device.Connected:
                    device.connect()

                if device.Connected:

                    cfg = [
                        device.Camera.f.ReadOutTime.value
                    ]
                    baumLogger.debug(":".join(f"{c}" for c in cfg))

                    #device.Camera.f.RegionMode.value = neoapi.RegionMode_On
                    #device.Camera.f.RegionSelector.value = neoapi.RegionSelector_Region0

                    cfg = [
                        device.Camera.f.OffsetX.value,
                        device.Camera.f.OffsetY.value,
                        device.Camera.f.Width.value,
                        device.Camera.f.Height.value,
                        device.Camera.f.RegionAcquisitionMode.value,
                        device.Camera.f.RegionConfigurationMode.value,
                        device.Camera.f.RegionMode.value,
                        device.Camera.f.RegionSelector.value
                    ]
                    baumLogger.debug(":".join(f"{c}" for c in cfg))

                    data = []
                    id = '99'

                    device.Step = 0
                    time.sleep(.5)
                    device.request()
                    id = device.Id

                    width = 1
                    start = 0
                    stop = start + 8000
                    for step in range(start, stop, width):

                        device.Step = step
                        #time.sleep(.5)
                        device.request()
                    
                        blur = device.Blur

                        baumLogger.debug(f"{id} {step} {blur:.2f}")

                        data.append([id,step,blur])

                        if self._exit.is_set():
                            break

                    frame = pd.DataFrame(data, columns=['id','step', 'blur'])
                    filename = os.path.join(self._folder,f"{id}.{width}.csv")
                    frame.to_csv(filename, index=False)

                    data = frame.to_numpy()                    
                    for step in [int(data[data[:,2].argmax(),1])]:

                        device.Step = step
                        device.request()

                        filename = os.path.join(self._folder,f"{id}.{width}.{step}.jpg")
                        device.store(filename)

                    self.exit()

                else:
                    raise baumNotConnected("device not connected")

            except Exception as ee:
                baumLogger.debug(ee)

            finally:
                
                if device.Connected:
                    device.disconnect()

                self._lock.release()
        
            self._exit.wait(self._delay)

    def exit(self):
        self._exit.set()  


def main():

    os.system('cls')

    try:
    
        device = baumDevice()
        if not device.Connected:
            device.connect()
        device.initialize(step=4500)        

        pub = baumPublisher(device)
        pub.start()
        
        sub = baumSubscriber(device)
        sub.start()

        input('<Enter>\n')
        
        asyncio.run(pub.publish(SUB_TOPIC,
                                json.dumps(dict(command='release')).encode('ascii')
                                ))
        pub.exit()
        sub.exit()
        
        pub.join()
        sub.join()

    except Exception as ex:
        baumLogger.error(ex)

    finally:

        if device.Connected: 
            device.disconnect()



if __name__ == '__main__':
    main()
