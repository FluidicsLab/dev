
from os import replace
import struct
import ctypes, time
import pysoem
import numpy as np
from threading import Lock,Event

from _EcatObject import EcatLogger


class IOLinkController(object):

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
    

class ifmIOLinkController(IOLinkController):

    _channels = 0
    def _get_channels(self):

        return self._channels

    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)

    _data = None
        
    def _get_pdoInput(self):
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(IOLinkController.TxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(IOLinkController.TxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]
    
    def _set_pdoInput(self, values):
        self.Device.sdo_write(IOLinkController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values):
            self.Device.sdo_write(IOLinkController.TxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(IOLinkController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))

    PdoInput = property(fget=_get_pdoInput,fset=_set_pdoInput)

    def _get_pdoOutput(self):        
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(IOLinkController.RxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(IOLinkController.RxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]

    def _set_pdoOutput(self, values):        
        self.Device.sdo_write(IOLinkController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values): 
            self.Device.sdo_write(IOLinkController.RxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(IOLinkController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))

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

    def _get_linkState(self):
        # MASTER_STATE
        #   _INACTIVE, _DIGIN, _DIGOUT, _COMESTABLISH, _INITMASTER, _INITSLAVE, _PREOPERATE, _OPERATE, _STOP
        #   0x00...0x09
        o = 0x01
        return [self.Device.sdo_read(a, o).value for a in [0xa000,0xa010,0xa020,0xa030]]    
    LinkState = property(fget=_get_linkState)
            
    def run(self):

        data = None

        if (self.Device.state & pysoem.PREOP_STATE) == self.Device.state:
            return data

        if (self.Device.state & pysoem.OP_STATE) != self.Device.state:
            return data

        self._lock.acquire()

        try:

            data = bytearray(self.Device.input)            
        
            # 0..3 bytes; (0 To 2147482880) * 1
            counterSteps = int.from_bytes([data[0], data[1], data[2], data[3]], signed=False)            
            counterScale = 360. / 36000
            
            # 6..9 bytes; (-120000 To 120000) * 0.1
            revolutionSteps = int.from_bytes([data[6], data[7], data[8], data[9]], signed=True)
            revolutionScale = 0.1

            data  = {
                'counter': {
                    'steps': counterSteps,
                    'scale': counterScale
                },
                'revolution': {
                    'steps': revolutionSteps,
                    'scale': revolutionScale
                }
            }

            #EcatLogger.debug(f"{data}")

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
            EcatLogger.error(f"ifmIOLinkController.output {ex}")

        finally:
            self._lock.release()
            return True
          
    def error(self, value):

        EcatLogger.debug(f"### {value}")
        EcatLogger.debug(f"    {value.__doc__}")          
