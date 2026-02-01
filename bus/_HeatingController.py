
import pysoem
import struct
from threading import Lock,Event

from _EcatObject import EcatLogger
from _EcatSeverity import SEVERITY_VERBOSE, EcatSeverityController


class HeatingController(object):

    _debug = False    
    _lock = Lock()
    _exit = Event()

    def _get_enabled(self):
        return not self._exit.is_set()
    Enabled = property(fget=_get_enabled)

    _index = 0

    _device = None
    def _get_device(self): return self._device
    Device = property(fget=_get_device)

    def _get_id(self):
        return f"{self._device.name}.{self._index}"
    Id = property(fget=_get_id)

    _deviceLock: Lock = None
    def _get_deviceLock(self): return self._deviceLock
    DeviceLock: Lock = property(fget=_get_deviceLock)

    _deviceChannel: int = None
    def _get_deviceChannel(self): return self._deviceChannel
    DeviceChannel: int = property(fget=_get_deviceChannel)

    _data = None
    def _get_data(self): return self._data
    Data = property(fget=_get_data)    

    _display = None
    def _get_display(self): 
        return self._display
    Display = property(fget=_get_display)    

    def __init__(self, index, device, lock, channel, debug=False) -> None:   
        super().__init__()   
        self._index = index  
        self._device = device
        self._deviceLock = lock
        self._deviceChannel = channel
        self._debug = debug
        
    def release(self):
        self._exit.set()

    def input(self):
        return None

    def output(self, data):        
        pass

    def write(self, data):   
        pass

    def init(self):
        return False
    
    def compute(self):
        pass
            
    def run(self):
        return False
    
    def callback(self, *args):
        pass

    def severityFunc(self, value):
        pass

    
class BeckhoffHeatingController(HeatingController):

    _severity = None

    def __init__(self, index, device, lock, channel, debug=False) -> None:
        super().__init__(index, device, lock, channel, debug)   
        self._severity = [SEVERITY_VERBOSE] * channel

    _initialized = False          
    def init(self):
        return True

    def run(self):
        
        if not self.Enabled:
            return None

        if (self.Device.state & pysoem.OP_STATE) != self.Device.state:
            return None

        self._lock.acquire()
        try:            
            if not self._initialized:
                self._initialized = self.init()
            
            if self._initialized:
                self.compute()

        except Exception as ex:
            EcatLogger.debug(f"-- BeckhoffHeatingController.run {ex}")

        finally:
            self._lock.release()

        return self.Data
    
    def compute(self):
        return self.read()
    
    def read(self):
        self.DeviceLock.acquire()
        try:
            pass
        except Exception as ex:
            pass
        finally:
            self.DeviceLock.release() 

    def write(self, data):
        self.DeviceLock.acquire()
        try:
            self.Device.output = data        
        except Exception as ex:
            EcatLogger.debug(f"-- BeckhoffHeatingController.write {ex}")
        finally:
            self.DeviceLock.release() 

    def output(self, data):
        
        try:
            num = len(data)
            if num == self.DeviceChannel:
                for i in range(num):
                    if not EcatSeverityController.isValid([self._severity[i]]):
                        data[i] = 0
                self.write(struct.pack(f'{num}H', *([int(v*65535) for v in data])))

        except Exception as ex:
            EcatLogger.error(f"-- BeckhoffHeatingController.output {ex}")
            return False

        return True

    def callback(self, *args):
        return False
    
    def isValid(self):
        return EcatSeverityController.isValid(self._severity)
    
    def severityFunc(self, value):   
        self._severity = value
