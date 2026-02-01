
import ctypes
import pysoem
from threading import Lock,Event

from _EcatObject import EcatLogger


class TemperatureController(object):

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
    

class BeckhoffTemperatureController(TemperatureController):

    _channels = 2
    def _set_channels(self, value):
        self._channels = value
    Channels = property(fset=_set_channels)
    
    def _get_txMap(self):        
        _fields = []
        for i in range(self._channels):
            _fields += [(f'status{i}', ctypes.c_uint16), (f'value{i}', ctypes.c_int16)]
        return type('TxMap', (ctypes.Structure, ), { '_pack': 1, '_fields': _fields })
    TxMap = property(fget=_get_txMap)

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

            buff =  self.TxMap.from_buffer_copy(self.Device.input)
            data = {}
            for i in range(self._channels):
                data[str(i)] = {
                    'status': bin(getattr(buff,f'status{i}', '0b0'))[2:].zfill(16),
                    'value': getattr(buff,f'value{i}', 0)
                }
                EcatLogger.debug(f"{data[str(i)]}")

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
            EcatLogger.error(f"BeckhoffTemperatureController.output {ex}")

        finally:
            self._lock.release()
            return True
          
    def error(self, value):

        EcatLogger.debug(f"### {value}")
        EcatLogger.debug(f"    {value.__doc__}")          
