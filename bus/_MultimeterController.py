
from os import replace
import struct
import ctypes, time
import pysoem
import numpy as np
from threading import Lock,Event

from _EcatObject import EcatLogger


class MultimeterController(object):

    RxPDO_MAP_ADDRESS = 0x1C12
    TxPDO_MAP_ADDRESS = 0x1C13

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
    

class BeckhoffMultimeterController(MultimeterController):

    class RxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [            
            ('control', ctypes.c_uint16),       #  2 1600
        ]

    class TxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [            
            ('status', ctypes.c_uint16),        #  2 1a00
            ('value', ctypes.c_int32),          #  4
            ('settings', ctypes.c_uint16)       #  2 1a01
        ]

    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)

    _data = None
        
    def _get_pdoInput(self):
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(MultimeterController.TxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(MultimeterController.TxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]
    
    def _set_pdoInput(self, values):
        self.Device.sdo_write(MultimeterController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values):
            self.Device.sdo_write(MultimeterController.TxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(MultimeterController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))

    PdoInput = property(fget=_get_pdoInput,fset=_set_pdoInput)

    def _get_pdoOutput(self):        
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(MultimeterController.RxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(MultimeterController.RxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]

    def _set_pdoOutput(self, values):        
        self.Device.sdo_write(MultimeterController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values): 
            self.Device.sdo_write(MultimeterController.RxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(MultimeterController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))

    PdoOutput = property(fget=_get_pdoOutput,fset=_set_pdoOutput)

    _pdoInLength = None
    def _get_pdoInLength(self):
        if self._pdoInLength is None:
            o = 0x24
            self._pdoInLength = [self.Device.sdo_read(a, o).value for a in [0x9000,0x9010,0x9020,0x9030]]
        return self._pdoInLength
    PdoInLength = property(fget=_get_pdoInLength)

    _pdoOutLength = None
    def _get_pdoOutLength(self):
        if self._pdoOutLength is None:
            o = 0x25
            self._pdoOutLength = [self.Device.sdo_read(a, o).value for a in [0x9000,0x9010,0x9020,0x9030]]
        return self._pdoOutLength
    PdoOutLength = property(fget=_get_pdoOutLength)

    def write(self, data):
        self.DeviceLock.acquire()
        try:
            self.Device.output = bytes(data)
        finally:
            self.DeviceLock.release()

    out = None
            
    def run(self):

        data = None

        if (self.Device.state & pysoem.PREOP_STATE) == self.Device.state:
            return data

        if (self.Device.state & pysoem.OP_STATE) != self.Device.state:
            return data

        self._lock.acquire()

        try:

            data = None

            if self.out is None:
                self.out = BeckhoffMultimeterController.RxMap()
            else:    

                buff =  BeckhoffMultimeterController.TxMap.from_buffer_copy(self.Device.input)                
                data  = {
                    'status': bin(buff.status)[2:].zfill(16),
                    'settings': bin(buff.settings)[2:].zfill(16),
                    'value': buff.value                  
                }        
            
            if self._data is not None:

                if 'control' in self._data.keys():
                    
                    cmode =  int(data['settings'],2) & int('0000000011110000',2) >> 4
                    crange = int(data['settings'],2) & int('1111111100000000',2) >> 8
                    cauto = int(data['status'],2) & int('0000000000100000',2) >> 6

                    if 'mode' in self._data['control'].keys(): cmode = self._data['control']['mode']
                    if 'range' in self._data['control'].keys(): crange = self._data['control']['range']
                    if 'auto' in self._data['control'].keys(): cauto = self._data['control']['auto']

                    control = (crange << 8) | (cmode << 4) | cauto

                    self.out.control = ctypes.c_uint16(control)
                    self.write(self.out)
                    
                    del self._data['control']

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
            EcatLogger.error(f"BeckhoffMultimeterController.output {ex}")

        finally:
            self._lock.release()
            return True
          
    def error(self, value):

        EcatLogger.debug(f"### {value}")
        EcatLogger.debug(f"    {value.__doc__}")          
