import neoapi

import os, time, sys
import cv2, base64

import pandas as pd
import numpy as np
import math

import datetime
from shapely.geometry import LineString, Point

import mqttools, json, asyncio

import threading
from threading import Event, Lock

from types import SimpleNamespace

from pathlib import Path
import pyexiv2

import psutil

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

WRK_FOLDER = r"C:\Data"
WRK_DELAY = 1.5

WRK_CONFIG_PATH = os.getcwd()

DEV_NO = [0]

DEV_FOCUS_STEP = 0
DEV_EXPOSURE_TIME = 10000 # µs
DEV_GAIN = 1.
DEV_ZOOM = 1.
DEV_CENTER = (.5,.5)
DEV_APERTURE_STEP = 64

DEV_ROTATION = [0,0.5,0.5] # deg,x,y

DEV_FLIP = 99 # 0 vertical, +1 horizontal, -1 both
DEV_BLUR = 0

DEV_PIXEL_FORMAT_BGR8 = 11
DEV_PIXEL_FORMAT_RGB8 = 153
DEV_PIXEL_FORMAT_Mono8 = 136
DEV_PIXEL_FORMAT_BayerRGB = 58

# 0: ActiveNoiseReduction - Sharpening is enabled in active noise reduction mode
# 1: AdaptiveSharpening - Sharpening is enabled in adaptive sharpening mode.
# 2: GlobalSharpening - Sharpening is enabled in global sharpening mode.
# 3: Off - Sharpening is disabled.
DEV_SHARP_MODE = 3
DEV_SHARP_FACTOR = 5
DEV_SHARP_THRESHOLD = 5

# BGR8: 11, Mono8: 136, RGB8: 153, BayerRGB: 58
DEV_PIXEL_FORMAT = DEV_PIXEL_FORMAT_RGB8 
DEV_GAMMA = 1.0

DEV_DECIMATION_MODE = 1
DEV_DECIMATION = 1

# 0: Average - The response from the combined cells will be averaged, resulting in increased signal/noise ratio.
# 1: Sum - The response from the combined cells will be added, resulting in increased sensitivity.
DEV_BINNING_MODE = 0
DEV_BINNING = 2

DEV_DELAY = .2
DEV_REQUEST_TIMEOUT = 1000 # µs
DEV_INIT_TIMEOUT = 2 # s

DEV_XMP = 1

IMG_QUALITY = 100
IMG_SHAPE_EMPTY = (0,0,1)

IMG_THUMB_SCALE = (0.1,0.1)
IMG_THUMB_DEFAULT = r"media\testcard_color.png"
IMG_THUMB_TEXT = "no image data"

PUB_HOST = 'localhost'
PUB_PORT = 10008
PUB_TOPIC = '/hot/ecat/baum/out'
PUB_ENABLED = 1
PUB_DELAY = .1
PUB_STOP_ON_ERROR = 0

PUB_DEBUG = 0

PUB_STORE_FOLDER = r"C:\Data"
PUB_STORE_PREFIX = ""
PUB_STORE_EXTENSION = ".jpg"

PUB_STORE_META_COL = ['source']
PUB_STORE_META_DEL = ";"
PUB_STORE_META_LF = "\n"

SUB_HOST = 'localhost'
SUB_PORT = 10008
SUB_TOPIC = '/hot/ecat/baum/in'
SUB_ENABLED = 1
SUB_DELAY = 0.1
SUB_STOP_ON_ERROR = 0
SUB_DEBUG = 0

OPTIC_STATUS = {
    0: "Busy - The optic controller executes a feature access/command.",
    1: "Error - The optic controller encountered an error.",
    2: "NotConnected - The optic contoller is physically not connected.",
    3: "NotInitialized - The optic controller is not initialized.",
    4: "NotSupported - The optic controller is physically connected but not supported.",
    5: "Ready - The optic controller is ready to use."
}

OPTIC_STATUS_ID = {
    "Busy": 0,
    "Error": 1,
    "NotConnected": 2,
    "NotInitialized": 3,
    "NotSupported": 4,
    "Ready": 5
}

BLUR_DDEPTH = cv2.CV_64F
BLUR_KSIZE = 3

FRAME_ENABLED = 0

FRAME_THRESH_VALUE = 100
FRAME_THRESH_MAX = 200
FRAME_THRESH_TYPE = cv2.THRESH_BINARY_INV

FRAME_POLY_EPSILON = 0.01
FRAME_POLY_LENGTH = 4

FRAME_DILATE_KERNEL = (40,40)
FRAME_DILATE_IT = 1

FRAME_INDEX = -1

FRAME_CONTOUR_ENABLED = 1
FRAME_CONTOUR_COLOR = (250,0,1)
FRAME_CONTOUR_BACKGROUND = (102,102,102)
FRAME_CONTOUR_THICKNESS = 10

FRAME_MASK_ENABLED = 0
FRAME_MASK_COLOR = (255,255,255)

FRAME_PIP_ENABLED = 0
FRAME_PIP_COLOR = (102,102,102)
FRAME_PIP_THICKNESS = 20
FRAME_PIP_SCALE = (.2,.2)       # %
FRAME_PIP_OFFSET = (.01,.01)    # %

FRAME_PIP_OPACITY = 0.7
FRAME_PIP_ROTATION = (0.,.5,.5) # deg,x,y

FRAME_ROTATE_ENABLED = 0
FRAME_ROTATE_VALUES = (0.,0.)   # deg(horiz),deg(vert)
FRAME_ROTATE_POINT = (0.5,0.5)  # x,y

FRAME_ROTATE_RULES = (0,0)
FRAME_ROTATE_COLOR = (121,121,121)
FRAME_ROTATE_THICKNESS = 10

FRAME_ROTATE_MOMENT = 1
FRAME_ROTATE_BOUNDING = 0

STM_STOP_ON_ERROR = 0
STM_ENABLED = 0

STM_FPS = 10
STM_DELAY = 1./STM_FPS

STM_FOLDER = r"C:\Data"
STM_CODEC = 'DIVX' # MJPG, DIVX, XVID
STM_EXTENSION = '.avi'
STM_NAME = 'unknown'


class baumNotConnected(Exception):
    pass

class baumNoContent(Exception):
    pass

class baumFeatureAccess(neoapi.neoapi.FeatureAccessException):
    pass

class baumUtils:

    @staticmethod
    def fileSize(folder, prefix, extension):
        return sum(file.stat().st_size for file in Path(folder).rglob(''.join([prefix,'*',extension])))
    
    @staticmethod
    def cpuUsage():
        return psutil.cpu_percent(interval=None, percpu=True)
    
    @staticmethod 
    def putText(frame, text):        

        h,w,_ = frame.shape

        fparam = {
            'font': cv2.FONT_HERSHEY_SIMPLEX,
            'scale': .6,
            'thickness': 1,
            'color': (0,0,201)
        }

        fsize, _ = cv2.getTextSize(text, fparam['font'], fparam['scale'], fparam['thickness'])
        fw, fh = fsize
        x, y = int(w/2-fw/2), int(h/4-fh/2)
        cv2.putText(frame, text, (x,y), fparam['font'], fparam['scale'], fparam['color'], fparam['thickness'])


class baumTrace(neoapi.NeoTrace):
    
    def __init__(self):
        super().__init__()

        self.EnableLogCallback(self.callback)
        self.SetSeverity(neoapi.NeoTraceSeverity_Info)

    @staticmethod
    def parse(message:str):        
        columns = ['timestamp','address','type','unknown1','user','device','command','message']
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


class baumConfig(object):

    FocusStep = DEV_FOCUS_STEP
    ApertureStep = DEV_APERTURE_STEP
    ExposureTime = DEV_EXPOSURE_TIME
    Gain = DEV_GAIN
    PixelFormat = DEV_PIXEL_FORMAT
    Gamma = DEV_GAMMA

    SharpeningMode = DEV_SHARP_MODE
    SharpeningFactor = DEV_SHARP_FACTOR
    SharpeningThreshold = DEV_SHARP_THRESHOLD

    Zoom = DEV_ZOOM
    Center = DEV_CENTER
    Rotation = DEV_ROTATION
    Flip = DEV_FLIP
    Blur = DEV_BLUR
            
    def __init__(self) -> None:        
        pass

    _filename = None
    def _get_filename(self): 
        if self._filename is None:
            self._filename = os.path.join(os.getcwd(), f"baum.config.json")
        return self._filename
    def _set_filename(self, value):
        self._filename = value
    Filename = property(fget=_get_filename, fset=_set_filename)
        
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
    
    def fromJSON(self, data):
        for key in data.keys():
            baumLogger.debug(f"    {key}: {data[key]}")
            setattr(self, key, data[key])
            
    def update(self, cam:neoapi.Cam, dev=None):
                
        baumLogger.debug(f"--- update config")

        try:
            if cam.HasFeature("ExposureTime"):
                self.ExposureTime = cam.f.ExposureTime.value
        except:
            self.ExposureTime = DEV_EXPOSURE_TIME

        try:
            if cam.HasFeature("Gain"):
                self.Gain = cam.f.Gain.value       
        except:
            self.Gain = DEV_GAIN

        try:
            if cam.HasFeature("FocusStepper"):
                self.FocusStep = cam.f.FocusStepper.value
        except:
            self.FocusStep = DEV_FOCUS_STEP

        try:
            if cam.HasFeature("ApertureStepper"):
                self.ApertureStep = cam.f.ApertureStepper.value
        except:
            self.ApertureStep = DEV_APERTURE_STEP

        try:
            if cam.HasFeature("PixelFormat"):
                self.PixelFormat = cam.f.PixelFormat.value
        except:
            self.PixelFormat = DEV_PIXEL_FORMAT

        try:
            if cam.HasFeature("Gamma"):
                self.Gamma = cam.f.Gamma.value
        except:
            self.Gamma = DEV_GAMMA

        try:
            if cam.HasFeature("SharpeningMode"):
                self.SharpeningMode = cam.f.SharpeningMode.value
        except:
            self.SharpeningMode = DEV_SHARP_MODE
        try:
            if cam.HasFeature("SharpeningFactor"):
                self.SharpeningFactor = cam.f.SharpeningFactor.value
        except:
            self.SharpeningFactor = DEV_SHARP_FACTOR
        try:
            if cam.HasFeature("SharpeningSensitivityThreshold"):
                self.SharpeningThreshold = cam.f.SharpeningSensitivityThreshold.value
        except:
            self.SharpeningThreshold = DEV_SHARP_THRESHOLD

        if dev is not None:
            self.Rotation = dev.Rotation
            self.Flip = dev.Flip
            self.Blur = dev.Blur
                        
    def load(self, filename):
        self._filename = filename
        baumLogger.debug(f"--- load config from {self.Filename}")
        try:
            with open(self.Filename,"r") as f:
                data = json.load(f)
            self.fromJSON(data)
        except Exception as ex:
            baumLogger.debug(ex)

    def save(self):            
        baumLogger.debug(f"--- save config at {self.Filename}")
        try:
            with open(self.Filename,"w") as f:
                f.write(self.toJSON())
        except Exception as ex:
            baumLogger.debug(ex)


class baumDevice():

    _no:int = 0
    def _get_no(self):
        return self._no
    No = property(fget=_get_no)

    _trace: baumTrace = None
    def _get_trace(self):
        if self._trace is None:
            self._trace = baumTrace()
        return self._trace
    Trace = property(fget=_get_trace)

    _config: baumConfig = None
    def _get_config(self):
        if self._config is None:
            self._config = baumConfig()
        return self._config
    Config = property(fget=_get_config)

    _stream = None 
    def _get_stream(self): 
        if self._stream is None:
            self._stream = {
                "enabled":0,
                "size":0,
                "cpu":0,
                "fps":STM_FPS,
                "folder":STM_FOLDER,
                "name":STM_NAME,
                "extension":STM_EXTENSION,
                "codec":STM_CODEC
                } 
        self._stream.update(
            {
                "size": baumUtils.fileSize(self._stream["folder"], self._stream["name"], self._stream["extension"]),
                "cpu": baumUtils.cpuUsage()
            }
        )  
        return self._stream
    def _set_stream(self,value): 
        self._stream = value
    Stream = property(fget=_get_stream,fset=_set_stream)

    _name:str = None
    def _set_name(self, value): 
        self._name = value
    def _get_name(self): 
        return self._name
    Name = property(fset=_set_name,fget=_get_name)

    _camera: neoapi.Cam = None
    def _get_camera(self):
        if self._camera is None: 
            if not self.Connected:
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

    def _get_modelId(self):
        return self._model['id'] if 'id' in self._model.keys() else '99'
    ModelId = property(fget=_get_modelId)

    def _get_temperature(self):
        return [self.Camera.f.DeviceTemperature.value, self.Camera.f.DeviceTemperatureExceeded.value]
    Temperature = property(fget=_get_temperature)

    #
    # feature
    #

    def _set_focusStep(self, value):        
        if self.Camera.IsWritable("FocusStepper") and self.Ready:
            self.Camera.f.FocusStepper.value = int(value)
    def _get_focusStep(self):
        if self.Camera.IsReadable("FocusStepper") and self.Ready:
            return self.Camera.f.FocusStepper.value if self.Connected else None
        else:
            return 0
    FocusStep = property(fset=_set_focusStep, fget=_get_focusStep)

    def _set_apertureStep(self, value):        
        if self.Camera.IsWritable("ApertureStepper") and self.Ready:
            self.Camera.f.ApertureStepper.value = int(value)
    def _get_apertureStep(self):
        if self.Camera.IsReadable("ApertureStepper") and self.Ready:
            return self.Camera.f.ApertureStepper.value if self.Connected else None
        else:
            return 0
    ApertureStep = property(fset=_set_apertureStep, fget=_get_apertureStep)

    def _set_exposureTime(self, value):
        self.Camera.f.ExposureTime.value = float(value) if type(value).__name__ == 'float' else float(value[0])
    def _get_exposureTime(self):
        return self.Camera.f.ExposureTime.value if self.Connected else None    
    ExposureTime = property(fset=_set_exposureTime, fget=_get_exposureTime)

    def _set_gain(self, value):
        self.Camera.f.Gain.value = float(value) if type(value).__name__ == 'float' else float(value[0])
    def _get_gain(self):
        return self.Camera.f.Gain.value if self.Connected else None
    Gain = property(fset=_set_gain, fget=_get_gain)

    def _set_sharpeningMode(self, value):        
        if self.Camera.IsWritable("SharpeningMode") and self.Ready:
            self.Camera.f.SharpeningMode.value = int(value)
    def _get_sharpeningMode(self):
        if self.Camera.IsReadable("SharpeningMode") and self.Ready:
            return self.Camera.f.SharpeningMode.value if self.Connected else None
        else:
            return 0
    SharpeningMode = property(fset=_set_sharpeningMode, fget=_get_sharpeningMode)
    
    def _set_sharpeningFactor(self, value):        
        if self.Camera.IsWritable("SharpeningFactor") and self.Ready:
            self.Camera.f.SharpeningFactor.value = int(value)
    def _get_sharpeningFactor(self):
        if self.Camera.IsReadable("SharpeningFactor") and self.Ready:
            return self.Camera.f.SharpeningFactor.value if self.Connected else None
        else:
            return 0
    SharpeningFactor = property(fset=_set_sharpeningFactor, fget=_get_sharpeningFactor)

    def _set_sharpeningThreshold(self, value):        
        if self.Camera.IsWritable("SharpeningThreshold") and self.Ready:
            self.Camera.f.SharpeningSensitivityThreshold.value = int(value)
    def _get_sharpeningThreshold(self):
        if self.Camera.IsReadable("SharpeningSensitivityThreshold") and self.Ready:
            return self.Camera.f.SharpeningSensitivityThreshold.value if self.Connected else None
        else:
            return 0
    SharpeningThreshold = property(fset=_set_sharpeningThreshold, fget=_get_sharpeningThreshold)

    #
    #
    #
    _lock:threading.Lock = None

    _raw: neoapi.Image = None
    def _set_raw(self, value): 
        self._lock.acquire()
        try:
            self._raw = value
            self.reset()
        finally:
            self._lock.release()
    def _get_raw(self): 
        self._lock.acquire()
        try:
            return self._raw
        finally:
            self._lock.release()
            
    Raw: neoapi.Image = property(fset=_set_raw, fget=_get_raw)

    _image = None
    _store = (None, 0)
    def _get_image(self):   
        if self.Raw is None:
            return None
        if self._image is None:            
            self._image = self.Raw.GetNPArray()
            self._image = np.flipud(self._image)
            if len(self._image) == 0:
                self._image = None
            else:
                self._store = (self._image, time.time_ns())
        if self._image is None:
            self._image = self._store[0]
        return self._image
    Image = property(fget=_get_image)

    def _get_age(self):
        if self._store[0] is None:
            return 0
        return (time.time_ns() - self.Modified) / 1e9
    Age = property(fget=_get_age)

    def _get_pixelFormat(self): 
        return self.Camera.f.PixelFormat.value
    def _set_pixelFormat(self, value:int): 
        self.Camera.f.PixelFormat.value = value
    PixelFormat = property(fget=_get_pixelFormat, fset=_set_pixelFormat)

    def _get_gamma(self): 
        return self.Camera.f.Gamma.value
    Gamma = property(fget=_get_gamma)

    _shape = IMG_SHAPE_EMPTY
    def _get_shape(self):
        if self._shape == IMG_SHAPE_EMPTY:
            image = self.Image
            self._shape = image.shape if image is not None else IMG_SHAPE_EMPTY
        return self._shape
    Shape = property(fget=_get_shape)

    def _get_scale(self):
        return IMG_THUMB_SCALE
    Scale = property(fget=_get_scale)

    _rotation = None
    def _get_rotation(self):
        if self._rotation is None:
            self._rotation = DEV_ROTATION
        return self._rotation
    def _set_rotation(self, value):
        if isinstance(value, float) or isinstance(value, int):
            self._rotation[0] = value
        else:
            self._rotation = value
    Rotation = property(fget=_get_rotation, fset=_set_rotation)

    def _set_center(self, value):
        self.Rotation[1:] = value
    Center = property(fset=_set_center)

    _flip = None
    def _get_flip(self):
        if self._flip is None:
            self._flip = DEV_FLIP
        return self._flip
    def _set_flip(self, value):
        self._flip = value
    Flip = property(fget=_get_flip,fset=_set_flip)    

    _blur = None
    def _get_blur(self): 
        if self._blur is None: 
            self._blur = DEV_BLUR
        return self._blur
    def _set_blur(self, value):
        self._blur = value
    Blur = property(fget=_get_blur,fset=_set_blur)    

    _zoom = None
    def _get_zoom(self):
        if self._zoom is None:
            self._zoom = DEV_ZOOM
        return self._zoom
    def _set_zoom(self,value):
        self._zoom = value
    Zoom = property(fget=_get_zoom,fset=_set_zoom)

    def _get_available(self):
        return self.Raw is not None and self.Raw.GetImageID() != 0
    Available:bool = property(fget=_get_available)

    _thumb = None
    def _get_thumb(self):
        if self._thumb is None:

            image = self.Image    

            if image is not None:

                image = self.frame(image)
                image = self.zoom(image, self.Zoom, angle=self.Rotation[0], point=self.Rotation[1:3])
                image = self.flip(image)

                self._thumb = cv2.resize(image,(0,0), fx=IMG_THUMB_SCALE[0], fy=IMG_THUMB_SCALE[1])
                self._thumb = cv2.cvtColor(self._thumb, cv2.COLOR_BGR2RGB)

            else:

                self._thumb = cv2.imread(os.path.join(os.getcwd(), IMG_THUMB_DEFAULT))   
                baumUtils.putText(self._thumb, IMG_THUMB_TEXT)   

        return self._thumb
    
    Thumb = property(fget=_get_thumb)

    _base64 = None
    def _get_base64(self):
        if self._base64 is None:
            thumb = self.Thumb        
            if thumb is not None:
                #t = datetime.datetime.now()
                ime = cv2.imencode('.jpg', thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 50])[1]
                self._base64 = base64.b64encode(ime).decode()
                #print(datetime.datetime.now() - t)
        return self._base64
    Base64 = property(fget=_get_base64)

    _modified = 0
    def _get_modified(self):
        return self._modified
    Modified = property(fget=_get_modified)

    _fps = SimpleNamespace(**dict(modified=0, delay=0))
    def _get_fps(self):
        return 0 if self._fps.delay == 0 else 1e9 / self._fps.delay
    Fps = property(fget=_get_fps)

    def _set_frameRate(self, value:float):
        if self.Camera.IsWritable("AcquisitionFrameRate"):
            self.Camera.f.AcquisitionFrameRate.value = value
    def _get_frameRate(self):
        return self.Camera.f.AcquisitionFrameRate.value
    FrameRate = property(fget=_get_frameRate, fset=_set_frameRate)

    _frameLock = threading.Lock()

    _frame = None
    def _get_frame(self):

        if self._frame is None:

            self._frame = dict(                
                
                enabled=FRAME_ENABLED,
                index=FRAME_INDEX,

                mask=dict(
                    enabled=FRAME_MASK_ENABLED,
                    color=FRAME_MASK_COLOR
                ),
                
                thresh=dict(
                    value=FRAME_THRESH_VALUE,
                    max=FRAME_THRESH_MAX,
                    type=FRAME_THRESH_TYPE
                ),

                poly=dict(
                    epsilon=FRAME_POLY_EPSILON,
                    length=FRAME_POLY_LENGTH
                ),

                dilate=dict(
                    kernel=FRAME_DILATE_KERNEL,
                    it=FRAME_DILATE_IT
                ),

                contour=dict(
                    enabled=FRAME_CONTOUR_ENABLED,
                    color=FRAME_CONTOUR_COLOR,
                    background=FRAME_CONTOUR_BACKGROUND,
                    thickness=FRAME_CONTOUR_THICKNESS,
                ),

                pip=dict(
                    enabled=FRAME_PIP_ENABLED,
                    color=FRAME_PIP_COLOR,
                    thickness=FRAME_PIP_THICKNESS,
                    scale=FRAME_PIP_SCALE,
                    offset=FRAME_PIP_OFFSET,
                    opacity=FRAME_PIP_OPACITY,
                    rotation=FRAME_PIP_ROTATION
                ),

                rotate=dict(
                    
                    values=FRAME_ROTATE_VALUES,
                    point=FRAME_ROTATE_POINT,
                    
                    enabled=FRAME_ROTATE_ENABLED,
                    rules=FRAME_ROTATE_RULES,
                    moment=FRAME_ROTATE_MOMENT,
                    bounding=FRAME_ROTATE_BOUNDING,

                    color=FRAME_ROTATE_COLOR,
                    thickness=FRAME_ROTATE_THICKNESS
                ),

                # stats                
                items=dict(
                    count=0,
                    area=[],
                    points=[]
                ),
                delay=0,
                modified=None
            )
        
        return self._frame
    
    def _set_frame(self, value):        
        self._frameLock.acquire()
        try:
            baumLogger.debug("--- update frame")
            self._frame.update(value)
        finally:
            self._frameLock.release()
    Frame = property(fget=_get_frame, fset=_set_frame)

    _pip = ''
    def _get_pip(self):
        return self._pip
    def _set_pip(self,value):
        self._pip = value
    Pip = property(fget=_get_pip,fset=_set_pip)

    _model = {}
    def _get_model(self):
        return self._model
    def _set_model(self,value):
        self._model = value
    Model = property(fget=_get_model,fset=_set_model)

    def __init__(self, no, filename) -> None:
        self._no = no
        self._trace = baumTrace()
        self._lock = threading.Lock()
        self.Config.load(filename)

    def __del__(self):
        self.Trace.disable()

    def flip(self, image):
        if self.Flip in [-1,0,1]:
            image = cv2.flip(image, self.Flip)
        return image
    
    def blur(self):
        image = self.Image
        if image is not None and self.Blur == 1:
            return cv2.Laplacian(
                image, 
                ddepth=BLUR_DDEPTH, 
                ksize=BLUR_KSIZE).var()
        return 0
    
    _mask = None
    def _get_mask(self):
        return self._mask
    Mask = property(fget=_get_mask)

    def frame(self, image):

        self._frameLock.acquire()

        ic = image

        try:

            def _isMono(pf):
                return pf == DEV_PIXEL_FORMAT_Mono8
            
            def _isRgb(pf):
                return pf == DEV_PIXEL_FORMAT_RGB8            

            def _toRgb(image, pf):
                # BGR8: 11, Mono8: 136, RGB8: 153
                match pf:
                    case 11: return cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
                    case 136: return cv2.cvtColor(image,cv2.COLOR_GRAY2RGB)
                    case _: return image.copy()

            def _toGray(image, pf, force=False):
                # BGR8: 11, Mono8: 136, RGB8: 153
                match pf:
                    case 153: return cv2.cvtColor(image,cv2.COLOR_RGB2GRAY)
                    case 11: return cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
                    case _: return image if not force else cv2.cvtColor(image,cv2.COLOR_RGB2GRAY)
                    
            def _fromGray(image, pf, force):
                match pf:
                    case 153: return cv2.cvtColor(image,cv2.COLOR_GRAY2RGB)
                    case 11: return cv2.cvtColor(image,cv2.COLOR_GRAY2BGR)
                    case _: return image if not force else cv2.cvtColor(image,cv2.COLOR_GRAY2RGB)

            def _moment(a):
                m = cv2.moments(a)
                return int(m['m10']/m['m00']),int(m['m01']/m['m00'])

            cfg = SimpleNamespace(**self.Frame)

            if cfg.enabled == 0:
                return image

            dt,t = 0, time.perf_counter_ns()
            
            i8 = _toGray(image, self.PixelFormat)

            rc, it = cv2.threshold(
                255-i8,
                thresh=cfg.thresh['value'],
                maxval=cfg.thresh['max'],
                type=cfg.thresh['type']
                )
            
            id = cv2.dilate(it, kernel=np.ones(cfg.dilate['kernel'],np.uint8), iterations=cfg.dilate['it'])
            cc,h = cv2.findContours(id,1,2)

            aa = []
            ca = []
            for c in cc:
                
                a = cv2.approxPolyDP(c, epsilon=cfg.poly['epsilon'] * cv2.arcLength(c,True), closed=True)
                
                if len(a) >= cfg.poly['length']:

                    r = cv2.minAreaRect(c)                    
                    b = cv2.boxPoints(r)
                    b = np.intp(b)
                    
                    aa.append(b)
                    ca.append(cv2.contourArea(c))

            ic = _toRgb(image, self.PixelFormat)
            # ic = _fromGray(i8, self.PixelFormat, force=True)

            ca = np.array(ca) 

            if len(ca) >0:   
                
                ii = np.argsort(ca)[::-1]            
                aa = np.array(aa)[ii]
                ca = ca[ii]

                if cfg.contour['enabled'] == 1:
                    
                    cv2.drawContours(
                        image=ic,
                        contours=aa,
                        contourIdx=0,
                        color=cfg.contour['color'],
                        thickness=cfg.contour['thickness']
                        )
                        
                    if len(ca) >1:
                    
                        cv2.drawContours(
                            image=ic,
                            contours=aa[1:,:,:],
                            contourIdx=-1,
                            color=cfg.contour['background'],
                            thickness=cfg.contour['thickness']
                            )

                if cfg.mask['enabled'] == 1:

                    mask = np.zeros_like(ic)
                    cv2.fillPoly(mask, [aa[0]], cfg.mask['color'])
                    ic = cv2.bitwise_and(ic,mask)
                    self._mask = aa[0]
                else:
                    self._mask = None

                if cfg.rotate["enabled"] == 1:
                    
                    if np.sum(cfg.rotate['rules']) > 0:
                                                
                        if cfg.rotate['moment'] == 1:
                            cx,cy = _moment(aa[0])
                            cv2.circle(ic,(cx,cy), 10, cfg.rotate['color'], cfg.rotate['thickness'])

                        def _invert(m):
                            a, b = m.shape
                            if a != b:
                                raise ValueError("Only square matrices are invertible.")

                            i = np.eye(a, a)
                            return np.linalg.lstsq(m, i)[0]

                        def _intersect(A,B):
                            m = np.array([A[1]-A[0],B[0]-B[1]]).T
                            i = B[0]-A[0]
                            t, s = np.linalg.lstsq(m,i,rcond=None)[0]
                            #t, s = np.linalg.solve(m, i)
                            return np.array([(1-t)*A[0] + t*A[1]]) # (1-s)*B[0] + s*B[1]
                        
                        def _rules(v,h,R):
                                                    
                            rv,rh = np.zeros((2,2)),np.zeros((2,2))
                            kv,kh = 0,0
                            for i in range(R.shape[0]):
                                B = R[i]
                                s = np.round(_intersect(v,B),0).astype(np.int32)
                                if LineString(B).contains(Point(s)) and kv <2:
                                    rv[kv,:] = s
                                    kv += 1
                                s = np.round(_intersect(h,B),0).astype(np.int32)
                                if LineString(B).contains(Point(s)) and kh <2:
                                    rh[kh,:] = s
                                    kh += 1
                            return rv.astype(np.int32), rh.astype(np.int32)
                        
                        def _angle(v0,v1):                            
                            angle = math.atan2(np.linalg.det([v0,v1]),np.dot(v0,v1))
                            return np.degrees(angle)
                            
                        p0,p1,p2,_ = aa[0]

                        v0 = np.array(p1)-np.array(p0)
                        v1 = np.array([0,1])
                        av = _angle(v0,v1)

                        v0 = np.array(p2)-np.array(p1)
                        v1 = np.array([1,0])
                        ah = _angle(v0,v1)

                        self.Frame['rotate']['values'] = (ah,av)

                        h,w = ic.shape[0],ic.shape[1]

                        # bounding rectangle
                        R = np.array([[0,0],[0,h], 
                                      [0,h],[w,h], 
                                      [w,h],[w,0], 
                                      [w,0],[0,0]]).reshape(4,2,2)

                        # rule vertical
                        v = np.array([p0,p1])
                        h = np.array([p1,p2])
                        rv,rh = _rules(v,h,R)

                        if cfg.rotate['rules'][0] == 1:
                            cv2.line(ic, rh[0], rh[1],cfg.rotate['color'], cfg.rotate['thickness'])
                        if cfg.rotate['rules'][1] == 1:
                            cv2.line(ic, rv[0], rv[1],cfg.rotate['color'], cfg.rotate['thickness'])

                        if cfg.rotate['bounding'] == 1:
                            for i in range(R.shape[0]):
                                B = R[i]
                                cv2.line(ic, B[0], B[1],cfg.rotate['color'], cfg.rotate['thickness'])


                if _isMono(self.PixelFormat):
                    ic = _toGray(ic, self.PixelFormat, force=True)

                if cfg.pip['enabled'] == 1:

                    id = _fromGray(id, self.PixelFormat, force=True)

                    id = cv2.resize(id,(0,0), fx=cfg.pip['scale'][0], fy=cfg.pip['scale'][1])
                    idc = np.array([[0,0],[id.shape[1],0],[id.shape[1],id.shape[0]],[0,id.shape[0]]])
                    cv2.drawContours(
                        image=id,
                        contours=[idc],
                        contourIdx=-1,
                        color=cfg.pip['color'],
                        thickness=cfg.pip['thickness']
                        )    
                    if _isMono(self.PixelFormat):
                        id = _toGray(id, self.PixelFormat, force=True)
                    self.Pip = base64.b64encode(cv2.imencode('.jpg', id)[1]).decode()
                else:
                    self.Pip = ''

                self.Frame['items'] = dict(
                    count=len(ca),
                    area=ca,
                    points=aa[0].flatten()
                )

            self.Frame['delay'] = time.perf_counter_ns() - t
            self.Frame['modified'] = time.perf_counter()

        except Exception as ex:
            baumLogger.debug(ex)
        
        finally:
            self._frameLock.release()

        return ic
       
    def zoom(self, data, zoom=1., angle=0, point=None):    
        point = DEV_CENTER if point is None else point        
        cy, cx = [point[i] * v for i,v in enumerate(data.shape[0:2])]
        R = cv2.getRotationMatrix2D((cx,cy), angle, zoom)
        return cv2.warpAffine(data, R, data.shape[1::-1], flags=cv2.INTER_LINEAR)

    @staticmethod
    def model(model):
        return {
            "id": model.GetId(),
            "name": model.GetModelName(),
            "serial": model.GetSerialNumber(),
            "vendor": model.GetVendorName(),
            "address": model.GetGevIpAddress(),
            "mac": model.GetGevMACAddress()
        }

    def connect(self):

        baumLogger.debug(f"--- connect device {self._no}")
                
        models = neoapi.CamInfoList.Get()
        models.Refresh()

        model = None        
        if self._no < models.size():
            model = models[self._no]        

        if model is None:
            return False
        
        if model.IsConnectable():                
            self.Name = model.GetModelName()

        if self.Name is not None:

            baumLogger.debug(f"    name {self.Name}")

            self._camera = neoapi.Cam()
            self.Camera.EnableImageCallback(self.callback)
            self.Camera.Connect(self.Name)

            self.Model = self.model(model)

            baumLogger.debug(f"    model {self.Model}")

            return True
        
        return False
        
    def disconnect(self):
        if self.Connected:
            self.Camera.DisableImageCallback()
            self.Camera.Disconnect()

    def release(self):
        self.Config.update(self.Camera, self)
        self.Config.save()

        self.disconnect()

    def callback(self, raw):
        
        self.Raw = raw
        
        self._modified = time.time_ns()

        self._fps.delay = self._modified - self._fps.modified
        self._fps.modified = self._modified

    def reset(self):
        self._image = None
        self._thumb = None
        self._base64 = None
        self._shape = IMG_SHAPE_EMPTY

    def _get_ready(self):
        try:
            return self.Camera.f.OpticControllerStatus.value == neoapi.OpticControllerStatus_Ready and \
                self.Camera.f.FocusStatus.value == neoapi.FocusStatus_Ready
        except:
            return False
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
        try:
            return (self.Camera.f.DecimationHorizontal.value,
                    self.Camera.f.DecimationVertical.value)
        except:
            return (1,1)
    def _set_decimation(self, value):        
        try:
            self.Camera.f.DecimationHorizontal.value = value
            self.Camera.f.DecimationVertical.value = value
        except:
            pass
    Decimation = property(fget=_get_decimation, fset=_set_decimation)

    def _get_decimationMode(self):
        try:
            return (self.Camera.f.DecimationHorizontalMode.value,
                    self.Camera.f.DecimationVerticalMode.value)
        except:
            return (1,1)
    def _set_decimationMode(self, value:int):     
        try:   
            self.Camera.f.DecimationHorizontalMode.SetInt(value)
            self.Camera.f.DecimationVerticalMode.SetInt(value)
        except:
            pass
    """
    Sets the mode used to reduce the resolution 
    when Decimation{Horizontal,Vertical} is used.
    0: Average - The values of a group of N adjacent pixels are averaged.
    1: Discard - The value of every Nth pixel is kept, others are discarded.
    """
    DecimationMode = property(fget=_get_decimationMode, fset=_set_decimationMode)

    """
    0: Ethernet100Mbps - Interface speed mode is 100 Mbps.
    1: Ethernet10Gbps - Operation at 10 Gbps. AVAILABLE: Always.
    2: Ethernet1Gbps - Interface speed mode is 1 Gbps.
    3: Ethernet2_5Gbps - Operation at 2.5 Gbps. AVAILABLE: Always.
    4: Ethernet5Gbps - Operation at 5 Gbps. AVAILABLE: Always.
    5: FullSpeed - USB Operation at 12 Mbps
    6: HighSpeed - USB Operation at 480 Mbps
    7: LowSpeed - USB Operation at 1.5 Mbps
    8: SuperSpeed - USB Operation at 5 Gbps
    """
    _sensorSpeedMode = None
    def _get_sensorSpeedMode(self):
        if self._sensorSpeedMode is None:
            self._sensorSpeedMode = self.Camera.f.InterfaceSpeedMode.value
        return self._sensorSpeedMode
    SensorSpeedMode = property(fget=_get_sensorSpeedMode)

    """
    0: Global - The shutter opens and closes at the same time for all pixels. All the pixels are exposed for the same length of time at the same time.
    1: GlobalReset - The shutter opens at the same time for all pixels but ends in a sequential manner. The pixels are exposed for different lengths of time.
    2: Rolling - The shutter opens and closes sequentially for groups (typically lines) of pixels. All the pixels are exposed for the same length of time but not at the same time.
    """
    _sensorShutterMode = None
    def _get_sensorShutterMode(self):
        if self._sensorShutterMode is None:
            self._sensorShutterMode = self.Camera.f.SensorShutterMode.value
        return self._sensorShutterMode
    SensorShutterMode = property(fget=_get_sensorShutterMode)    

    """
    0: Eight - 8 taps.
    1: Four - 4 taps.
    2: One - 1 tap.
    3: Ten - 10 taps.
    4: Three - 3 taps.
    5: Two - 2 taps.
    """
    _sensorTaps = None
    def _get_sensorTaps(self):
        if self._sensorTaps is None and self.Camera.HasFeature("SensorTaps"):            
            self._sensorTaps = self.Camera.f.SensorTaps.value
        return self._sensorTaps
    SensorTaps = property(fget=_get_sensorTaps)        

    _sensor = None
    def _get_sensor(self):
        if self._sensor is None:

            self._sensor = dict(

                name=self.Camera.f.SensorName.value,

                height=self.Camera.f.SensorHeight.value,
                width=self.Camera.f.SensorWidth.value,

                pixelHeight=self.Camera.f.SensorPixelHeight.value,
                pixelWidth=self.Camera.f.SensorPixelWidth.value,  

                taps=self.SensorTaps,
                shutter=self.SensorShutterMode,
                speedMode=self.SensorSpeedMode,
            )

        return self._sensor
    Sensor = property(fget=_get_sensor)

    _sequencer = None
    def _get_sequencer(self):
        if self._sequencer is None:

            self._sequencer = dict(

                mode=self.Camera.f.SequencerMode.value,

            )

        return self._sequencer
    
    Sequencer = property(fget=_get_sequencer)

    _optic = None
    def _get_optic(self):
        try:
            status = self.Camera.f.OpticControllerStatus.value
            self._optic = dict(               
                status=status,
                statusDescription=OPTIC_STATUS[status]
            )
            if status == neoapi.OpticControllerStatus_Ready:
                self._optic.update(dict(
                    firmwareVersion=self.Camera.f.OpticControllerFirmwareVersion.value,
                    vendorName=self.Camera.f.OpticControllerVendorName.value
                ))
            
        except:
            status = 2
            self._optic = dict(               
                status=status,
                statusDescription=OPTIC_STATUS[status]
            )
        finally:
            return self._optic

    Optic = property(fget=_get_optic)

    def setup(self):

        try:
            
            baumLogger.debug(f"--- check and setup camera")

            if not self.Connected:
                baumLogger.debug(f"    not connected")
                return False

            #
            # execute optic startup
            #

            baumLogger.debug(f"    opti controller ")
            baumLogger.debug(f"    {self.Optic}")            

            if self.Optic['status'] not in [OPTIC_STATUS_ID['Ready'], OPTIC_STATUS_ID['NotConnected']]:    

                baumLogger.debug(f"    not ready, try to initialize")

                try:

                    self.Camera.f.OpticControllerDisconnect.Execute()

                except Exception as ex:
                    baumLogger.debug(f"    disconnect failed")
                    baumLogger.debug(ex)

                try:

                    self.Camera.f.OpticControllerInitialize.Execute()
                    t = time.perf_counter()
                    while True:
                        time.sleep(0.5)
                        baumLogger.debug(f"    state {self.Camera.f.OpticControllerStatus.value}")
                        if 5 == self.Camera.f.OpticControllerStatus.value:
                            break
                        if time.perf_counter() - t > 4:
                            break
                
                except Exception as ex:
                    baumLogger.debug(f"    initialize failed")
                    baumLogger.debug(ex)

                baumLogger.debug(f"    {self.Optic}")
            
            #
            # setup image aquisition
            #

            self.Camera.f.ExposureAuto.value = neoapi.ExposureAuto_Off

            baumLogger.debug(f"    exposure auto {self.Camera.f.ExposureAuto.value}")
            baumLogger.debug(f"    speed mode {self.Camera.f.InterfaceSpeedMode.value}")

            # 1 Off, 3 Success
            self.Camera.f.BalanceWhiteAuto.value = neoapi.BalanceWhiteAuto_Off
            baumLogger.debug(f"    balance white {self.Camera.f.BalanceWhiteAuto.value}")

            self.Camera.f.ColorTransformationAuto.value = neoapi.ColorTransformationAuto_Once
            baumLogger.debug(f"    color trans. auto {self.Camera.f.ColorTransformationAuto.value}")

            # 0 overlapped, 1 sequencial
            self.Camera.f.ReadoutMode.value = 0
            baumLogger.debug(f"    readout {self.Camera.f.ReadoutMode.value} {self.Camera.f.ReadOutTime.value}")

            baumLogger.debug(f"    w w(max) {self.Camera.f.Width.value}, {self.Camera.f.WidthMax.value}")         
            baumLogger.debug(f"    h h(max) {self.Camera.f.Height.value} {self.Camera.f.HeightMax.value}")         

            baumLogger.debug(f"--- sensor")
            baumLogger.debug(f"    {self.Sensor}")

            baumLogger.debug(f"--- sequncer")
            baumLogger.debug(f"    {self.Sequencer}")

            #
            #
            #
            self.PixelFormat = DEV_PIXEL_FORMAT

            baumLogger.debug(f"--- pixel format")
            baumLogger.debug(f"    {self.PixelFormat}")

            try:

                self.Decimation = DEV_DECIMATION
                self.DecimationMode = DEV_DECIMATION_MODE

                baumLogger.debug(f"--- decimation")
                baumLogger.debug(f"    {self.Decimation} {self.DecimationMode}")

            except Exception as ex:
                baumLogger.debug(f"{ex}")

            try:

                self.Binning = DEV_BINNING
                self.BinningMode = DEV_BINNING_MODE

                baumLogger.debug(f"--- binning")
                baumLogger.debug(f"    {self.Binning} {self.BinningMode}")

            except Exception as ex:
                baumLogger.debug(f"{ex}")

            baumLogger.debug(f"--- gamma")
            baumLogger.debug(f"    {self.Gamma}")

            region = self.Region            
            region['x'] = 0
            region['width'] = region['widthMax']
            region['y'] = 0
            region['height'] = region['heightMax']            
            self.Region = region

            baumLogger.debug(f"--- region")
            baumLogger.debug(f"    {self.Region}")

            rgn_ = [
                self.Camera.f.RegionMode.value,                 # 1: On
                self.Camera.f.RegionConfigurationMode.value,    # 0: NonOverlapping
                self.Camera.f.RegionAcquisitionMode.value,      # 1: Sensor
                self.Camera.f.RegionTransferMode.value,         # 1: StackedImage
                self.Camera.f.RegionSelector.value,             # 1: Region0
                ]

            baumLogger.debug(f"--- region")
            baumLogger.debug(f"    {','.join([str(v) for v in rgn_])}")

            baumLogger.debug(f"--- sharpening")

            # 0: ActiveNoiseReduction - Sharpening is enabled in active noise reduction mode
            # 1: AdaptiveSharpening - Sharpening is enabled in adaptive sharpening mode.
            # 2: GlobalSharpening - Sharpening is enabled in global sharpening mode.
            # 3: Off - Sharpening is disabled.
            self.Camera.f.SharpeningMode.value = DEV_SHARP_MODE
            self.Camera.f.SharpeningFactor.value = DEV_SHARP_FACTOR
            self.Camera.f.SharpeningSensitivityThreshold.value = DEV_SHARP_THRESHOLD

            baumLogger.debug(f"    {self.Camera.f.SharpeningMode.value} {self.Camera.f.SharpeningFactor.value} {self.Camera.f.SharpeningSensitivityThreshold.value}")

            time.sleep(DEV_INIT_TIMEOUT)

        except Exception as ex:
            baumLogger.debug(ex)
            return False

        finally:
            return True

    def initialize(self):

        if self.Connected:

            if self.setup():

                try:
                
                    self.FocusStep = self.Config.FocusStep,
                    self.ApertureStep = self.Config.ApertureStep,
                    self.ExposureTime = self.Config.ExposureTime,
                    self.Gain = self.Config.Gain,
                    self.SharpeningMode = self.Config.SharpeningMode,
                    self.SharpeningFactor = self.Config.SharpeningFactor,
                    self.SharpeningThreshold = self.Config.SharpeningThreshold,
                    self.Rotation = self.Config.Rotation
                    self.Flip = self.Config.Flip
                    self.Blur = self.Config.Blur

                except Exception as ex:
                    baumLogger.debug(ex)
                    return False

                return self.request()
        return False

    def request(self, 
                focusStep:int=None, 
                apertureStep:int=None,
                exposureTime:float=None, 
                gain:float=None,
                sharpeningMode:int=None,
                sharpeningFactor:int=None,
                sharpeningThreshold:int=None,
                zoom:float=None,
                rotation:float=None,
                center:dict=None,
                flip:int=None,
                blur:int=None,
                rate:float=None,
                format:str=None                
                ):
        
        if self.Connected:

            if focusStep is not None: self.FocusStep = focusStep
            if apertureStep is not None: self.ApertureStep = apertureStep
            if exposureTime is not None: self.ExposureTime = exposureTime
            if gain is not None: self.Gain = gain
            if sharpeningMode is not None: self.SharpeningMode = sharpeningMode
            if sharpeningFactor is not None: self.SharpeningFactor = sharpeningFactor
            if sharpeningThreshold is not None: self.SharpeningThreshold = sharpeningThreshold
            if zoom is not None: self.Zoom = zoom
            if rotation is not None: self.Rotation = rotation
            if center is not None: self.Center = center
            if flip is not None: self.Flip = flip
            if blur is not None: self.Blur = blur
            if rate is not None: self.FrameRate = rate
            if format is not None: self.PixelFormat = format
            
        return self.Available
    
    def balance(self):
        self.Camera.f.ExposureAuto.value = neoapi.ExposureAuto_Once
        self.Camera.f.BalanceWhiteAuto.value = neoapi.BalanceWhiteAuto_Once
        self.Camera.f.ColorTransformationAuto.value = neoapi.ColorTransformationAuto_Once
        
    def store(self, filename:str=None, mode:str='jpg', tags:dict=dict()):

        rc = None
        
        image = self.Image if mode == 'jpg' else self.Raw
                
        if image is not None:

            if self.Flip in [-1,0,1]:
                image = self.flip(image)

            folder = PUB_STORE_FOLDER
            prefix = PUB_STORE_PREFIX
            extension = PUB_STORE_EXTENSION
            
            if filename is None:                

                prefix = tags["prefix"] if "prefix" in tags.keys() and len(tags["prefix"]) > 0 else prefix                
                modified = tags['modified']
                extension = '.jpg' if 'jpg' == mode else extension
                
                filename = os.path.join(folder, f"{prefix}{modified}{extension}")                
            
            if 'jpg' == mode:
                rc = cv2.imwrite(filename, 
                                 cv2.cvtColor(image, cv2.COLOR_BGR2RGB), [int(cv2.IMWRITE_JPEG_QUALITY), IMG_QUALITY])
            else:
                rc = image.Save(filename)
        
            tags.update(
                dict(
                    pixelFormat = self.PixelFormat,
                    focusStep = self.FocusStep,
                    apertureStep = self.ApertureStep,
                    exposureTime = self.ExposureTime,
                    gain = self.Gain,
                    sharpeningMode = self.SharpeningMode,
                    sharpeningFactor = self.SharpeningFactor,
                    sharpeningThreshold = self.SharpeningThreshold
                )
            )

            self.meta(filename, prefix, tags)

            self._size = baumUtils.fileSize(folder, prefix, extension)

        return rc
    
    def meta(self, filename:str, prefix:str, tags:dict):

        if DEV_XMP:

            try:
                # store tags to image xmp data
                image = pyexiv2.Image(filename)        
                pyexiv2.registerNs(f"Xmp.hot", "hot")
                data = {f"Xmp.hot.{key}": tags[key] for key in tags.keys() }
                sensor = self.Sensor
                data = { f"Xmp.hot.sensor.{key}": sensor[key] for key in sensor.keys() } | data
                image.modify_xmp(data)
            finally:            
                image.close()

        try:
            # append pub store meta
            #row = [str(tags[k]) for k in PUB_STORE_META_COL if k in tags.keys()]
            row = [str(tags[k]) for k in tags.keys()]
            row += [os.path.basename(filename)]
            filename = os.path.join(PUB_STORE_FOLDER, f"{prefix}.csv")
            with open(filename, '+a') as f:
                f.write(f"{PUB_STORE_META_DEL.join(row)}{PUB_STORE_META_LF}")
        except Exception as ex:
            baumLogger.debug(ex)
        finally:
            pass

    _size = None
    def _get_size(self): 
        if self._size is None:
            self._size = baumUtils.fileSize(PUB_STORE_FOLDER, PUB_STORE_PREFIX, PUB_STORE_EXTENSION)
        return self._size
    Size = property(fget=_get_size)

    _process = None
    def _get_process(self):
        p = psutil.Process(os.getpid())        
        self._process = {
            'name': p.name(),
            'pid': p.pid,
            'threads': len(p.threads()),
            'cpu': p.cpu_percent(.1),
            'time': sum(p.cpu_times())
        }        
        return self._process    
    Process = property(fget=_get_process)

        
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

    def _get_info(self):
        rc = dict()        
        if self.Available:           
            raw = self.Raw
            rc.update(dict(
                id=raw.GetImageID(),
                timestamp=raw.GetTimestamp(),
                size=raw.GetSize(),
                format=raw.GetPixelFormat(),
                width=raw.GetWidth(),
                height=raw.GetHeight()
            ))
        return rc
    Info = property(fget=_get_info)


class baumWorker(threading.Thread):
    
    _process = None
    def _get_process(self):

        p = psutil.Process(os.getpid())
        
        self._process = {
            'name': p.name(),
            'pid': p.pid,
            'threads': len(p.threads()),
            'cpu': p.cpu_percent(.1),
            'time': sum(p.cpu_times())
        }
        
        return self._process
    
    Process = property(fget=_get_process)

    _lock:threading.Lock = None
    def _get_lock(self):
        return self._lock
    
    def _get_stopOnError(self):
        return True
    StopOnError = property(fget=_get_stopOnError)

    _delay = DEV_DELAY
    def _get_delay(self): return self._delay
    Delay = property(fget=_get_delay)

    _exit = None
    def _get_exit(self): return self._exit
    def _set_exit(self,value): self._exit = value
    Exit = property(fget=_get_exit, fset=_set_exit)

    _devices:list = []
    def _get_devices(self): 
        return self._devices
    def _set_devices(self, value):
        self._devices = value
    Devices:list = property(fget=_get_devices, fset=_set_devices)    

    def device(self, no):
        for device in self.Devices:
            if no == device.No:
                return device
        return None

    def _set_running(self, value):
        if not value and self.Exit is not None:
            self.Exit.set()
        if value and self.Exit is None:
            self.Exit = threading.Event()
    def _get_running(self):
        return self.Exit is not None and not self.Exit.is_set()
    Running = property(fset=_set_running,fget=_get_running)

    def _get_connected(self):
        for d in self._devices:
            if d.Connected:
                return True
        return False
    Connected = property(fget=_get_connected)

    def _get_enabled(self):
        return 0!=len(self._devices) and self.Connected
    Enabled = property(fget=_get_enabled)    

    def __init__(self, devices, lock):
       super().__init__()          
       self.daemon = True
       self.Devices = devices
       self._lock = lock

    def run(self):
        pass

    def release(self):
        if self.Enabled:
            self.Devices = []

    def exit(self):
        if self.Exit is not None:
            self.Exit.set()  

    def wait(self):
        self.Exit.wait(self.Delay)


class baumPublisher(baumWorker):
    
    def _get_stopOnError(self):
        return super().StopOnError and PUB_STOP_ON_ERROR
    StopOnError = property(fget=_get_stopOnError)
    
    def _get_enabled(self):
        return super().Enabled and PUB_ENABLED
    Enabled = property(fget=_get_enabled)

    def __init__(self, devices, lock):
       super().__init__(devices, lock)   
       self._delay = PUB_DELAY
       
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
            elif isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            return json.JSONEncoder.default(self, obj) 

    def run(self):

        self.Running = True

        loop = asyncio.new_event_loop()
        threading.Thread(target=loop.run_forever).start()   
        
        while(self.Running):            
            
            self._lock.acquire()

            try:

                for device in self.Devices:

                    if not device.request():
                        self.wait()
                        continue

                    t = datetime.datetime.now()

                    data:dict = dict(
                        
                        name=device.Name,
                        id=device.Id,
                        modelId=device.ModelId,
                        no=device.No,
                        
                        connected=device.Connected,
                        available=device.Available,

                        f=dict( 
                            focusStep=device.FocusStep,
                            apertureStep=device.ApertureStep,
                            exposureTime=device.ExposureTime,
                            gain=device.Gain,                            
                            sharpeningMode=device.SharpeningMode,
                            sharpeningFactor=device.SharpeningFactor,
                            sharpeningThreshold=device.SharpeningThreshold,
                            zoom=device.Zoom,
                            rotation=device.Rotation,
                            flip=device.Flip,
                            pixelFormat=device.PixelFormat,
                            gamma=device.Gamma,
                        ),
                        
                        blur=device.blur(),

                        image=dict(
                            thumb=device.Base64,
                            shape=device.Shape,
                            scale=device.Scale,                            
                            age=device.Age,
                            frame=device.Frame,
                            pip=device.Pip,
                            mask=device.Mask                              
                        ),

                        stream=device.Stream,

                        status=device.Status,

                        decimation=dict(
                            value=device.Decimation,
                            mode=device.DecimationMode
                        ),
                        binning=dict(
                            value=device.Binning,
                            mode=device.BinningMode
                        ),
                        region=device.Region,

                        info=device.Info,
                        model=device.Model,
                        sensor=device.Sensor,
                        optic=device.Optic,

                        fps=device.Fps,
                        frameRate=device.FrameRate,
                        size=device.Size,
                        process=device.Process,

                        temperature=device.Temperature,
                        
                        modified=time.time_ns()
                    )  

                    message = json.dumps(data, cls=baumPublisher.ComplexJSONEncoder).encode('ascii')

                    if PUB_DEBUG:
                        if device.No in [DEV_NO[0]]:
                            #baumLogger.debug(f"{data['id']}: {data['f']}")
                            #baumLogger.debug(f"{data['status']}")
                            #baumLogger.debug(f"{sys.getsizeof(data)}")
                            #baumLogger.debug(f"{device.Process}")
                            baumLogger.debug(f"{datetime.datetime.now()} {device.No}: {data['fps']} {data['blur']:04f} {datetime.datetime.now()-t} ")
                    
                    asyncio.run_coroutine_threadsafe(self.publish(PUB_TOPIC, message), loop)

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

    def __init__(self, devices:list, lock):
       super().__init__(devices, lock)   
       self._delay = SUB_DELAY

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

                    rc = asyncio.run(subscribe([SUB_TOPIC], self.callback), debug=True)                
                    
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

        self._lock.acquire()
        try:

            baumLogger.debug(f"    subscribe to {data}")

            keys = list(data.keys())

            if SUB_DEBUG:                
                if 'frame' not in keys:
                    baumLogger.debug('    ' + str(data))

            device = self.device(data['no'])
            if device is None:
                asyncio.get_running_loop().call_soon_threadsafe(self._event.set)
                return False
            
            if 'connect' in keys:
                if not device.Connected:
                    device.connect()

            if 'disconnect' in keys:
                if device.Connected:
                    device.disconnect()

            if 'step' in keys:
                if device.Connected:                
                    device.request(focusStep=data['step'])
            if 'aperture' in keys:
                if device.Connected:                
                    device.request(apertureStep=data['aperture'])
            if 'exposure' in keys:
                if device.Connected:                
                    device.request(exposureTime=data['exposure'])
            if 'gain' in keys:
                if device.Connected:                
                    device.request(gain=data['gain'])

            if 'sharpeningMode' in keys:
                if device.Connected:                
                    device.request(sharpeningMode=data['sharpeningMode'])
            if 'sharpeningFactor' in keys:
                if device.Connected:                
                    device.request(sharpeningFactor=data['sharpeningFactor'])
            if 'sharpeningThreshold' in keys:
                if device.Connected:                
                    device.request(sharpeningThreshold=data['sharpeningThreshold'])

            if 'zoom' in keys:
                if device.Connected:                
                    device.request(zoom=data['zoom'])
            if 'rotation' in keys:
                if device.Connected:                
                    device.request(rotation=data['rotation'])
            if 'flip' in keys:
                if device.Connected:                
                    device.request(flip=data['flip'])

            if 'blur' in keys:
                if device.Connected:                
                    device.request(blur=data['blur'])

            if 'rate' in keys:
                if device.Connected:                
                    device.request(rate=data['rate'])
                    device.request(exposureTime=1_000_000.0/data['rate'])

            if 'balance' in keys:
                if device.Connected:
                    device.balance()

            if 'center' in keys:
                if device.Connected:                
                    device.request(center=data['center'])

            if 'format' in keys:
                if device.Connected:                
                    device.request(format=data['format'])

            if 'store' in keys:
                if device.Connected:
                    device.store(mode=data['store']['mode'],tags=data['store']['tags'])
                        
            if 'save' in keys:
                if device.Connected:
                    device.Config.update(device.Camera, device)
                    device.Config.save()

            if 'stream' in keys:
                if device.Connected:
                    device.Stream = None
                    device.Stream.update(data['stream']['tags'])

            if 'frame' in keys:
                device.Frame = data['frame']
                
            if 'command' in keys:
                if 'release' == data['command']:
                    self.Running = False

            asyncio.get_running_loop().call_soon_threadsafe(self._event.set)

        finally:
            self._lock.release()

    def wait(self):
        self.Exit.wait(self.Delay)


class baumStreamer(baumWorker):

    def _get_stopOnError(self):
        return super().StopOnError and STM_STOP_ON_ERROR
    StopOnError = property(fget=_get_stopOnError)
    
    def _get_enabled(self):
        return super().Enabled and STM_ENABLED
    Enabled = property(fget=_get_enabled)

    def __init__(self, devices, lock):
       super().__init__(devices, lock)
       self.setup()

    def setup(self): 
        self._streams = []
        for device in self.Devices:
            self._streams.append(baumStreamer._Stream(device))
            try:                
                device.Camera.f.AcquisitionFrameRateEnable.value = True
                device.Camera.f.AcquisitionFrameRate.value = self.stmFrameRate(device)
            except:
                pass

    class _Stream():

        _device = None

        def _get_no(self): return self._device.No if self._device is not None else -1
        No = property(fget=_get_no)

        def __init__(self, device):
            super().__init__()
            self._device = device

        def _get_enabled(self): 
            return self._device.Stream["enabled"] == 1    
        Enabled = property(fget=_get_enabled)
       
        def _get_frameRate(self): 
            return self._device.Stream["fps"]
        FrameRate = property(fget=_get_frameRate)

        _frameSize = None
        def _get_frameSize(self):
            if self._frameSize is None:
                frame = self.Frame
                self._frameSize = (frame.shape[1],frame.shape[0])                
            return self._frameSize
        FrameSize = property(fget=_get_frameSize)
        
        def _get_extension(self): 
            return self._device.Stream["extension"]
        Extension = property(fget=_get_extension)
        
        def _get_name(self): 
            return self._device.Stream["name"]
        Name = property(fget=_get_name)
        
        def _get_folder(self): 
            return self._device.Stream["folder"]
        Folder = property(fget=_get_folder)
        
        def _get_filename(self): 
            return os.path.join(self.Folder, f"{self.Name}{self.Extension}")
        Filename = property(fget=_get_filename)
        
        def _get_frame(self): 
            return self._device.Image
        Frame = property(fget=_get_frame)
        
        def _get_codec(self): 
            return self._device.Stream["codec"]
        Codec = property(fget=_get_codec)

        def _get_size(self): 
            return baumUtils.fileSize(self.Folder, self.Name, self.Extension)
        Size = property(fget=_get_size)

        _video = None
        def _get_video(self):
            if self._video is None:
                baumLogger.debug(f"--- open video writer")
                fourcc = cv2.VideoWriter_fourcc(*(self.Codec))
                frameRate = self.FrameRate
                frameSize = self.FrameSize                
                self._video = cv2.VideoWriter()
                self._video.open(self.Filename, fourcc, frameRate, frameSize, True)
                baumLogger.debug(f"    {fourcc} {frameRate} {frameSize}")
            return self._video
        Video = property(fget=_get_video)

        def _get_opened(self):
            return self._video is not None and self._video.isOpened()
        Opened = property(fget=_get_opened)

        def write(self, frame=None):

            if frame is None:
                frame = self.Frame
            
            self._video.write(frame)

            fname = self.Filename
            _ = cv2.imwrite(f"{fname}.jpg", frame, 
                            [int(cv2.IMWRITE_JPEG_QUALITY), IMG_QUALITY])
            
            fsize = self.Size
            baumLogger.debug(f"{fsize} {fname}")

        def disable(self, force=False):
            if not self.Enabled or force:
                if self._video is not None:
                    self._video.release()
                self._video = None

    _streams = []

    def stream(self, no):
        for stream in self._streams:
            if stream.No == no:
                return stream
        return None
    

    def device(self, no):
        for device in self.Devices:
            if device.No == no:
                return device
        return None
    
    def run(self):
        
        self.Running = True

        try:               

            while(self.Running):

                no = 0

                device = self.device(no)
                if device is None:
                    self.wait()
                    continue

                stream = self.stream(no)
                if stream is None:
                    self.wait()
                    continue

                if stream.Enabled:

                    self._lock.acquire()

                    try:
                        
                        frame = stream.Frame
                        if frame is None:
                            continue

                        _ = stream.Video # init video, if not avilable

                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                                    
                        if stream.Opened:
                            stream.write(frame)

                    except Exception as ex:
                        baumLogger.debug(ex)
                    finally:
                        self._lock.release()

                else:
                    stream.disable()

                self.wait()

        except Exception as ex:
            baumLogger.debug(ex)
        
        finally:

            self.disable()
            self.Running = False

    def disable(self):
        for stream in self._streams:
            stream.disable(force=True)


    def release(self):
        if self.Enabled:
            super().release()

    def wait(self):
        self.Exit.wait(self.Delay)


    def update(self, tags:dict=dict()):
        
        no = 0        
        
        prefix = tags["prefix"] if "prefix" in tags.keys() and len(tags["prefix"]) > 0 else prefix                
        modified = tags['modified']

        device = self.device(no)
        device.Stream.update(
            dict(
                name=f"{prefix}{modified}",
                codec=tags["codec"] if "codec" in tags.keys() else STM_CODEC,
                modified=modified
            )
        )
        

def main():

    os.system('cls')

    try:

        devices = []

        for no in DEV_NO:

            filename = sys.argv[no+1] if len(sys.argv) > no+1 else os.path.join(WRK_CONFIG_PATH, f'baum.config.{no}.json')
    
            device = baumDevice(no=no,filename=filename)
            if not device.Connected:
                device.connect()            
            device.initialize()                        
            devices.append(device)

        lock:threading.Lock = threading.Lock()

        pub = baumPublisher(devices,lock)
        pub.start()
        
        sub = baumSubscriber(devices,lock)
        sub.start()

        stm = baumStreamer(devices,lock)
        stm.start()

        _runningEvent = Event()
        def _runningLoop():
            baumLogger.debug("--- running until ctrl+c")
            try:
                while not _runningEvent.is_set():
                    _runningEvent.wait(.1)
            except KeyboardInterrupt:
                _runningEvent.set()
        _runningLoop()
        
        asyncio.run(pub.publish(SUB_TOPIC,
                                json.dumps(dict(command='release')).encode('ascii')
                                ))
        pub.exit()
        sub.exit()
        stm.exit()
        
        pub.join()
        sub.join()
        stm.join()

    except Exception as ex:
        baumLogger.error(ex)

    finally:

        for device in devices:
            if device.Connected: 
                device.release()



if __name__ == '__main__':
    main()
