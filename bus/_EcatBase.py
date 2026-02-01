
from _Ecat import *
from _EcatSettings import EcatConfig

import threading
from threading import Event, Lock
from queue import Queue

from typing import Type

import asyncio
import mqttools
import json

import sys, gc

import logging
logging.basicConfig(level=logging.ERROR,
                    #format='%(levelname)-8s %(threadName)-15s %(message)s'
                    format='%(message)s'
                    )
EcatBaseLogger = logging.getLogger(__name__)
EcatBaseLogger.setLevel(logging.DEBUG)
EcatBaseLogger.name = "__EcatBaseLogger__"
def loggingFilter(record: logging.Filter): return True
EcatBaseLogger.addFilter(loggingFilter)


class scheduleWorker(threading.Thread):

    _exit = None
    _delay = .5

    _stopOnError = False

    _items = None

    _queue:Queue = None
    _lock: Lock = Lock()

    def _set_running(self, value):
        if not value and self._exit is not None:
            self._exit.set()
        if value and self._exit is None:
            self._exit = Event()
    def _get_running(self):
        return self._exit is not None and not self._exit.is_set()
    running = property(fset=_set_running,fget=_get_running)

    _host = None
    def _get_host(self): 
        return self._host    
    Host = property(fget=_get_host)

    _port = None
    def _get_port(self): 
        return self._port
    Port = property(fget=_get_port)

    def __init__(self, host, port):
       super().__init__()
       self._host = host
       self._port = port
       self._items = []
       self._queue = Queue()       
       self.daemon = True

    def run(self):
        pass

    def register(self, item):
        self._lock.acquire()
        try:
            self._items.append(item)
        finally:
            self._lock.release()

    def unregister(self, item):
        self._lock.acquire()
        try:
            self._items.append(item)
        finally:
            self._lock.release()

    def dispatch(self, data):

        if data is None or data['value'] is None:
            return False
        
        self._lock.acquire()
        try:
            self._queue.put(data)
        finally:
            self._lock.release()

        return not self._queue.empty()
    
    def exit(self):
        self._exit.set()  

    def wait(self):
        self._exit.wait(self._delay)


class tunerWorker(scheduleWorker):

    _lock: Lock = Lock()

    def __init__(self, host, port):
       super().__init__(host, port)
       self._delay = EcatConfig().Tuner.delay

    _event = None
       
    def run(self): 

        self.running = True

        async def subscribeTopic(host, port, topics:list[str], callback):
            
            threading.current_thread().name = self._name
            
            client:mqttools.Client = mqttools.Client(host, port, 
                                                     connect_delays=[],
                                                     subscriptions=topics)
            rc = client.client_id
            
            try:
                await client.start()
                
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
                EcatLogger.error(ex)
                return -1
            finally:
                await client.stop()

            return rc  
        
        while(self.running):
            
            try:    
                rc = asyncio.run(
                    subscribeTopic(self.Host, self.Port, EcatConfig().Tuner.topics, self.callback), 
                    debug=False)
                
                if (-1 == rc):
                    if -1 == rc:
                        if self._stopOnError:
                            msg = f'Subscription stop on error at {self.Host}:{self.Port}'
                            EcatBaseLogger.debug(msg)                        
                            self.running = False            
            except Exception as ee: 
                EcatBaseLogger.error(ee)
            finally:                
                pass

            self.wait()

        self.running = False

    def callback(self, data):

        source = data['source']
        for item in self._items: 
            if item.name == source:
                item.publish(data)

        asyncio.get_running_loop().call_soon_threadsafe(self._event.set)


class dispatchWorker(scheduleWorker):
    
    def __init__(self, host, port):
       super().__init__(host, port)     
       self._delay = EcatConfig().Dispatch.delay  

    class ComplexJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.ndarray, np.number)):
                return obj.tolist()
            return json.JSONEncoder.default(self, obj) 
    
    def run(self): 

        self.running = True
        
        async def publishTopic(host, port, topic, message):
            
            threading.current_thread().name = self._name            
            client = mqttools.Client(host, port, connect_delays=[])            
            rc = client.client_id
            try:
                await client.start()
                client.publish(mqttools.Message(topic, message))            
            except Exception as ex:                        
                EcatLogger.error(ex)
                rc = -1             
            finally:
                await client.stop() 
                                    
            return rc   
        
        loop = asyncio.new_event_loop()
        threading.Thread(target=loop.run_forever).start()   
        
        while(self.running):

            self._lock.acquire()

            try:
                prefix = EcatConfig().Dispatch.topic

                while not self._queue.empty():
                    
                    data = self._queue.get_nowait()

                    if isinstance(data, dict):
                        
                        topic = f"{prefix}{data['source']}"
                        message = json.dumps(data, cls=dispatchWorker.ComplexJSONEncoder).encode('ascii')
                                             
                        asyncio.run_coroutine_threadsafe(publishTopic(self.Host, self.Port, topic, message), loop)
                    
                    self._queue.task_done()

            finally:

                self._lock.release()
        
            self.wait()
        
        self.running = False


class baseWorker(threading.Thread):

    _lock = Lock()

    _name = ''
    _key = 'NONE'

    _exit = None
    _delay = 1.

    _scheduler:list[scheduleWorker] = []
    _master:EcatMaster = None

    _index:int = None
    _debug:bool = False

    _kwargs = None

    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], index:int=None, 
                 debug:bool=False, **kwargs):
        super().__init__()
        
        self._master = master
        self._scheduler = scheduler
        self._index = index
        self._debug = debug

        self._exit = Event()
        self.daemon = True
        self._name = self.__class__.__name__

        self._kwargs = kwargs
        
        self.setup()

    def setup(self):
        for scheduler in self._scheduler:
            scheduler.register(self)

    def exit(self):
        self._exit.set()

    def run(self):
        pass

    def dispatch(self, data):
        for scheduler in self._scheduler:
            if isinstance(scheduler, dispatchWorker):
                scheduler.dispatch(data)

    def publish(self, data):
        pass

    def device(self, cls:Type):
        """
        index'ed device from master list
        """
        devices = [device for device in self._master.Devices if isinstance(device, cls)]
        if self._index is not None and len(devices) >0:
            devices =  [device for device in devices if device.Index == self._index]        
        return devices[0] if len(devices)>0 else None
    
    def valid(self, cls:Type):
        return self._device is not None and isinstance(self._device, cls)   

    def enable(self, value:bool=True):
        if self._device is not None:
            
            self._device.Debug = self._debug
            self._device.Enabled = value
            if value:
                self._device.setup()

    def preset(self):
        pass

    def reset(self):
        pass

       
class masterWorker(baseWorker):
        
    """
    unused
    """

    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], index:int=None, 
                 debug:bool=False):
        super().__init__(master, scheduler, index, debug)
        self._delay = EcatConfig().Master.delay
        self._name = self.__class__.__name__

    def setup(self):
        super().setup()

    def disable(self):
        self.exit()

    def run(self):
             
        while(not self._exit.is_set()): 
            rc = self._master.Proceed()
            self.dispatch(dict(source=self._name, value=rc))            
            self._exit.wait(self._delay)


class el1008Worker(baseWorker):

    # [8,4, 7,3, 6,2, 5,1]
    
    _device:EcatEL1008 = None

    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], index:int=None, debug:bool=False):
        super().__init__(master, scheduler, index, debug)
        self._key = 'EL1008'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")
        
    def setup(self) -> bool:        
        self._device:EcatEL1008 = self.device(EcatEL1008)

        mode = [1,0,50_000,1,0,50_000]
        self._device.Mode = (mode[:3],mode[3:])

        if self.valid(EcatEL1008):
            super().enable()            
            super().setup()
        
        return self._device.Enabled if self._device is not None else False
        
    def disable(self):
        super().enable(False)

    def run(self):    
                            
        while(not self._exit.is_set()):     

            if self._device is not None:
                rc = self._device.Proceed()
                self.dispatch(dict(source=self._name,value=rc))

            self._exit.wait(self._delay)
    
        self.disable()


class el1124Worker(baseWorker):

    # [4,2, 3,1]
    
    _device:EcatEL1124 = None

    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], index:int=None, debug:bool=False):
        super().__init__(master, scheduler, index, debug)
        self._key = 'EL1124'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")
        
    def setup(self) -> bool:        
        self._device:EcatEL1124 = self.device(EcatEL1124)
        if self.valid(EcatEL1124):
            super().enable()            
            super().setup()        
        return self._device.Enabled if self._device is not None else False

    def disable(self):
        super().enable(False)

    def run(self):    
                            
        while(not self._exit.is_set()):         

            rc = self._device.Proceed()

            self.dispatch(dict(source=self._name,value=rc))

            self._exit.wait(self._delay)
    
        self.disable()


class el2008Worker(baseWorker):

    # [8,4, 7,3, 6,2, 5,1]

    _disableByShutdown = True
    def _get_disableByShutdown(self): return self._disableByShutdown
    DisableByShutdown = property(fget=_get_disableByShutdown)
    
    _device:EcatEL2008 = None
    
    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], index:int=None, 
                 debug:bool=False,
                 disableByShutdown:bool=True,
                 **kwargs
                 ):
        super().__init__(master, scheduler, index, debug, **kwargs)
        self._key = 'EL2008'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        self._disableByShutdown = disableByShutdown
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")

    def setup(self) -> bool:        
        self._device:EcatEL2008 = self.device(EcatEL2008)
        if self.valid(EcatEL2008):
            super().enable()
            super().setup()
            if 'value' in self._kwargs:
                self.Params = self._kwargs['value']
        return self._device.Enabled if self._device is not None else False
        
    def disable(self):
        super().enable(False)
                
    def run(self):         
     
        while(not self._exit.is_set()):            
            
            rc = self._device.Proceed(self.Params)
                                    
            self.dispatch(dict(source=self._name,value=rc))

            self._exit.wait(self._delay)
    
        if self.DisableByShutdown:
            rc = self._device.Proceed([0]*self._device.Channels)
            self.dispatch(dict(source=self._name,value=rc))

        self.disable()

    _params = None
    def _get_params(self):
        self._lock.acquire()
        try:
            if self._params is None:
                self._params = [0]*self._device.Channels
        finally:
            self._lock.release()        
        return self._params
    def _set_params(self,value):
        self._lock.acquire()
        try:
            self._params = value
        finally:
            self._lock.release()
    Params = property(fget=_get_params,fset=_set_params)        

    def publish(self, data):
        if len(data.keys()) >0:
            if data['source'] == self._name and \
                ('target' in data.keys() and data['target'] == self._device.Index): 
                self.Params = data['value']                       


class el2124Worker(baseWorker):

    # [4,2, 3,1]

    _sendOnce = False
    def _get_sendOnce(self): return self._sendOnce
    SendOnce = property(fget=_get_sendOnce)

    _disableByShutdown = True
    def _get_disableByShutdown(self): return self._disableByShutdown
    DisableByShutdown = property(fget=_get_disableByShutdown)
    
    _device:EcatEL2124 = None
    
    def __init__(self, master:EcatMaster, 
                 scheduler:list[scheduleWorker]=[], index:int=None, 
                 debug:bool=False,
                 sendOnce:bool=False,
                 disableByShutdown:bool=True                
                 ):
        super().__init__(master, scheduler, index, debug)
        self._key = 'EL2124'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        self._sendOnce = sendOnce        
        self._disableByShutdown = disableByShutdown
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")

    def setup(self) -> bool:        
        self._device:EcatEL2124 = self.device(EcatEL2124)
        if self.valid(EcatEL2124):
            super().enable()
            super().setup()
        return self._device.Enabled if self._device is not None else False
    
    def disable(self):
        super().enable(False)
        
    def run(self):    
                
        while(not self._exit.is_set()):    
            
            rc = self._device.Proceed(self.Params)

            if self.SendOnce:
                self.Params = None

            #self.dispatch(dict(source=self._name,value=rc))

            self._exit.wait(self._delay)


        if self.DisableByShutdown:
            rc = self._device.Proceed([0]*self._device.Channels)
            self.dispatch(dict(source=self._name,value=rc))

        self.disable()

    _params = None
    def _get_params(self):
        self._lock.acquire()
        try:
            if self._params is None:
                self._params = [0]*self._device.Channels                
        finally:
            self._lock.release()        
        return self._params
    def _set_params(self,value):
        self._lock.acquire()
        try:
            self._params = value
        finally:
            self._lock.release()
    Params = property(fget=_get_params,fset=_set_params)        

    def publish(self, data):
        if len(data.keys()) >0:
            if data['source'] == self._name and 'target' in data.keys() \
                and data['target'] == self._device.Index:                

                #EcatBaseLogger.debug(f"{self._name} {self._device.Index} <<< {data['value']}")

                self.Params = data['value'] 


class el3202Worker(baseWorker):

    _device:EcatEL3202 = None

    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], index:int=None, debug:bool=False):
        super().__init__(master, scheduler, index, debug)        
        self._key = 'EL3202'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")
        
    def setup(self) -> bool:
        self._device:EcatEL3202 = self.device(EcatEL3202)
        if self.valid(EcatEL3202):
            super().enable()     
            super().setup()
        return self._device.Enabled if self._device is not None else False
    
    def disable(self):
        super().enable(False)
        
    def run(self):
           
        while(not self._exit.is_set()):       

            rc = self._device.Proceed()

            self.dispatch(dict(source=self._name,value=rc))

            self._exit.wait(self._delay)
        
        self.disable()

    def publish(self, data):
        self._device.Payload(data)


class el2502Worker(baseWorker):
    
    _device:EcatEL2502 = None

    """
    # temperature control
    # 20Hz, 50ms
    ([1,0,50_000],[1,0,50_000])
                    
    # light control
    # 1kHz, 1ms
    ([1,0,1_000],[1,0,1_000])
    """
    
    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], 
                 index:int=None, 
                 debug:bool=False,
                 **kwargs
                 ):                
        self._key = 'EL2502'
        super().__init__(master, scheduler, index, debug, **kwargs) 
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")
            
    def setup(self) -> bool:

        self._device:EcatEL2502 = self.device(EcatEL2502) 
                
        if self.valid(EcatEL2502):
            super().enable()
            super().setup()
            if 'value' in self._kwargs:
                self.Params = self._kwargs['value']

        return self._device.Enabled if self._device is not None else False
    
    def disable(self):
        super().enable(False)
        
    def run(self):    
        
        while(not self._exit.is_set()):        
            if self._device is not None:
                rc = self._device.Proceed(self.Params)
                self.dispatch(dict(source=self._name,value=rc))
            self._exit.wait(self._delay)
       
        self.disable()

    _params = None
    def _get_params(self):
        self._lock.acquire()
        try:
            if self._params is None:
                self._params = [0.]*self._device.Channels
        finally:
            self._lock.release()        
        return self._params
    def _set_params(self,value):
        self._lock.acquire()
        try:
            self._params = value
        finally:
            self._lock.release()
    Params = property(fget=_get_params,fset=_set_params)        

    def publish(self, data):
        if len(data.keys()) >0:            
            if data['source'] == self._name:                
                if 'target' in data.keys() and data['target'] == self._device.Index:
                    if 'value' in data.keys():
                        self.Params = data['value']

class el2596Worker(baseWorker):
    
    _device:EcatEL2596 = None
    
    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], 
                 index:int=None, 
                 debug:bool=False,
                 **kwargs
                 ):                
        self._key = 'EL2596'
        super().__init__(master, scheduler, index, debug, **kwargs) 
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")
            
    def setup(self) -> bool:

        self._device:EcatEL2596 = self.device(EcatEL2596) 
                
        if self.valid(EcatEL2596):
            super().enable()
            super().setup()
            if 'value' in self._kwargs:
                self.Params = self._kwargs['value']

        return self._device.Enabled if self._device is not None else False
    
    def disable(self):
        super().enable(False)
        
    def run(self):    
        
        while(not self._exit.is_set()): 
            if self._device is not None:
                rc = self._device.Proceed(self.Params)
                self.dispatch(dict(source=self._name,value=rc))
            self._exit.wait(self._delay)       
        self.disable()

    _params = None
    def _get_params(self):
        self._lock.acquire()
        try:
            if self._params is None:
                self._params = [0.]*self._device.Channels
        finally:
            self._lock.release()        
        return self._params
    def _set_params(self,value):
        self._lock.acquire()
        try:
            self._params = value
        finally:
            self._lock.release()
    Params = property(fget=_get_params,fset=_set_params)        

    def publish(self, data):
        if len(data.keys()) >0:            
            if data['source'] == self._name:                
                if 'target' in data.keys() and data['target'] == self._device.Index:
                    if 'value' in data.keys():
                        self.Params = data['value']                        
                                

class el3314Worker(baseWorker):

    _device:EcatEL3314 = None

    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], index:int=None, debug:bool=False):
        super().__init__(master, scheduler, index, debug)        
        self._key = 'EL3314'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")
   
    def setup(self) -> bool:
        
        self._device:EcatEL3314 = self.device(EcatEL3314)
        
        if self.valid(EcatEL3314):
            super().enable()
            super().setup()
        
        return self._device.Enabled if self._device is not None else False
    
    def disable(self):
        super().enable(False)   
        
    def run(self):

        if not self.setup():
            return
        
        while(not self._exit.is_set()):            

            rc = self._device.Proceed()
            
            self.dispatch(dict(source=self._name,value=rc))

            self._exit.wait(self._delay)
        
        self.disable()

    def publish(self, data):
        self._device.Payload(data)


class el4104Worker(baseWorker):
    
    _device:EcatEL4104 = None

    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], 
                 index:int=None, 
                 debug:bool=False,
                 **kwargs
                 ):
        super().__init__(master, scheduler, index, debug, **kwargs)
        self._key = 'EL4104'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        EcatBaseLogger.debug(f"{self._index} {self._key} {self._name}")

    def setup(self) -> bool:        
        self._device:EcatEL4104 = self.device(EcatEL4104)
        if self.valid(EcatEL4104):
            super().enable()            
            super().setup()
            if 'value' in self._kwargs:
                self.Params = self._kwargs['value']
        return self._device.Enabled if self._device is not None else False
    
    def disable(self):
        super().enable(False)   
        
    def run(self):
        
        while(not self._exit.is_set()):
            if self._device is not None:
                rc = self._device.Proceed(self.Params)                        
                self.dispatch(dict(source=self._name,value=rc))
            self._exit.wait(self._delay)
        
        self.disable()
        
    _params = None
    def _get_params(self):
        self._lock.acquire()
        try:
            if self._params is None:
                self._params = [0.]*self._device.Channels                

        finally:            
            self._lock.release()        
        return self._params
    def _set_params(self,value):
        self._lock.acquire()
        try:
            self._params = value
        finally:
            self._lock.release()
    Params = property(fget=_get_params,fset=_set_params)

    def publish(self, data):
        if len(data.keys()) >0:
            if data['source'] == self._name and 'target' in data.keys() \
                and data['target'] == self._device.Index:
                self.Params = data['value']


class el3164Worker(baseWorker):
    
    _device:EcatEL3164 = None

    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], index:int=None, debug:bool=False):        
        super().__init__(master, scheduler, index, debug)
        self._key = 'EL3164'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")

    def setup(self) -> bool:        
        self._device:EcatEL3164 = self.device(EcatEL3164)
        if self.valid(EcatEL3164):
            super().enable()            
            super().setup()
        return self._device.Enabled if self._device is not None else False
        
    def disable(self):
        super().enable(False) 

    def run(self):
        
        while(not self._exit.is_set()):

            rc = self._device.Proceed()   

            self.dispatch(dict(source=self._name,value=rc))

            self._exit.wait(self._delay)
        
        self.disable()


class el6614Worker(baseWorker):
    
    _device:EcatEL6614 = None

    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], index:int=None, debug:bool=False):
        super().__init__(master, scheduler, index, debug)
        self._key = 'EL6614'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")

    def setup(self) -> bool:        
        self._device:EcatEL6614 = self.device(EcatEL6614)
        if self.valid(EcatEL6614):
            super().enable()            
            super().setup()
        return self._device.Enabled if self._device is not None else False
        
    def disable(self):
        super().enable(False) 

    def run(self):
        
        while(not self._exit.is_set()):
            
            rc = self._device.Proceed()            
            
            self.dispatch(dict(source=self._name,value=rc))

            self._exit.wait(self._delay)
        
        self.disable()


class el3124Worker(baseWorker):
    
    _device:EcatEL3124 = None

    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], index:int=None, 
                 debug:bool=False):
        super().__init__(master, scheduler, index, debug)
        self._key = 'EL3124'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")

    def setup(self) -> bool:        
        self._device:EcatEL3124 = self.device(EcatEL3124)        
        if self.valid(EcatEL3124):
            super().enable()
            super().setup()     
        return self._device.Enabled if self._device is not None else False
    
    def disable(self):
        super().enable(False)   

    def run(self):

        while(not self._exit.is_set()):                    
            if self._device is not None:    
                rc = self._device.Proceed()
                self.dispatch(dict(source=self._name,value=rc))
            self._exit.wait(self._delay)
        
        self.disable()


class el6021Worker(baseWorker):
    
    _device:EcatEL6021 = None
    
    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], 
                 index:int=None, debug:bool=False, **kwargs):
        super().__init__(master, scheduler, index, debug, **kwargs)        
        self._key = 'EL6021'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__        
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")

    def setup(self) -> bool:
        self._device:EcatEL6021 = self.device(EcatEL6021)
        if self.valid(EcatEL6021):
            super().enable()
            super().setup()
            if 'addr' in self._kwargs.keys():
                self._device.config(addr=self._kwargs['addr'], debug=self._debug)       
        return self._device.Enabled if self._device is not None else False
    
    def disable(self):
        super().enable(False)    
        
    def run(self):    
        
        while(not self._exit.is_set()):       
            if self._device is not None:      
                rc = self._device.Proceed()
                self.dispatch(dict(source=self._name,value=rc)) 
                self._exit.wait(self._delay)        
        
        self.disable()


class ed1fWorker(baseWorker):
    
    _device:EcatED1F = None
    
    def __init__(self, master:EcatMaster, scheduler:list[scheduleWorker]=[], index:int=None, debug:bool=False):
        super().__init__(master, scheduler, index, debug)        
        self._key = 'ED1F'
        self._delay = EcatConfig().Terminal[self._key].delay
        self._name = self.__class__.__name__        
        EcatBaseLogger.debug(f"{self._index:03d} {self._key} {self._name}")

    def setup(self) -> bool:
        self._device:EcatED1F = self.device(EcatED1F)
        if self._device is not None:
            self._device.Debug = super()._debug    
        if self.valid(EcatED1F):            
            super().enable()
            super().setup() # register to mqtt
        return self._device.Enabled if self._device is not None else False
    
    def disable(self):
        super().enable(False)

    def preset(self):
        if self._device is not None:
            self._device.ProfileVelocity = 0

    def reset(self):
        if self._device is not None:
            self._device.ProfileVelocity = 0
        
    def run(self):    

        while(not self._exit.is_set()): 
            
            rc = self._device.Proceed() if self._device is not None else {}
            
            self.dispatch(dict(source=self._name,value=rc))            

            self._exit.wait(self._delay)        
        
        self.disable()

    def publish(self, data):
        if len(data.keys()) >0 and self._device is not None:
            if data['source'] == self._name and 'target' in data.keys() and data['target'] == self._device.Index:
                if 'value' in data.keys():
                    value = data['value']
                    if 'velocity' in value.keys():
                        self._device.ProfileVelocity = value['velocity']
                    if 'positionOffset' in value.keys():
                        self._device.PositionOffset = value['positionOffset']    
                EcatBaseLogger.debug(f"{self._device.Name}.{self._device.Index} {data}")

