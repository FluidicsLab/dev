
import ctypes
import pysoem
from threading import Lock,Event

from _EcatObject import EcatLogger


class PressureController(object):

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

    _deviceLock = None
    def _get_deviceLock(self): return self._deviceLock
    DeviceLock: Lock = property(fget=_get_deviceLock)

    _data = {}
    def _get_data(self): return self._data
    Data = property(fget=_get_data)    
    
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

    def write(self, data):        
        pass

    def output(self, data):        
        pass

    def init(self):
        return False
            
    def run(self):
        return False
    
    def callback(self, *args):
        pass
    

class BeckhoffPressureController(PressureController):

    class TxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [            
            ('status1', ctypes.c_uint16),        #  2 1a00
            ('value1', ctypes.c_int16),          #  4
            ('status2', ctypes.c_uint16),        #  2 1a00
            ('value2', ctypes.c_int16),          #  4
        ]

    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)

    _data = None
           
    def run(self):

        data = None

        if (self.Device.state & pysoem.PREOP_STATE) == self.Device.state:
            return data

        if (self.Device.state & pysoem.OP_STATE) != self.Device.state:
            return data

        self._lock.acquire()

        try:

            data = None
            
            buff =  BeckhoffPressureController.TxMap.from_buffer_copy(self.Device.input)                
            data  = {
                '1': { 'status': bin(buff.status1)[2:].zfill(16), 'value': buff.value1 },
                '2': { 'status': bin(buff.status2)[2:].zfill(16), 'value': buff.value2 }
            }        

        except Exception as ex:
            self.error(ex)
        
        finally:
            self._lock.release()

        return data

    def output(self, data):

        if not self.Enabled:
            return False
        
        self._lock.acquire()
        try:
            self._data = data.copy()            

        except Exception as ex:
            EcatLogger.error(f"BeckhoffPressureController.output {ex}")

        finally:
            self._lock.release()
            return True
          
    def error(self, value):

        EcatLogger.debug(f"### {value}")
        EcatLogger.debug(f"    {value.__doc__}")          
