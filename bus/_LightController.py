import pysoem
import ctypes
from threading import Lock,Event

from _EcatObject import EcatLogger


class LightController(object):

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
    DeviceLock = property(fget=_get_deviceLock)

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

    def output(self, data):        
        pass

    def write(self, data):   
        pass

    def init(self):
        return False
            
    def run(self):
        return False
    

class CcsLightController(LightController):

    class RxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            # 0 enable, 1 output, 7 reset
            ('control', ctypes.c_uint16),   # 1600
            ('current', ctypes.c_uint16)    # 1601
        ]

    class TxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [            
            # 0 ready to activate, 1 output active, 
            # 6 warning, 7 error
            ('status', ctypes.c_uint16),
        ]  

    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)    

    def _get_infoData(self):
        rc = {}
        try:
            a = 0x9000
            rc = { key: ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(a,o)).value 
                for (o,key) in [(0x08, 'voltage'), (0x09, 'current'), (0x11, 'hour')]}
        finally:
            return rc
    InfoData = property(fget=_get_infoData)

    def _get_diagData(self):
        rc = {}
        try:
            a = 0xA000
            rc = { key: ctypes.c_bool.from_buffer_copy(self.Device.sdo_read(a,o)).value 
                  for (o,key) in [(0x01, 'saturated'), (0x02, 'over temperature'), 
                                  (0x04, 'under voltage (supply)'), (0x05, 'over voltage (supply)'), 
                                  (0x06, 'short circuit'), (0x07, 'open load'),
                                  (0x09, 'misc error'), (0x0b, 'over voltage (output)')]}        
        finally:
            return rc
    DiagData = property(fget=_get_diagData)

    def run(self):

        self._lock.acquire()

        data = None  
        try:

            buff =  CcsLightController.TxMap.from_buffer_copy(self.Device.input)            
            data  = {
                'status': bin(buff.status)[2:].zfill(16),
                'infoData': self.InfoData,
                'diagData': self.DiagData
            }
        
            if self._data is not None:

                if 'current' in self._data.keys():

                    # 0: ready to activate, 1: output active
                    cw = '0000000000000011' if self._data['current'] >0 else '0000000000000001'

                    c = int(self._data['current'])

                    out = CcsLightController.RxMap()
                    out.control = ctypes.c_uint16(int(cw,2))
                    out.current = ctypes.c_uint16(c) 
                    self.write(out)
                    
                    self.Device.sdo_write(0x8000, 0x02, bytes(ctypes.c_uint16(c)))

                    del self._data['current']

                elif 'command' in self._data.keys():

                    cw = self._data['command']

                    out = CcsLightController.RxMap()
                    out.control = ctypes.c_uint16(int(cw,2))                    
                    self.write(out)

                    del self._data['command']
        
        finally:
            self._lock.release()

        return data
    
    def write(self, data):
        self.DeviceLock.acquire()
        try:
            self.Device.output = bytes(data)
        finally:
            self.DeviceLock.release()

    def output(self, data):

        if not self.Enabled:
            return False
        
        self._lock.acquire()
        try:
            self._data = data.copy()            

        except Exception as ex:
            EcatLogger.debug(ex)

        finally:
            self._lock.release()
            return True        