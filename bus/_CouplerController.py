
import pysoem
import psutil

from threading import Lock,Event,Thread

from _EcatObject import EcatLogger
from _EcatSeverity import SEVERITY_VERBOSE, EcatSeverityController, SeverityLogger


class CouplerController(object):

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

    _data = None
    def _get_data(self): return self._data
    Data = property(fget=_get_data)    

    _display = None
    def _get_display(self): 
        return self._display
    Display = property(fget=_get_display)    

    def __init__(self, index, device, lock, debug=False) -> None:   
        super().__init__()   
        self._index = index  
        self._device = device
        self._deviceLock = lock
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

    
class BeckhoffCouplerController(CouplerController):

    _severity = None
    _reader: Thread = None

    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)   
        self._severity = [SEVERITY_VERBOSE]

    _initialized = False          
    def init(self):
        self._data = {}
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
                    self._reader = Thread(target=self.compute)
                    self._reader.start()
            
        except Exception as ex:
            EcatLogger.debug(f"-- BeckhoffCouplerController.run {ex}")

        finally:
            self._lock.release()

        return self.Data
    
    def compute(self):
        
        EcatLogger.debug(f"--- start computing {self.__class__.__name__}")
                    
        while not self._exit.is_set():

            self.read()

            delay = 1.0
            self._exit.wait(delay)

        EcatLogger.debug(f"--- stop computing {self.__class__.__name__}")

    
    def read(self):
        self.DeviceLock.acquire()
        try:

            # non-blocking
            self._data["cpu"] = { 
                'p': psutil.cpu_percent(interval=None) ,
                'pp': psutil.cpu_percent(interval=None, percpu=True),
                'count': psutil.cpu_count()
                }

        except Exception as ex:
            EcatLogger.debug(f"-- BeckhoffCouplerController.read {ex}")
        finally:
            self.DeviceLock.release() 

    def callback(self, *args):
        return False
    
    def isValid(self):
        return EcatSeverityController.isValid(self._severity)
    