
from threading import Lock, Event, Thread
import ctypes, time, struct
from types import SimpleNamespace
import pysoem

import numpy as np

from _EcatObject import EcatLogger
from _EcatSeverity import SEVERITY_VERBOSE, EcatSeverityController


# to configure and reset by TC


class DataMap(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('i1', ctypes.c_int32),
        ('i2', ctypes.c_int32),
        ('i3', ctypes.c_int32)    ]


class NOVRAMProfile:
    
    control = ['0x0001','0x0002','0x0004']    
    control_name = ['STORE','LOCK','UNLOCK']

    @staticmethod
    def __control__(value):
        for i,c in enumerate(NOVRAMProfile.control):
            if int(value,2) == int(c,16):
                return value, NOVRAMProfile.control_name[i]
        return value, 'UNKNOWN'
           
    status = ['0x0001',
              '0x0008',
              '0x0100',
              '0x0200',
              '0x0400']        
    status_name = ['STORED',
                   'FAULT',
                   'LOCKED',
                   'INITIALIZED',
                   'RESTORED']
    
    @staticmethod
    def __status__(value):
        return ",".join([f"{NOVRAMProfile.status_name[i]}" 
                        for i,s in enumerate(NOVRAMProfile.status) 
                            if ((int(s,16) & value) == int(s,16)) and (int(s,16) not in [0])
                        ])
        

class BeckhoffMemoryController(object):

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

    _severity = SEVERITY_VERBOSE
    
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
    
    def toggle(self):
        pass

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

    def isValid(self):
        return False

    def severityFunc(self, value):
        pass    

    def controllerFunc(self, value):
        pass


class NOVRAMMemoryController(BeckhoffMemoryController):

    _reader: Thread = None
    _writer: Thread = None

    _upload: Thread = None

    TIMEOUT_SLAVE_STATE = 5.0
    TIMEOUT_STATE_CHECK = 50_000

    TIMEOUT_ACYCLIC_READ = 0.05     # s
    TIMEOUT_ACYCLIC_WRITE = 0.05    # s

    SHIFT_TIME = 250_000            # ns
    CYCLE_TIME = 10_000_000         # ns

    UPLOAD_BEGIN = 0x0001
    UPLOAD_END = 0x0000
    UPLOAD_TIMEOUT = 0.05     # s

    MODE = 'ACYCLIC'

    #
    # 
    # control   0x0001 store data
    #           0x0002 lock novram objects
    #           0x0004 unlock novram objects
    #

    class RxMapEx:
        register = 0x1C12
        address = [
            0x1601,
            0x1600
            ]
      
    class RxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            ('control', ctypes.c_uint16),            
            ('data', DataMap)
        ]

    #
    # 
    # status    0x0001 data stored
    #           0x0008 no data written
    #           0x0100 novram objects locked
    #           0x0200 novram initialized
    #           0x0400 novram objects restored
    #           0xn000 acyclic data stored

    class TxMapEx:
        register = 0x1C13
        address = [
            0x1A01,
            0x1A00
            ]

    class TxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            ('status', ctypes.c_uint16),
            ('data', DataMap)
        ]  
    
    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)

    def release(self):
        super().release()

    def _disablePdoAssignment(self):
        self._enablePdoAssignment(False)

    def _enablePdoAssignment(self, enable=True):
        try:
            if not enable:
                # DISABLE pdo mapping assignment
                self.Device.sdo_write(NOVRAMMemoryController.TxMapEx.register, 0, bytes(ctypes.c_uint8(0)))
                self.Device.sdo_write(NOVRAMMemoryController.RxMapEx.register, 0, bytes(ctypes.c_uint8(0))) 
            else:
                # ENABLE pdo mapping assignment
                self.Device.sdo_write(NOVRAMMemoryController.TxMapEx.register, 0, 
                                      bytes(ctypes.c_uint8(len(NOVRAMMemoryController.TxMapEx.address))))
                self.Device.sdo_write(NOVRAMMemoryController.RxMapEx.register, 0, 
                                      bytes(ctypes.c_uint8(len(NOVRAMMemoryController.RxMapEx.address)))) 
        except Exception as ex:
            EcatLogger.error(f"{ex}")

    def setState(self, state):
        rc = True
        self.Device.state = state
        timeout = NOVRAMMemoryController.TIMEOUT_SLAVE_STATE
        start_time = time.time()
        while self.Device.state_check(state, timeout=NOVRAMMemoryController.TIMEOUT_STATE_CHECK) != state:
            if time.time() - start_time > timeout:
                rc = False
                break
        return rc
    
    def hasState(self, state):
        return self.Device.state & state == state
        
    _values = [None] * 3

    def _get_controlWord(self):
        try:
            buff =  NOVRAMMemoryController.RxMap.from_buffer_copy(self.Device.output)                
            return bin(buff.control)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    def _set_controlWord(self, value):
        try:
            out = NOVRAMMemoryController.RxMap()
            out.data.i1 = ctypes.c_int32(self._values[0])
            out.data.i2 = ctypes.c_int32(self._values[1])
            out.data.i3 = ctypes.c_int32(self._values[2])            
            out.control = ctypes.c_uint16(value)            
            self.write(out)   
        except Exception as ex:
            EcatLogger.error(f"{ex}")

    ControlWord = property(fget=_get_controlWord,fset=_set_controlWord)    

    def _get_locked(self):
        return ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(0xF100,0x03)).value
    Locked = property(fget=_get_locked)

    _initialized = False

    def initConfig(self): 

        """                
        :param self: 
        """
        
        try:

            #
            # PDO
            #

            self._disablePdoAssignment()

            # RxPDO
            # outputs; write; master-slave  

            addr = NOVRAMMemoryController.RxMapEx.register            
            for i,value in enumerate(NOVRAMMemoryController.RxMapEx.address): 
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)), True)

            # TxPDO
            # inputs; read; slave-master

            addr = NOVRAMMemoryController.TxMapEx.register            
            for i,value in enumerate(NOVRAMMemoryController.TxMapEx.address):
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)), True)  

            self._enablePdoAssignment()
            # ESM PREOP -> SAFEOP RxPDO effective
            # ESM SAFEOP -> OP TxPDO effective
            
            
            #
            # startup
            #

            if NOVRAMMemoryController.MODE == 'ACYCLIC':

                self.Device.sdo_write(0xF200, 0x02, bytes(ctypes.c_uint16(0)))              # unlock
                # 4 items a 4 byte                
                self.Device.sdo_write(0x2F00, 0x00, bytes([0x03,0x00, 0x04,0x00, 0x04,0x00, 0x04,0x00]), True)
                self.Device.sdo_write(0xF200, 0x02, bytes(ctypes.c_uint16(1)))              # lock                


            #
            # timing
            #

            shift_time = NOVRAMMemoryController.SHIFT_TIME
            cycle_time = NOVRAMMemoryController.CYCLE_TIME
            EcatLogger.debug(f"cycle time {cycle_time}; shift time {shift_time} {self.__class__.__name__}")
            
            self.Device.dc_sync(act=True, 
                                sync0_cycle_time=cycle_time, sync0_shift_time=shift_time, 
                                sync1_cycle_time=cycle_time
                                )            

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
    
    def init(self):

        self._initialized = False
        
        try:

            if NOVRAMMemoryController.MODE == 'ACYCLIC':

                self._reader = Thread(target=self.acyclicInput)
                self._reader.start()
                self._writer = Thread(target=self.acyclicOutput)
                self._writer.start() 

            else:

                self._upload = Thread(target=self.upload)
                self._upload.start()

            self._initialized = True

        except pysoem.SdoError as se:
            EcatLogger.error(f"SdoError {se}")  
        except pysoem.PacketError as pe:
            EcatLogger.error(f"PacketError {pe}")  
        except pysoem.MailboxError as me:
            EcatLogger.error(f"MailboxError {me}")  
        except pysoem.WkcError as we:
            EcatLogger.error(f"WkcError {we}")  
        except Exception as ex:
            EcatLogger.error(f"Exception {ex}")  

    def _get_statusWord(self):
        try:
            buff = NOVRAMMemoryController.TxMap.from_buffer_copy(self.Device.input)                
            return bin(buff.status)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    StatusWord = property(fget=_get_statusWord)

    def _get_statusRegister(self):
        try:            
            return bin(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0xF100,0x01)).value)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    StatusRegister = property(fget=_get_statusRegister)

    _size = None
    def _get_size(self):
        if self._size is None:
            self._size = [0] * ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(0x2F00,0x00)).value
            for i in range(len(self._size)):
                self._size[i] = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(0x2F00,i+1)).value
        return self._size    
    def _set_size(self, data):
        self.Device.sdo_write(0xF200, 0x02, bytes(ctypes.c_uint16(0)))              # unlock        
        # 3 items a 4 byte [0x03,0x00, 0x04,0x00, 0x04,0x00, 0x04,0x00]
        size = [len(data), 0x00]
        for d in data:
            size += [d, 0x00] 
        self.Device.sdo_write(0x2F00, 0x00, bytes(data), True)        
        self.Device.sdo_write(0xF200, 0x02, bytes(ctypes.c_uint16(1)))              # lock    
        self._size = None    
    Size = property(fget=_get_size, fset=_set_size)

    _memoryLock = Lock()

    _input = []    
    def acyclicInput(self):

        EcatLogger.debug(f"start computing acyclic read @ {self.__class__.__name__}")

        while not self._exit.is_set():

            self._memoryLock.acquire()
            try:
                if len(self._input) == 0:
                    addr = 0x2000
                    for offset in self.Size:
                        self._input.append(ctypes.c_int32.from_buffer_copy(self.Device.sdo_read(addr,0x00)).value)
                        addr += 2 * offset
            except Exception as ex:
                EcatLogger.error(f"acyclicInput {ex}")
            finally:
                self._memoryLock.release()   

            self._exit.wait(NOVRAMMemoryController.TIMEOUT_ACYCLIC_READ)

    _output = []
    def acyclicOutput(self):

        EcatLogger.debug(f"start computing acyclic write @ {self.__class__.__name__}")

        while not self._exit.is_set():
            
            if len(self._output) > 0:

                self._memoryLock.acquire()
                try:
                    addr = 0x2000
                    for i,offset in enumerate(self.Size):
                        self.Device.sdo_write(addr, 0x00, bytes(ctypes.c_int32(self._output[i])))
                        addr += 2 * offset
                    
                    self._output = []
                    self._input = []

                except Exception as ex:
                    EcatLogger.error(f"acyclicOutput {ex}")

                finally:
                    self._memoryLock.release()
            
            self._exit.wait(NOVRAMMemoryController.TIMEOUT_ACYCLIC_WRITE)

    def input(self):

        # pdo read
        try:

            if not self._initialized:      
                self.init()    

            data = None

            if NOVRAMMemoryController.MODE == 'CYCLIC':

                if ctypes.sizeof(NOVRAMMemoryController.TxMap) == len(self.Device.input):

                    buff =  NOVRAMMemoryController.TxMap.from_buffer_copy(self.Device.input)

                    if self._values[0] is None:
                        self._values[0] = buff.i1
                    if self._values[1] is None:
                        self._values[1] = buff.i2
                    if self._values[2] is None:
                        self._values[2] = buff.i3
                    
                    status = bin(buff.status)[2:].zfill(16)  
                    status_text = NOVRAMProfile.__status__(int(status,2))
                                                
                    data  = {

                        'status': {
                            'value':status, 
                            'text': status_text,
                        },

                        'mode': NOVRAMMemoryController.MODE,

                        'values': self._values,
                        
                        'modified': time.time_ns()
                    }
            else:

                status = self.StatusRegister
                status_text = NOVRAMProfile.__status__(int(status,2))

                data  = {

                        'status': {
                            'value':status, 
                            'text': status_text,
                        },

                        'mode': NOVRAMMemoryController.MODE,

                        'values': self._input,
                        
                        'modified': time.time_ns()
                    }

            return data

        except Exception as ex:
            EcatLogger.error(f"input {ex}")
            return None
                    
    def write(self, data):
        # pdo write
        self.DeviceLock.acquire()
        try:
            output = NOVRAMMemoryController.RxMap()
            ctypes.memmove(ctypes.byref(output), ctypes.byref(data), ctypes.sizeof(NOVRAMMemoryController.RxMap))
            self.Device.output = bytes(output)
        except Exception as ex:
            EcatLogger.error(f"write {ex}")
        finally:
            self.DeviceLock.release()     

    _data = None   

    def run(self):

        data = None

        if self.Device.state != pysoem.OP_STATE:
            return data

        self._lock.acquire()

        try:            

            data = self.input()

            if self._data is not None:

                if 'data' in self._data.keys() and self._data['data'] is not None:
                    for i in range(len(self._values)):
                        self._values[i] = self._data['data'][i]                    
                    self._update = True               
                    self._data['data'] = None                
                                    
        except Exception as ex:
            EcatLogger.error(f"run {ex}")
        
        finally:
            self._lock.release()

        return data

    def output(self, data):
        rc = False
        if not self.Enabled:
            return rc        
        self._lock.acquire()
        try:
            if self._data is None:
                self._data = dict()
            self._data.update(data)
            rc = True
        except Exception as ex:
            EcatLogger.error(f"output {ex}")
        finally:
            self._lock.release()        
        return rc
    
    _update = False
    def upload(self):

        EcatLogger.debug(f"start computing cyclic upload @ {self.__class__.__name__}")

        while not self._exit.is_set():
            
            if self._update:
                self.ControlWord = NOVRAMMemoryController.UPLOAD_BEGIN
                self._exit.wait(NOVRAMMemoryController.UPLOAD_TIMEOUT)
                self.ControlWord = NOVRAMMemoryController.UPLOAD_END
                self._update = False
            else:
                self._exit.wait(NOVRAMMemoryController.UPLOAD_TIMEOUT)
    
    def callback(self, *args):

        self._lock.acquire()
        
        try:
            
            pass

        except Exception as ex:
            EcatLogger.error(f"callback {ex}")
        
        finally:
            self._lock.release()
                            
    def controllerFunc(self, value):
        """
        :param self: 
        :param value: 
        """
        self._lock.acquire()
        try:  
            pass
        finally:
            self._lock.release()
            
    def isValid(self):
        return EcatSeverityController.isValid(self._severity)
    
    _severity = []
    def severityFunc(self, value):
        """                
        :param self: 
        :param value: 
        """
        self._severity = value        
        if not self.isValid():
            pass