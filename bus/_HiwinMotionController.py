from math import trunc
import ctypes, time
from typing import final
import pysoem
import numpy as np
from threading import Lock,Event,Thread
from types import SimpleNamespace

from _EcatObject import EcatLogger

from _EcatSeverity import SEVERITY_VERBOSE, EcatSeverityController, SeverityLogger
from _EcatStates import EcatStates


class Ed1fPidController(object):

    TIMEOUT_CONTROL = 0.1
    FRACTION = 50
    MODE_DEFAULT = 'p'

    _scaler = {
        'input': {
            'p': { "low": 0, "high": 700 },                 # bar   (pressure)
            'd': { "low": 0, "high": 4_294_967_295_000 }    # cycle (distance)         
        },
        'output': { "low": 0, "high": 838_633_324 }         # inc/s (velocity)
    }

    _limit = {
        'output': { "low": -838_633_324 * 8/9, "high": 838_633_324 * 8/9 }  # inc/s (velocity)
    }

    _lock: Lock = Lock()
    _exit = Event()

    _task: Thread = None

    _processvalue = {}
    _setpoint = {}

    _mode = MODE_DEFAULT                                # p
    def _get_mode(self):
        return self._mode
    def _set_mode(self, value):
        self.reset()
        self._mode = value
    Mode = property(fget=_get_mode,fset=_set_mode)

    _enabled = False
    def _get_enabled(self):
        return self._enabled
    Enabled = property(fget=_get_enabled)

    _error = 0.0
    _demand = 0.0
    _integral = []

    # Kp, Ki, Kd, dt
    _params = {
        'p': [0.5, 0.001, 0.0001, 0.1],
        'd': [10.0, 0.001, 0.0001, 0.1]
    }

    _factor = {
        'p': +1,
        'd': -1
    }

    _updatable = True

    _callback = None

    _source = []
    def _set_source(self, values: list):
        self._source = []
        for value in values:
            self._source.append(SimpleNamespace(**value))
            self._scaler['input'][value['key']] = {
                "low": value["low"], 
                "high": value["high"]
            }
            self._processvalue[value['key']] = 0
            self._setpoint[value['key']] = 0
            
    def _get_source(self):
        return self._source
    Source = property(fset=_set_source, fget=_get_source)

    def __init__(self, callback):
        super().__init__()
        self._callback = callback
        self._task = Thread(target=self.compute)
        self._task.start()

    def release(self):
        self._exit.set()

    def config(self, config):
        self._lock.acquire()
        try:
            EcatLogger.debug(f"update config {config}")

            if 'mode' in config.keys() and config['mode'] is not None:
                self.Mode = config['mode']

            if 'setpoint' in config.keys() and config['setpoint'] is not None:
                self._setpoint[self.Mode] = config['setpoint']

            if 'params' in config.keys() and config['params'] is not None:
                self._params[self.Mode] = config['params'].copy()

            if 'enabled' in config.keys() and config['enabled'] is not None:
                self._enabled = config['enabled']

            if 'reset' in config.keys():
                self.reset()
                
            if 'updatable' in config.keys() and config['updatable'] is not None:
                self._updatable = config['updatable']

            if 'processvalue' in config.keys() and config['processvalue'] is not None:
                self._processvalue[self.Mode] = config['processvalue']

        finally:
            self._lock.release()

    def update(self, key, value=None):
        self._lock.acquire()
        try:
            if value is not None:
                self._processvalue[key] = value
            else:
                self._enabled = False
        finally:
            self._lock.release()

    def reset(self):
        self._error = 0.0
        self._demand = 0.0
        self._integral = []
        self._mode = Ed1fPidController.MODE_DEFAULT

    def compute(self):

        def scale(value):
            return (value - self._scaler['input'][self._mode]['low']) / (self._scaler['input'][self._mode]['high'] - self._scaler['input'][self._mode]['low'])
        
        def unscale(value):
            return self._scaler['output']['low'] + (self._scaler['output']['high'] - self._scaler['output']['low']) * value

        def limit(value): 
            return max(self._limit['output']['low'], min(self._limit['output']['high'], value))

        enabled = False
        zero = False

        while not self._exit.is_set():

            if enabled and not self._enabled:
                if self._callback is not None:
                    self._callback(None)

            if self._enabled:

                self._lock.acquire()
                try:

                    sp = scale(self._setpoint[self.Mode])
                    pv = scale(max(0, self._processvalue[self.Mode]))

                    err = (pv - sp) * self._factor[self.Mode]

                    params = self._params[self.Mode]

                    kp = params[0] * err
                    ki = params[1] * err * params[3]
                    kd = params[2] * (err - self._error) / params[3]

                    self._integral.append(ki)                    
                    while len(self._integral) > Ed1fPidController.FRACTION:
                        self._integral.pop(0)
                    ki = sum(self._integral)
                    self._error = err

                    dv = kp + ki + kd
                    dv = unscale(dv)
                    dv = limit(dv)
                
                    if self._callback is not None:
                        if self._demand != dv:
                            self._callback(dv, err)
                            zero = False
                        else:
                            if dv == 0.0 and not zero:
                                self._callback(dv, err)
                                zero = True

                    self._demand = dv

                except Exception as ex:
                    EcatLogger.error(f"pid compute {ex}")

                finally:
                    self._lock.release()

            self._exit.wait(Ed1fPidController.TIMEOUT_CONTROL)

            enabled = self._enabled


class Ed1fProfileMode:

    MODE_NONE               = 0

    MODE_PP                 = 1     # profile position
    MODE_VV                 = 2     # velocity
    MODE_PV                 = 3     # profile velocity
    MODE_TQ                 = 4     # profile torque

    MODE_HM                 = 6     # homing

    MODE_CSP                = 8     # cyclic synchronous position
    MODE_CSV                = 9     # cyclic synchronous velocity
    MODE_CST                = 10    # cyclic synchronous torque
    
    name = [
        'none',
        'profile position',
        'velocity',
        'profile velocity',
        'profile torque',
        'unknown',
        'homing',
        'unknown',
        'cyclic synchronous position', 
        'cyclic synchronous velocity', 
        'cyclic synchronous torque'
        ]
    
    @staticmethod
    def __str__(value: int):                
        return Ed1fProfileMode.name[value] if value >=0 and value < len(Ed1fProfileMode.name) else 'unknown'
    
    @staticmethod
    def valid(value):
        return (value >= Ed1fProfileMode.MODE_CSP and value <= Ed1fProfileMode.MODE_CST) or Ed1fProfileMode.MODE_NONE == value
    
    @staticmethod
    def velocity(value):
        return value == Ed1fProfileMode.MODE_CSV

    @staticmethod
    def position(value):
        return value == Ed1fProfileMode.MODE_CSP
    
    @staticmethod
    def torque(value):
        return value == Ed1fProfileMode.MODE_CST
    
    
class Ed1fProfile:

    # control word LoByte
    FAULT_RESET             = '10000000'    # 1xxx xxxx 15
    SHUTDOWN                = '00000110'    # 0xxx x110 2,6,8
    SWITCH_ON               = '00000111'    # 0xxx 0111 3,5
    ENABLE_OPERATION        = '00001111'    # 0xx0 1111 4

    control = ['10000000','00000110','00000111','00001111']
    control_name = ['FAULT_RESET','SHUTDOWN','SWITCH_ON','ENABLE_OPERATION']

    @staticmethod
    def __control__(value):
        for i,c in enumerate(Ed1fProfile.control):
            if int(value,2) == int(c,2):
                return value, Ed1fProfile.control_name[i]
        return value, 'UNKNOWN'
    
    # status word
    NOT_READY_TO_SWITCH_ON  = 0     # 0000 0000 0000 0000
    READY_TO_SWITCH_ON      = 1     # 0000 0000 0000 0001
    SWITCHED_ON             = 2     # 0000 0000 0000 0010
    OPERATION_ENABLED       = 4     # 0000 0000 0000 0100
    FAULT                   = 8     # 0000 0000 0000 1000    
    VOLTAGE_DISABLED        = 16    # 0000 0000 0001 0000    
    QUICK_STOP              = 32    # 0000 0000 0010 0000    
    SWITCH_ON_DISABLED      = 64    # xxx0 xxxx x1xx 0000
    WARNING                 = 128   # 0000 0000 1000 0000

    REMOTE                  = 512   # 0000 0010 0000 0000
    TARGET_REACHED          = 1024  # 0000 0100 0000 0000        
    LIMIT_ACTIVE            = 2_048 # 0000 1000 0000 0000

    
    status = [
        NOT_READY_TO_SWITCH_ON, READY_TO_SWITCH_ON, SWITCHED_ON, OPERATION_ENABLED, 
        FAULT, QUICK_STOP, SWITCH_ON_DISABLED, WARNING, LIMIT_ACTIVE]
    
    status_name = [
        'NOT_READ_TO_SWITCH_ON','READY_TO_SWITCH_ON', 'SWITCHED_ON', 'OPERATION_ENABLED', 
        'FAULT', 'QUICK_STOP', 'SWITCH_ON_DISABLED', 'WARNING', 'LIMIT_ACTIVE']
    
    @staticmethod
    def __status__(value):
        return ",".join([f"{Ed1fProfile.status_name[i]}" 
                        for i,s in enumerate(Ed1fProfile.status) 
                            if ((s & value) == s) and (s not in [0])
                        ])
    
    @staticmethod
    def __translate__(value, src, dst):
        
        def constant(f):
            def fset(self, value):
                raise TypeError
            def fget(self):
                return f()
            return property(fget, fset)

        class _iri(object):
            @constant
            def value():
                gearBoxGearRatio = 1_000.
                spindlePitch = 5.
                timingBeltTransmissionGearRatio = 2.
                motorIncrementPositions = 8_388_608
                cylinderDiameter = 15.                
                cylinderArea = cylinderDiameter**2 * np.pi / 4.
                transmission = spindlePitch / (timingBeltTransmissionGearRatio * gearBoxGearRatio)
                injectionRateRotation = transmission * cylinderArea
                return injectionRateRotation / motorIncrementPositions

        iri = _iri()  
        
        if src == 'mulmin' and dst == 'incs':
            return round(value / iri.value, 0)
        if src == 'incs' and dst == 'mulmin':
            return value * iri.value


class Ed1fProfilePosition:

    UINT32_MAX = 4_294_967_295

    INT32_MAX = 2_147_483_647
    INT32_MIN = -2_147_483_648

    @staticmethod
    def merge(value):
        return value[0] * Ed1fProfilePosition.UINT32_MAX + value[1] + Ed1fProfilePosition.INT32_MAX
    
    @staticmethod
    def split(value):
        mtb = trunc(value / Ed1fProfilePosition.UINT32_MAX)
        stb = (value - mtb) * Ed1fProfilePosition.UINT32_MAX - Ed1fProfilePosition.INT32_MAX
        return [mtb, stb]


class HiwinMotionController(object):

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
    

class Ed1fMotionController(HiwinMotionController):

    SHIFT_TIME = 250_000        # ns
    CYCLE_TIME = 10_000_000     # ns

    class RxMapEx:
        register = 0x1C12
        address = [0x1601]    

    class RxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            ('control', ctypes.c_uint16),
            ('mode', ctypes.c_uint8),
            ('velocity', ctypes.c_int32),
            ('digital', ctypes.c_uint32)
        ]

    class TxMapEx:
        register = 0x1C13
        address = [0x1A01]        

    class TxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [            
            ('errorcode', ctypes.c_uint16),
            ('status', ctypes.c_uint16),
            ('mode', ctypes.c_uint8),
            ('position', ctypes.c_int32),
            ('velocity', ctypes.c_int32),
            ('torque', ctypes.c_int16),
            ('digital', ctypes.c_uint32)
        ]  
   
    UINT32_MAX  = 4_294_967_295
    TORQUE_MAX  = 8000
    RPM_MAX     = 10000

    _controller: Ed1fPidController = None

    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)
        self._controller = Ed1fPidController(self.controllerFunc)

    def release(self):
        super().release()
        if self._controller is not None:
            self._controller.release()

    _mode = None
    def _get_mode(self):
        try:
            if len(self.Device.input) == ctypes.sizeof(Ed1fMotionController.TxMap):
                buff = Ed1fMotionController.TxMap.from_buffer_copy(self.Device.input)
                self._mode = buff.mode
            else:
                self._mode = Ed1fProfileMode.MODE_CSV
        except Exception as ex:
            EcatLogger.error(f"mode {ex}")
        return self._mode    
    def _set_mode(self, value):
        try:                        
            out = Ed1fMotionController.RxMap()
            out.control = ctypes.c_uint16(int(self.ControlWord,2))
            out.velocity = ctypes.c_int32(self.VelocitySetpoint)
            out.mode = ctypes.c_uint8(value)
            self.write(out)            
        except Exception as ex:
            EcatLogger.error(f"mode {ex}")
    Mode = property(fget=_get_mode,fset=_set_mode)             

    def _get_controlWord(self):
        try:
            buff =  Ed1fMotionController.RxMap.from_buffer_copy(self.Device.output)                
            return bin(buff.control)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"control {ex}")
            return None
    def _set_controlWord(self, value):
        try:            
            EcatLogger.info(f"control {Ed1fProfile.__control__(value)}")
            out = Ed1fMotionController.RxMap()
            out.control = ctypes.c_uint16(int(value,2))
            out.velocity = ctypes.c_int32(self.VelocitySetpoint)
            out.mode = self.Mode
            self.write(out)            
        except Exception as ex:
            EcatLogger.error(f"control {ex}")
    ControlWord = property(fget=_get_controlWord, fset=_set_controlWord) 

    def _get_velocity(self):
        try:
            buff = Ed1fMotionController.TxMap.from_buffer_copy(self.Device.input)                
            return buff.velocity
        except Exception as ex:
            EcatLogger.error(f"velocity {ex}")
            return None
    def _set_velocity(self, value):
        try:
            out = Ed1fMotionController.RxMap()
            out.control = ctypes.c_uint16(int(self.ControlWord,2))
            out.velocity = ctypes.c_int32(self.VelocitySetpoint)
            out.mode = self.Mode
            self.write(out)            
        except Exception as ex:            
            EcatLogger.error(f"velocity {ex}")
    Velocity = property(fset=_set_velocity,fget=_get_velocity)

    _velocitySetpoint = 0
    def _get_velocitySetpoint(self):
        return self._velocitySetpoint
    def _set_velocitySetpoint(self,value):
        self._velocitySetpoint = value
    VelocitySetpoint = property(fget=_get_velocitySetpoint, fset=_set_velocitySetpoint)

    _firmware = None
    def _get_firmware(self):
        if self._firmware is None:
            # firmware major.medium.minor
            self._firmware = [                
                ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x4097,0x00)).value,
                ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x2502,0x00)).value
                ]
        return self._firmware
    Firmware = property(fget=_get_firmware)

    _velocityLimit = None # inc/s
    def _get_velocityLimit(self):
        if self._velocityLimit is None:
            self._velocityLimit = 838_633_324            
        return self._velocityLimit    
    VelocityLimit = property(fget=_get_velocityLimit)  

    _multiturn = 0
    def _get_multiturn(self):
        return self._multiturn
    def _set_multiturn(self, value):
        self._multiturn = value
    Multiturn = property(fget=_get_multiturn, fset=_set_multiturn)

    _singleTurn = 0
    def _get_singleTurn(self):
        return self._singleTurn - Ed1fProfilePosition.INT32_MAX
    def _set_singleTurn(self, value):
        self._singleTurn = value + Ed1fProfilePosition.INT32_MAX
    Singleturn = property(fget=_get_singleTurn, fset=_set_singleTurn)

    _positionOffset = 0
    def _get_positionOffset(self):        
        return self._positionOffset - Ed1fProfilePosition.INT32_MAX
    def _set_positionOffset(self, value):
        self._positionOffset = value + Ed1fProfilePosition.INT32_MAX
    PositionOffset = property(fget=_get_positionOffset,fset=_set_positionOffset)    
    
    def _get_position(self):        
        return Ed1fProfilePosition.merge([self.Multiturn, self.Singleturn])
    def _set_position(self, value):
        self._multiturn, self._singleTurn = Ed1fProfilePosition.split(value)
    Position = property(fget=_get_position,fset=_set_position)

    def initEx(self, source=[]): 
        """                
        :param self: 
        :param source: [] with dict with keys like { terminal, address, key, low, high }
        """
        if self._controller is not None:
            self._controller.Source = source.copy()

    def _enablePdoAssignment(self, enable=False):
        try:
            if not enable:
                # DISABLE pdo mapping assignment
                self.Device.sdo_write(Ed1fMotionController.TxMapEx.register, 0, bytes(ctypes.c_uint8(0)))
                self.Device.sdo_write(Ed1fMotionController.RxMapEx.register, 0, bytes(ctypes.c_uint8(0))) 
            else:
                # ENABLE pdo mapping assignment
                self.Device.sdo_write(Ed1fMotionController.TxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(Ed1fMotionController.TxMapEx.address))))
                self.Device.sdo_write(Ed1fMotionController.RxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(Ed1fMotionController.RxMapEx.address)))) 
        except Exception as ex:
            EcatLogger.error(f"pdo {ex}")    

    def reset(self):    
        try:
            pass
        except Exception as ex:        
            EcatLogger.error(f"reset {ex}")  

    def clear(self):
        try:
            pass
        except Exception as ex:        
            EcatLogger.error(f"clear {ex}")  
    
    def initConfig(self): 
        
        """                
        :param self: 
        """
        
        try:

            self.Device.sdo_write(0x6060, 0x0, bytes(ctypes.c_int8(Ed1fProfileMode.MODE_CSV)))
            # accel
            value = int(0.9*Ed1fMotionController.UINT32_MAX)
            self.Device.sdo_write(0x6083, 0, bytes(ctypes.c_uint32(value)))
            self.Device.sdo_write(0x60C5, 0, bytes(ctypes.c_uint32(value)))
            # decel            
            value = int(0.9*Ed1fMotionController.UINT32_MAX)
            self.Device.sdo_write(0x6084, 0, bytes(ctypes.c_uint32(value)))
            self.Device.sdo_write(0x60C6, 0, bytes(ctypes.c_uint32(value)))
            # quick stop
            value = int(0.1*Ed1fMotionController.UINT32_MAX)
            self.Device.sdo_write(0x6067, 0, bytes(ctypes.c_uint32(value)))
            self.Device.sdo_write(0x6068, 0, bytes(ctypes.c_uint32(value)))

            self._enablePdoAssignment(False) 

            #
            # PDO
            #

            # inputs; read; slave-master
            addr = Ed1fMotionController.TxMapEx.register            
            for i,value in enumerate(Ed1fMotionController.TxMapEx.address):
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))

            # outputs; write; master-slave  
            addr = Ed1fMotionController.RxMapEx.register            
            for i,value in enumerate(Ed1fMotionController.RxMapEx.address): 
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))
            
            self._enablePdoAssignment(True)
            # ESM PREOP -> SAFEOP TxPDO effective
            # ESM SAFEOP -> OP TxPDO effective

            self.Device.sdo_write(0x6072, 0, bytes(ctypes.c_uint16(Ed1fMotionController.TORQUE_MAX)))
            self.Device.sdo_write(0x2502, 0, bytes(ctypes.c_uint16(Ed1fMotionController.RPM_MAX)))

            shift_time = Ed1fMotionController.SHIFT_TIME
            cycle_time = Ed1fMotionController.CYCLE_TIME
            EcatLogger.debug(f"cycle time {cycle_time}; shift time {shift_time}")
            
            self.Device.dc_sync(act=True, 
                                sync0_cycle_time=cycle_time, sync0_shift_time=shift_time, 
                                sync1_cycle_time=cycle_time
                                )
            
            _ = self.VelocityLimit
            _ = self.Firmware
            
            self._initialized = True  

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


    def input(self):

        # pdo read
        try:

            buff =  Ed1fMotionController.TxMap.from_buffer_copy(self.Device.input)

            self.Singleturn = buff.position
                        
            status = bin(buff.status)[2:].zfill(16)  
            status_text = Ed1fProfile.__status__(int(status,2))
            
            data  = {
                'mode': {
                    'raw': buff.mode,
                    'text': Ed1fProfileMode.__str__(buff.mode)
                },
                'position': {
                    'raw': buff.position,
                    'value': [self.Multiturn, self.Singleturn]
                },
                'velocity':{
                    'raw': buff.velocity,
                    'value': Ed1fProfile.__translate__(buff.velocity, 'incs', 'mulmin')
                },
                'info': {
                    'error': buff.errorcode
                },
                'torque': {
                    'raw': buff.torque                    
                },
                'status': {
                    'value':status, 
                    'text': status_text,
                },
                'encoder': { 
                    'type': 'singleturn',
                    'turnbits': [0, 32],
                    'firmware': self.Firmware
                },
                # severity callback position
                '0x01': { 'd': self.Position }
            }

            return data

        except Exception as ex:
            EcatLogger.error(f"input {ex}")
            return None   

    _data = None

    def run(self):

        self._lock.acquire()

        data = None

        try:

            data = self.input()
        
            if self._data is not None:

                if 'mode' in self._data.keys() and self._data['mode'] is not None:   
                    self.Mode = self._data['mode']
                    self._data['mode'] = None

                if 'command' in self._data.keys() and self._data['command'] is not None:                    
                    self.ControlWord = self._data['command']
                    self._data['command'] = None

                if 'velocity' in self._data.keys() and self._data['velocity'] is not None: 
                    self.VelocitySetpoint = self._data['velocity']
                    self.Velocity = self.VelocitySetpoint
                    self._data['velocity'] = None

                if 'position' in self._data.keys() and self._data['position'] is not None:   
                    # unused
                    self._data['position'] = None

                if 'offset' in self._data.keys() and self._data['offset'] is not None:   
                    self.PositionOffset = self._data['offset']
                    self._data['offset'] = None

                # pid controller
                if 'control' in self._data.keys() and self._data['control'] is not None:
                    if self._controller is not None: 
                        enabled = self._controller.Enabled
                        self._controller.config(self._data['control'])   
                        if enabled and not self._controller.Enabled:
                            self.VelocitySetpoint = 0
                            self.Velocity = self.VelocitySetpoint
                            self.ControlWord = Ed1fProfile.SWITCH_ON
                    self._data['control'] = None

        except Exception as ex:
            EcatLogger.error(f"run {ex}")
        
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
            if self._data is None:
                self._data = dict()
            self._data.update(data)
        except Exception as ex:
            EcatLogger.error(f"output {ex}")
        finally:
            self._lock.release()        
        return True
            
    _callbackData = None

    def callback(self, *args):
        """          
        update controller data      
        :param self: 
        :param args: 
        """        
        self._lock.acquire()
        try:            
            
            name = f"{args[0]['name']}.{args[0]['index']}"            
            value = args[0]['value']['value'] if 'value' in args[0]['value'].keys() else None            
            if value is not None:

                if 'data' in value.keys() and len(value['data']) > 0:
                    self._callbackData = value['data'].copy()[:2]
                    self.Multiturn = value['data'][0]
                    self.Singleturn = value['data'][1]
                                            
                if self._controller is not None and self._controller._updatable and len(self._controller.Source) != 0:
                    for source in self._controller.Source:
                        if name == source.name:
                            addr = source.addr
                            key = source.key
                            if 'value' in list(args[0]['value']):
                                if value:
                                    if addr in value.keys():
                                        data = value[addr]
                                        if key in data.keys():                                            
                                            if 'd' == key:
                                                if self._callbackData is not None:
                                                    self._controller.update(key, Ed1fProfilePosition.merge(self._callbackData))
                                            else:
                                                self._controller.update(key, data[key])   
                                        
        except Exception as ex:
            EcatLogger.error(f"callback {ex}")
        finally:
            self._lock.release()

    def controllerFunc(self, value, error=0):
        """
        call back from PID        
        :param self: 
        :param value: velocity inc/s
        :param error: error py pid controller calc.
        """
        self._lock.acquire()
        try:  
            EcatLogger.debug(f"{value} {error} {self.Multiturn} {self.Singleturn}")
            self._data.update({
                'velocity': round(value)
            })
        finally:
            self._lock.release()

    def isValid(self):
        return EcatSeverityController.isValid(self._severity)
    
    def severityFunc(self, value):
        self._severity = value        
        if not EcatSeverityController.isValid(self._severity):            
            self._data = { 
                'control': '0000000000000110', 
                'velocity': 0 
            }                