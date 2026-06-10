
from os import replace
import struct
import ctypes, time
import pysoem
import numpy as np
from threading import Lock,Event

from _EcatObject import EcatLogger


class MultimeterController(object):
    
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

    MMC_INTERFACE = 15          # 0..5V
    MMC_RESOLUTION = 640e-9     # V

    class RxMapEx:
        register = 0x1C12
        address = []

    class RxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = []

    class TxMapEx:
        register = 0x1C13
        address = [            
            0x1A00,
            0x1A01,
            ]

    class TxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [           
            ('status', ctypes.c_uint32),
            ('sample', ctypes.c_int32),
        ]

    _data = {}
    def _get_data(self): return self._data
    Data = property(fget=_get_data)    

    def _get_pdoInput(self):        
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(BeckhoffMultimeterController.TxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(BeckhoffMultimeterController.TxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]
    
    def _set_pdoInput(self, values):
        self.Device.sdo_write(BeckhoffMultimeterController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values):
            self.Device.sdo_write(BeckhoffMultimeterController.TxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(BeckhoffMultimeterController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))
    
    PdoInput = property(fget=_get_pdoInput,fset=_set_pdoInput)
        
    def _get_pdoOutput(self):        
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(BeckhoffMultimeterController.RxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(BeckhoffMultimeterController.RxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]

    def _set_pdoOutput(self, values):        
        self.Device.sdo_write(BeckhoffMultimeterController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values): 
            self.Device.sdo_write(BeckhoffMultimeterController.RxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(BeckhoffMultimeterController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))

    PdoOutput = property(fget=_get_pdoOutput,fset=_set_pdoOutput)    

    def _enablePdoAssignment(self, enable=False):
        try:
            if not enable:
                # DISABLE pdo mapping assignment
                self.Device.sdo_write(BeckhoffMultimeterController.TxMapEx.register, 0, bytes(ctypes.c_uint8(0)))
                self.Device.sdo_write(BeckhoffMultimeterController.RxMapEx.register, 0, bytes(ctypes.c_uint8(0))) 
            else:
                # ENABLE pdo mapping assignment
                self.Device.sdo_write(BeckhoffMultimeterController.TxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(BeckhoffMultimeterController.TxMapEx.address))))
                self.Device.sdo_write(BeckhoffMultimeterController.RxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(BeckhoffMultimeterController.RxMapEx.address)))) 
        except Exception as ex:
            EcatLogger.error(f"{ex}")

    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)
    
    def initConfig(self, mode='V', interface=5): 

        """                
        :param self: 
        """

        try:

            self._enablePdoAssignment(False)
        
            addr = BeckhoffMultimeterController.TxMapEx.register            
            for i,value in enumerate(BeckhoffMultimeterController.TxMapEx.address):
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))

            # outputs; write; master-slave  
            addr = BeckhoffMultimeterController.RxMapEx.register            
            for i,value in enumerate(BeckhoffMultimeterController.RxMapEx.address): 
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))  

            self._enablePdoAssignment(True)

            self.Device.sdo_write(0x8000, 0x01, bytes(ctypes.c_uint16(BeckhoffMultimeterController.MMC_INTERFACE)))
            # RTD; none
            self.Device.sdo_write(0x8000, 0x14, bytes(ctypes.c_uint16(0)))

        except pysoem.SdoError as se:
            self._initialized = False
            EcatLogger.error(f"SdoError {se}")  
        except pysoem.PacketError as pe:
            self._initialized = False
            EcatLogger.error(f"PacketError {pe}")  
        except pysoem.MailboxError as me:
            self._initialized = False
            EcatLogger.error(f"MailboxError {me}")  
        except pysoem.WkcError as we:
            self._initialized = False
            EcatLogger.error(f"WkcError {we}")  
        except Exception as ex:
            self._initialized = False
            EcatLogger.error(f"Exception {ex}")  

    _initialized = False
    def init(self):
        self._initialized = True
    
    def input(self):

        try:
                        
            if not self._initialized:      
                self.init()  

            buff = BeckhoffMultimeterController.TxMap.from_buffer_copy(self.Device.input)

            status = bin(buff.status).replace('0b','').zfill(32)[::-1]

            data = {
                'status': {
                    'available': status[0],
                    'error': status[8],
                    'underrange': status[9],
                    'overrange': status[10],
                    'invalid': status[13],
                },
                'value': buff.sample * BeckhoffMultimeterController.MMC_RESOLUTION
            }
            
            return data

        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None        

    _data = None            
    def run(self):

        data = None

        if self.Device.state != pysoem.OP_STATE:
            return data

        self._lock.acquire()

        try:

            data = self.input()
            
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
