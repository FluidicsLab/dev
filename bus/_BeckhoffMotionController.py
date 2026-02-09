
import ctypes, time, struct
from types import SimpleNamespace

from narwhals import UInt32
import pysoem
import numpy as np
from threading import Lock, Event, Thread
import math

from _EcatObject import EcatLogger

from _EcatSeverity import SEVERITY_VERBOSE, EcatSeverityController, SeverityLogger


class AM8111PidController(object):

    _scaler = SimpleNamespace(**{
        'input': { "low": 0, "high": 700 },          # bar   (pressure) 
        'output': { "low": 0, "high": 24_185_993 }   # inc/s (velocity)
    })

    _lock: Lock = Lock()
    _exit = Event()

    _task: Thread = None

    _processvalue = 0
    _setpoint = 0

    _enabled = False
    def _get_enabled(self):
        return self._enabled
    Enabled = property(fget=_get_enabled)

    _error = 0.0
    _demand = 0.0
    _integral = []

    # Kp, Ki, Kd, dt
    _params = [0.5, 0.001, 0.0001, 0.1]

    _updatable = True

    _callback = None

    _source = SimpleNamespace(**{
        "name": None,
        "addr": 0x00,
        "key": None,
        "low": 0,
        "high": 0
    })
    def _set_source(self, value: dict):
        self._source = SimpleNamespace(**value)
        self._scaler.input["low"] = self._source.low
        self._scaler.input["high"] = self._source.high
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
            EcatLogger.debug(f"    ++ update config {config}")

            if 'setpoint' in config.keys() and config['setpoint'] is not None:
                self._setpoint = config['setpoint']
            if 'processvalue' in config.keys() and config['processvalue'] is not None:
                pass
                #self._updatable = False
                #self._processvalue = config['processvalue']
            if 'enabled' in config.keys() and config['enabled'] is not None:
                self._enabled = config['enabled']
            if 'reset' in config.keys():
                self.reset()
            if 'params' in config.keys() and config['params'] is not None:
                self._params = config['params']
            if 'updatable' in config.keys() and config['updatable'] is not None:
                self._updatable = config['updatable']
            
        finally:
            self._lock.release()

    def update(self, value=None):
        self._lock.acquire()
        try:
            if value is not None:
                self._processvalue = value
            else:
                self._enabled = False
        finally:
            self._lock.release()

    def reset(self):
        self._error = 0.0
        self._demand = 0.0
        self._integral = []

    def compute(self):

        def scale(value):
            return (value - self._scaler.input['low']) / (self._scaler.input['high'] - self._scaler.input['low'])
        
        def unscale(value):
            return self._scaler.output['low'] + (self._scaler.output['high'] - self._scaler.output['low']) * value

        enabled = False

        while not self._exit.is_set():

            if enabled and not self._enabled:
                if self._callback is not None:
                    self._callback(0)

            if self._enabled:

                self._lock.acquire()
                try:

                    sp = scale(self._setpoint)
                    pv = scale(max(0, self._processvalue))

                    err = pv - sp

                    kp = self._params[0] * err
                    ki = self._params[1] * err * self._params[3]
                    kd = self._params[2] * (err - self._error) / self._params[3]

                    self._integral.append(ki)                    
                    while len(self._integral) > 20:
                        self._integral.pop(0)
                    ki = sum(self._integral)
                    self._error = err

                    dv = kp + ki + kd
                    dv = unscale(dv)
                
                    if self._callback is not None:
                        if self._demand != dv:
                            self._callback(dv)

                    self._demand = dv

                finally:
                    self._lock.release()

            self._exit.wait(0.25)

            enabled = self._enabled


class AM8111ProfileMode:

    MODE_NONE               = 0

    MODE_CSP                = 8     # cyclic synchronous position
    MODE_CSV                = 9     # cyclic synchronous velocity
    MODE_CST                = 10    # cyclic synchronous torque
    MODE_CSTCA              = 11    # cyclic synchronous torque with commutation angle

    name = ['cyclic synchronous position', 'cyclic synchronous velocity', 
            'cyclic synchronous torque', 'cyclic synchronous torque with commutation angle']
    
    @staticmethod
    def __str__(value: int):
        i = value - AM8111ProfileMode.MODE_CSP
        return AM8111ProfileMode.name[i] if i >=0 and i < len(AM8111ProfileMode.name) else 'unknown'
    
    @staticmethod
    def valid(value):
        return (value >= AM8111ProfileMode.MODE_CSP and value <= AM8111ProfileMode.MODE_CSTCA) or AM8111ProfileMode.MODE_NONE == value
    
    @staticmethod
    def velocity(value):
        return value == AM8111ProfileMode.MODE_CSV

    @staticmethod
    def position(value):
        return value == AM8111ProfileMode.MODE_CSP
    
    @staticmethod
    def torque(value):
        return value == AM8111ProfileMode.MODE_CST or value == AM8111ProfileMode.MODE_CSTCA


class AM8111ProfilePosition:

    @staticmethod
    def split(value, bits, range=32):            
        value = bin(value)[2:].zfill(range)
        return [
            int(value[:bits].zfill(range),2), 
            int(value[bits:].zfill(range),2)
            ]
    
    @staticmethod
    def merge(value, bits, range=32):
        return AM8111ProfilePosition.value(int("".join([
            bin(value[0])[2:].zfill(bits), 
            bin(value[1])[2:].zfill(range-bits)
            ]), 2), range)
    
    @staticmethod
    def value(value, range=32):
        return (2**range - 1) + value if value < 0 else value
        
    @staticmethod
    def compare(raw, value, bits, range=32):
        raw = AM8111ProfilePosition.split(raw, bits, range)
        if raw[0] < value[0]:
            return -1
        elif raw[0] > value[0]:
            return +1
        else:
            if raw[1] < value[1]:
                return -1
            elif raw[1] > value[1]:
                return +1
        return 0        
    

class AM8111ProfileTorque:

    @staticmethod
    def get(value, config):
        rc = 0
        if 0 == config[0]:
            rc = (value / 1000) * (config[2] / np.sqrt(2)) * config[1]
        else:
            rc = (value / 1000) * config[2] * config[1]
        return rc    
    
    @staticmethod
    def set(value, config):
        rc = 0
        if 0 == config[0]:
            rc = 1000 * value  / ((config[2] / np.sqrt(2)) * config[1])
        else:
            rc = 1000 * value / (config[2] * config[1])
        return rc    


class AM8111Profile:

    # status word
    NOT_READY_TO_SWITCH_ON  = 0     # xxx0 xxxx x0xx 0000
    READY_TO_SWITCH_ON      = 1     # xxx0 xxxx x01x 0001
    SWITCHED_ON             = 2     # xxx0 xxxx x1xx 0011
    OPERATION_ENABLED       = 4     # xxx0 xxxx x1xx 0111
    FAULT                   = 8
    
    QUICK_STOP              = 32
    SWITCH_ON_DISABLED      = 64    # xxx0 xxxx x1xx 0000
    WARNING                 = 128

    # control word LoByte
    FAULT_RESET             = '10000000'    # 1xxx xxxx 15
    SHUTDOWN                = '00000110'    # 0xxx x110 2,6,8
    SWITCH_ON               = '00000111'    # 0xxx 0111 3,5
    ENABLE_OPERATION        = '00001111'    # 0xx0 1111 4
    
    """
    status                                              control

    xxx0 xxxx x0xx 0000     not ready to switch on
               |                                        
    xxx0 xxxx x1xx 0000     switch on disabled
                      |                                 0000 0000 0xxx x110       shutdown
    xxx0 xxxx x01x 0001     ready to switch on
                     |                                  0000 0000 0xxx x111       switch on
    xxx0 xxxx x1xx 0011     switched on
                    |                                   0000 0000 0xx0 1111       enable operation
    xxx0 xxxx x1xx 0111     operation enabled


    xxx0 xxxx x0xx 1111     fault reaction active
    xxx0 xxxx x0xx 1000     fault                       0000 0000 1xxx xxxx       fault reset

    
                                                        0000 0000 0xxx xx0x       disable voltage
                                                        0000 0000 0xxx x01x       
    """
    
    status = [
        NOT_READY_TO_SWITCH_ON, READY_TO_SWITCH_ON, SWITCHED_ON, OPERATION_ENABLED, 
        FAULT, QUICK_STOP, SWITCH_ON_DISABLED, WARNING]
    
    status_name = [
        'NOT_READ_TO_SWITCH_ON','READY_TO_SWITCH_ON', 'SWITCHED_ON', 'OPERATION_ENABLED', 
        'FAULT', 'QUICK_STOP', 'SWITCH_ON_DISABLED', 'WARNING']
    
    @staticmethod
    def __str__(state):
        return ",".join([f"{AM8111Profile.status_name[i]}" 
                        for i,s in enumerate(AM8111Profile.status) 
                            if ((s & state) == s) and (s not in [0])
                        ])
    @staticmethod
    def __get__(state):
        return [s for s in AM8111Profile.status if ((s & state) == s) and (s not in [0])]

    @staticmethod
    def __has__(value, state):
        return (state | value) == value

    @staticmethod
    def __transit__(value):

        # transition, state, index

        if AM8111Profile.__has__(value, AM8111Profile.FAULT):
            return [
                (AM8111Profile.FAULT_RESET, AM8111Profile.SWITCH_ON_DISABLED, 15)
                ]

        if AM8111Profile.__has__(value, AM8111Profile.OPERATION_ENABLED):
            return [
                (AM8111Profile.SWITCH_ON, AM8111Profile.SWITCHED_ON, 5), 
                (AM8111Profile.SHUTDOWN, AM8111Profile.READY_TO_SWITCH_ON, 8)
                ]
        
        if AM8111Profile.__has__(value, AM8111Profile.SWITCHED_ON):
            return [                
                (AM8111Profile.ENABLE_OPERATION, AM8111Profile.OPERATION_ENABLED, 4),
                (AM8111Profile.SHUTDOWN, AM8111Profile.READY_TO_SWITCH_ON, 6)
                ]
        
        if AM8111Profile.__has__(value, AM8111Profile.SWITCHED_ON):
            return [
                (AM8111Profile.ENABLE_OPERATION, AM8111Profile.OPERATION_ENABLED, 4)
                ]   
        
        if AM8111Profile.__has__(value, AM8111Profile.READY_TO_SWITCH_ON):
            return [
                (AM8111Profile.SWITCH_ON, AM8111Profile.SWITCHED_ON, 3),                
                ]

        if AM8111Profile.__has__(value, AM8111Profile.SWITCH_ON_DISABLED):
            return [
                (AM8111Profile.SHUTDOWN, AM8111Profile.READY_TO_SWITCH_ON, 2)
                ]    

        return []    
    
    warning_name = [None, None, 'UNDER_VOLTAGE', 'OVER_VOLTAGE', 'OVER_TEMPERATURE', 
                    'I2T_AMPLIFIER', 'I2T_MOTOR', 'ENCODER']
    error_name = ['ADC_ERROR', 'OVER_CURRENT', 'UNDER_VOLTAGE', 'OVER_VOLTAGE', 'OVER_TEMPERATURE', 
                  'I2T_AMPLIFIER', 'I2T_MOTOR', 'ENCODER', 'WATCHDOG']
    
    touch_name = ['TP1_ENABLE', 'TP1_POS', 'TP1_NEG', None, None, None, None, 'TP1_INPUT',
                  'TP2_ENABLE', 'TP2_POS', 'TP2_NEG', None, None, None, None, 'TP2_INPUT'
                  ]

    @staticmethod
    def __info__(value, mode='e'):
        value = bin(value)[2:].zfill(16)[::-1]
        value = list(map(lambda x: int(x), value))
        if mode == 'w':            
            return ",".join([f"{AM8111Profile.warning_name[i]}" 
                        for i,n in enumerate(AM8111Profile.warning_name) 
                            if n is not None and value[i] == 1
                        ])
        if mode == 'e':            
            return ",".join([f"{AM8111Profile.error_name[i]}" 
                        for i,n in enumerate(AM8111Profile.error_name) 
                            if n is not None and value[i] == 1
                        ])
        if mode == 't':
            return ",".join([f"{AM8111Profile.touch_name[i]}" 
                        for i,n in enumerate(AM8111Profile.touch_name) 
                            if n is not None and value[i] == 1
                        ])
        return ""


class BeckhoffMotionController(object):

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

    def _get_pdoInput(self):        
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(BeckhoffMotionController.TxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(BeckhoffMotionController.TxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]
    
    def _set_pdoInput(self, values):
        self.Device.sdo_write(BeckhoffMotionController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values):
            self.Device.sdo_write(BeckhoffMotionController.TxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(BeckhoffMotionController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))
    
    PdoInput = property(fget=_get_pdoInput,fset=_set_pdoInput)
        
    def _get_pdoOutput(self):        
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(BeckhoffMotionController.RxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(BeckhoffMotionController.RxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]

    def _set_pdoOutput(self, values):        
        self.Device.sdo_write(BeckhoffMotionController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values): 
            self.Device.sdo_write(BeckhoffMotionController.RxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(BeckhoffMotionController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))

    PdoOutput = property(fget=_get_pdoOutput,fset=_set_pdoOutput)    

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


class AM8111MotionController(BeckhoffMotionController):

    TIMEOUT_SLAVE_STATE = 5.0
    TIMEOUT_STATE_CHECK = 50_000

    SHIFT_TIME = 250_000        # ns
    CYCLE_TIME = 10_000_000     # ns

    ENCODER_TURNBITS = [17,15]              # multiturn, singleturn; default 12,20
    
    class RxMapEx:
        register = 0x1C12
        address = [0x1600,0x1601,
                   0x1606,0x1607,
                   0x1608]
  
    class RxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
           ('control', ctypes.c_uint16),    # 1600
           ('velocity', ctypes.c_int32),    # 1601
           
           ('position', ctypes.c_int32),    # 1606
           ('touchprobe', ctypes.c_uint16), # 1607  
           
           ('mode', ctypes.c_uint8)         # 1608
        ]

    class TxMapEx:
        register = 0x1C13
        address = [0x1A00,0x1A01,0x1A02,0x1A03,0x1A04,0x1A05,
                   0x1A07,0x1A08,0x1A09,0x1A0A,0x1A0B,
                   0x1A0E]

    class TxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [            
            ('position', ctypes.c_int32),   # 1A00
            ('status', ctypes.c_uint16),    # 1A01
            ('velocity', ctypes.c_int32),   # 1A02
            ('torque', ctypes.c_int16),     # 1A03
            
            ('info1', ctypes.c_uint16),     # 1A04
            ('info2', ctypes.c_uint16),     # 1A05            
            
            ('tpstatus', ctypes.c_uint16),  # 1A07
            ('tp1pos', ctypes.c_uint32),    # 1A08
            ('tp1neg', ctypes.c_uint32),    # 1A09
            ('tp2pos', ctypes.c_uint32),    # 1A0A
            ('tp2neg', ctypes.c_uint32),    # 1A0B            
            
            ('mode', ctypes.c_uint8)        # 1A0E
        ]  

    UINT32_MAX = 4_294_967_295
    INT32_MAX = 2_147_483_647
    INT32_MIN = -2_147_483_647
    
    _controller: AM8111PidController = None
    
    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)
        self._controller = AM8111PidController(self.controllerFunc)

    def release(self):
        super().release()
        if self._controller is not None:
            self._controller.release()

    _torqueConfig = None       # feature, constant, mA
    def _get_torqueConfig(self):
        try:
            if self._torqueConfig is None:                
                self._torqueConfig = [
                    # feature index
                    ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x8010, 0x54)).value,
                    # torque constant
                    ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x8011, 0x16)).value,
                    # rated current
                    ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x8011, 0x12)).value
                ]
        except Exception as ex:
            pass
        return self._torqueConfig
    TorqueConfig = property(fget=_get_torqueConfig)

    _torqueLimit = None 
    def _set_torqueLimit(self, value):
        try:
            value = AM8111ProfileTorque.set(value, self.TorqueConfig)
            self.Device.sdo_write(0x7010, 0x0B, bytes(ctypes.c_uint16(value)))
        except Exception as ex:
            EcatLogger.error(f"{ex}")
        self._torqueLimit = None
    def _get_torqueLimit(self):
        if self._torqueLimit is None:
            try:
                value = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x7010, 0x0B)).value
                self._torqueLimit = AM8111ProfileTorque.get(value, self.TorqueConfig)
            except Exception as ex:
                EcatLogger.error(f"{ex}")
        return self._torqueLimit
    TorqueLimit = property(fget=_get_torqueLimit, fset=_set_torqueLimit)

    _mode = None
    def _get_mode(self):
        try:
            if len(self.Device.input) == ctypes.sizeof(AM8111MotionController.TxMap):
                buff = AM8111MotionController.TxMap.from_buffer_copy(self.Device.input)
                self._mode = buff.mode
            else:
                self._mode = AM8111ProfileMode.MODE_CSV
        except Exception as ex:
            EcatLogger.error(f"{ex}")
        return self._mode
    def _set_mode(self, value):
        if AM8111ProfileMode.valid(value):
            try:
                out = AM8111MotionController.RxMap()
                out.control = ctypes.c_uint16(int(self.ControlWord,2))
                out.velocity = self.Velocity
                out.position = self.Position
                out.touchprobe = ctypes.c_uint16(int(self.TouchprobeWord,2))
                out.mode = ctypes.c_uint8(value)
                self.write(out)            
            except Exception as ex:            
                EcatLogger.error(f"{ex}")
    Mode = property(fget=_get_mode,fset=_set_mode)     

    _velocityLimit = None # inc/s
    def _get_velocityLimit(self):
        if self._velocityLimit is None:
            try:
                # velocity encoder resolution * motor speed limitation / 60s
                ver = ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x9010, 0x14)).value
                msl = ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x8011, 0x1B)).value
                self._velocityLimit = np.int32(ver * msl / 60)
            except Exception as ex:
                EcatLogger.error(f"{ex}")
        return self._velocityLimit
    VelocityLimit = property(fget=_get_velocityLimit)

    def _get_velocity(self):
        try:
            buff = AM8111MotionController.TxMap.from_buffer_copy(self.Device.input)                
            return buff.velocity
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    def _set_velocity(self, value):
        try:
            out = AM8111MotionController.RxMap()
            out.control = ctypes.c_uint16(int(self.ControlWord,2))
            out.velocity = max(-self.VelocityLimit, min(self.VelocityLimit, ctypes.c_int32(value)))
            out.position = self.Position
            out.touchprobe = ctypes.c_uint16(int(self.TouchprobeWord,2))
            out.mode = self.Mode
            self.write(out)            
        except Exception as ex:            
            EcatLogger.error(f"{ex}")
    Velocity = property(fset=_set_velocity,fget=_get_velocity)

    def _get_positionLimit(self):
        return AM8111MotionController.UINT32_MAX
    PositionLimit = property(fget=_get_positionLimit)

    _positionOffset = None
    def _get_positionOffset(self):
        if self._positionOffset is None:
            self._positionOffset = ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x8000,0x17)).value
        return self._positionOffset
    def _set_positionOffset(self, value):
        try:
            value = AM8111ProfilePosition.merge(value, AM8111MotionController.ENCODER_TURNBITS[1])
            self.Device.sdo_write(0x8000,0x17,bytes(ctypes.c_uint32(value)))
        except Exception as ex:
            EcatLogger.error(f"{ex}")
    PositionOffset = property(fget=_get_positionOffset,fset=_set_positionOffset)

    def _get_position(self):
        try:
            buff = AM8111MotionController.TxMap.from_buffer_copy(self.Device.input)                
            return buff.position
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None    
    def _set_position(self, value):
        try:
            out = AM8111MotionController.RxMap()
            out.control = ctypes.c_uint16(int(self.ControlWord,2))
            out.velocity = self.Velocity
            out.position = ctypes.c_int32(value)
            out.touchprobe = ctypes.c_uint16(int(self.TouchprobeWord,2))
            out.mode = self.Mode
            self.write(out)            
        except Exception as ex:            
            EcatLogger.error(f"{ex}")
    Position = property(fget=_get_position, fset=_set_position)

    def _get_statusWord(self):
        try:
            buff = AM8111MotionController.TxMap.from_buffer_copy(self.Device.input)                
            return bin(buff.status)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    StatusWord = property(fget=_get_statusWord)

    def _get_controlWord(self):
        try:
            buff =  AM8111MotionController.RxMap.from_buffer_copy(self.Device.output)                
            return bin(buff.control)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    def _set_controlWord(self, value):
        try:            
            out = AM8111MotionController.RxMap()
            out.control = ctypes.c_uint16(int(value,2))
            out.velocity = ctypes.c_int32(0)
            out.position = self.Position     
            out.touchprobe = ctypes.c_uint16(0)
            out.mode = self.Mode
            self.write(out)            
        except Exception as ex:
            EcatLogger.error(f"{ex}")
    ControlWord = property(fget=_get_controlWord, fset=_set_controlWord)

    def _get_touchprobeWord(self):
        try:
            buff = AM8111MotionController.RxMap.from_buffer_copy(self.Device.output)                
            return bin(buff.touchprobe)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    def _set_touchprobeWord(self, value):
        try:            
            out = AM8111MotionController.RxMap()
            out.control = ctypes.c_uint16(int(self.ControlWord,2))
            out.velocity = self.Velocity
            out.position = self.Position
            out.touchprobe = ctypes.c_uint16(int(value,2))
            out.mode = self.Mode    
            self.write(out)            
        except Exception as ex:
            EcatLogger.error(f"{ex}")
    TouchprobeWord = property(fget=_get_touchprobeWord, fset=_set_touchprobeWord) 

    def _get_touchprobeStatusWord(self):
        try:
            buff = AM8111MotionController.TxMap.from_buffer_copy(self.Device.input)                
            return bin(buff.tpstatus)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    TouchprobeStatusWord = property(fget=_get_touchprobeStatusWord)

    _turnbits = None
    def _get_turnbits(self):
        if self._turnbits is None:
            self._turnbits = [
                ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(0x8000,0x12)).value,
                ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(0x8000,0x13)).value
            ]
        return self._turnbits
    def _set_turnbits(self, value):
        self.Device.sdo_write(0x8000, 0x12, bytes(ctypes.c_uint8(value[0])))
        self.Device.sdo_write(0x8000, 0x13, bytes(ctypes.c_uint8(value[1])))
        self._turnbits = None
    Turnbits = property(fget=_get_turnbits,fset=_set_turnbits)

    def debug(self):
        bits = self.Turnbits
        EcatLogger.debug(f"++ debug")
        EcatLogger.debug(f"   bits      {bits} {2**bits[0]}, {2**bits[1]}")
        EcatLogger.debug(f"   toggle    {ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(0x8010,0x01)).value}")
        EcatLogger.debug(f"   offset    {AM8111ProfilePosition.split(self.PositionOffset, bits[1])}")
        
    _initialized = False

    def initEx(self, source=None): 
        """                
        :param self: 
        :param source: dict with keys like { terminal, address, key, low, high }
        """
        if self._controller is not None:
            self._controller.Source = source

    def _enablePdoAssignment(self, enable=False):
        try:
            if not enable:
                # disable pdo mapping assignment
                self.Device.sdo_write(AM8111MotionController.TxMapEx.register, 0, bytes(ctypes.c_uint8(0)))
                self.Device.sdo_write(AM8111MotionController.RxMapEx.register, 0, bytes(ctypes.c_uint8(0))) 
            else:
                # enable pdo mapping assignment
                self.Device.sdo_write(AM8111MotionController.TxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(AM8111MotionController.TxMapEx.address))))
                self.Device.sdo_write(AM8111MotionController.RxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(AM8111MotionController.RxMapEx.address)))) 
        except Exception as ex:
            EcatLogger.error(f"{ex}")

    def _set_deviceState(self, state):
        rc = True
        timeout = AM8111MotionController.TIMEOUT_SLAVE_STATE
        start_time = time.time()
        while self.Device.state_check(state, timeout=AM8111MotionController.TIMEOUT_STATE_CHECK) != state:
            if time.time() - start_time > timeout:
                rc = False
                break
        return rc

    def init(self): 

        """                
        :param self: 
        """
        try:

            ca = True   # complete access

            if self._set_deviceState(pysoem.PREOP_STATE):
                EcatLogger.debug(f"++ PREOP_STATE reached")
            else:
                EcatLogger.debug(f"-- PREOP_STATE NOT reached")

            # amplifier settings
            self.Device.sdo_write(0x8010, 0x01, bytes(ctypes.c_bool(True)), ca)     # enable toggle

            # FB settings 0x8000            
            self.PositionOffset = [22_900, 0]                           # 0x17 uin32

            # mode of operation
            self.Device.sdo_write(0x7010, 0x03, bytes(ctypes.c_uint8(self.Mode)))

            #
            # PDO
            #

            self._enablePdoAssignment(False)

            # inputs; read; slave-master
            addr = AM8111MotionController.TxMapEx.register            
            for i,value in enumerate(AM8111MotionController.TxMapEx.address):
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))

            # outputs; write; master-slave  
            addr = AM8111MotionController.RxMapEx.register            
            for i,value in enumerate(AM8111MotionController.RxMapEx.address): 
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))

            self._enablePdoAssignment(True)
            # ESM PREOP -> SAFEOP TxPDO effective
            # ESM SAFEOP -> OP TxPDO effective

            #
            # startup AM8111
            #

            self.Device.sdo_write(0x8011, 0x13, bytes(ctypes.c_uint8(3)), ca)       # motor pole pairs
            
            self.Device.sdo_write(0x8011, 0x11, bytes(ctypes.c_uint32(8600)), ca)   # max. current
            self.Device.sdo_write(0x8011, 0x12, bytes(ctypes.c_uint32(2710)), ca)   # rated current
            
            self.Device.sdo_write(0x8011, 0x15, bytes(ctypes.c_int16(-90)), ca)     # commutation offset
            self.Device.sdo_write(0x8011, 0x16, bytes(ctypes.c_uint32(70)), ca)     # torque const.
            self.Device.sdo_write(0x8011, 0x18, bytes(ctypes.c_uint32(33)), ca)     # rotor moment of inertia g cm^2
            self.Device.sdo_write(0x8011, 0x19, bytes(ctypes.c_uint16(15)), ca)     # winding inductance
            self.Device.sdo_write(0x8011, 0x1B, bytes(ctypes.c_uint32(5406)), ca)   # motor speed limitation 1/min ~ 291_780 1/s
            
            self.Device.sdo_write(0x8011, 0x2B, bytes(ctypes.c_uint16(1200)), ca)   # motor temperature warn level 0.1°C
            self.Device.sdo_write(0x8011, 0x2C, bytes(ctypes.c_uint16(1400)), ca)   # motor temperature error level 0.1°C
            self.Device.sdo_write(0x8011, 0x2D, bytes(ctypes.c_uint16(5400)), ca)   # motor thermal time constant 0.1s
            
            # current controller
            self.Device.sdo_write(0x8010, 0x13, bytes(ctypes.c_uint16(177)), ca)    # P 0.1 V/A
            self.Device.sdo_write(0x8010, 0x12, bytes(ctypes.c_uint16(5)), ca)      # I 0.1 ms Tn   integral time

            # velocity controller
            self.Device.sdo_write(0x8010, 0x15, bytes(ctypes.c_uint32(43)), ca)     # P mA/(rad/s)  
            self.Device.sdo_write(0x8010, 0x14, bytes(ctypes.c_uint32(150)), ca)    # I 0.1 ms Tn   integral time

            # position controller
            self.Device.sdo_write(0x8010, 0x17, bytes(ctypes.c_uint32(5)), ca)    # P (rad/s)/rad

            # torque limitation
            self.Device.sdo_write(0x7010, 0x0B, bytes(ctypes.c_uint16(0x02)), ca)

            shift_time = AM8111MotionController.SHIFT_TIME
            cycle_time = AM8111MotionController.CYCLE_TIME
            EcatLogger.debug(f"++ cycle time {cycle_time}; shift time {shift_time}")
            
            self.Device.dc_sync(act=True, 
                                sync0_cycle_time=cycle_time, sync0_shift_time=shift_time, 
                                sync1_cycle_time=cycle_time
                                )
            
            if self._set_deviceState(pysoem.SAFEOP_STATE):
                EcatLogger.debug(f"++ SAFEOP_STATE reached")
            else:
                EcatLogger.debug(f"-- SAFEOP_STATE NOT reached")
    
            # info data
            self.Device.sdo_write(0x8010, 0x39, bytes(ctypes.c_uint16(0x05)), ca)   # errors
            self.Device.sdo_write(0x8010, 0x3A, bytes(ctypes.c_uint16(0x06)), ca)   # warnings

            _ = self.TorqueConfig
            _ = self.TorqueLimit

            _ = self.VelocityLimit         

            self.Turnbits = AM8111MotionController.ENCODER_TURNBITS     # 0x13, 0x12   
            _ = self.Turnbits

            _ = self.PositionOffset

            self.debug()

            self._initialized = True

        except pysoem.SdoError as se:
            self._initialized = False
            EcatLogger.debug(f"-- SdoError {se}")  
        except pysoem.PacketError as pe:
            self._initialized = False
            EcatLogger.debug(f"-- PacketError {pe}")  
        except pysoem.MailboxError as me:
            self._initialized = False
            EcatLogger.debug(f"-- MailboxError {me}")  
        except pysoem.WkcError as we:
            self._initialized = False
            EcatLogger.debug(f"-- WkcError {we}")  
        except Exception as ex:
            self._initialized = False
            EcatLogger.debug(f"-- Exception {ex}")  

        return self._initialized
    
    def input(self):

        # pdo read
        try:

            buff =  AM8111MotionController.TxMap.from_buffer_copy(self.Device.input)
            status = bin(buff.status)[2:].zfill(16)  

            bits = self.Turnbits[1]

            position = AM8111ProfilePosition.value(buff.position)
            torque = AM8111ProfileTorque.get(buff.torque, self.TorqueConfig)
            
            data  = {
                'mode': {
                    'raw': buff.mode,
                    'value': buff.mode,
                    'text': AM8111ProfileMode.__str__(buff.mode)
                },
                'position': {
                    'raw': position,
                    'value': AM8111ProfilePosition.split(position, bits),
                    'offset': {
                        'raw': self.PositionOffset,
                        'value': AM8111ProfilePosition.split(self.PositionOffset, bits)
                    }
                },
                'velocity':{
                    'raw': buff.velocity,
                    'limit': self.VelocityLimit
                },
                'torque': {
                    'raw': buff.torque,
                    'value': torque,
                    'limit': self.TorqueLimit
                },
                'info': {
                    'error': buff.info1,
                    'error_text': AM8111Profile.__info__(buff.info1, 'e'),
                    'warning': buff.info2,
                    'warning_text': AM8111Profile.__info__(buff.info2, 'w')
                },
                'touch': {
                    'status': {
                        'value': buff.tpstatus,
                        'text': AM8111Profile.__info__(buff.tpstatus, 't')
                    },
                    'probe1': {
                        'positive': {
                            'raw': buff.tp1pos,
                            'value': AM8111ProfilePosition.split(buff.tp1pos, bits)
                        },
                        'negative': {
                            'raw': buff.tp1neg,
                            'value': AM8111ProfilePosition.split(buff.tp1neg, bits)
                        }
                    },
                    'probe2': {
                        'positive': {
                            'raw': buff.tp2pos,
                            'value': AM8111ProfilePosition.split(buff.tp2pos, bits)
                        },
                        'negative': {
                            'raw': buff.tp2neg,
                            'value': AM8111ProfilePosition.split(buff.tp2neg, bits)
                        }
                    }
                },
                'status': {
                    'value':status,
                    'text': AM8111Profile.__str__(int(status,2)),
                },
                'transition': AM8111Profile.__transit__(int(status,2))
            }

            return data

        except Exception as ex:
            EcatLogger.error(f"-- input {ex}")
            return None
            
    def write(self, data):
        # pdo write
        self.DeviceLock.acquire()
        try:
            output = AM8111MotionController.RxMap()
            ctypes.memmove(ctypes.byref(output), ctypes.byref(data), ctypes.sizeof(AM8111MotionController.RxMap))
            self.Device.output = bytes(output)
        except Exception as ex:
            EcatLogger.error(f"-- write {ex}")
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

                if 'command' in self._data.keys() and self._data['command'] is not None:                    
                    self.ControlWord = self._data['command']
                    self._data['command'] = None

                if 'mode' in self._data.keys() and self._data['mode'] is not None:   
                    self.Mode = self._data['mode']
                    self._data['mode'] = None

                if 'velocity' in self._data.keys() and self._data['velocity'] is not None:   
                    self.Velocity = self._data['velocity']
                    self._data['velocity'] = None

                if 'position' in self._data.keys() and self._data['position'] is not None:    
                    self.Position = AM8111ProfilePosition.merge(self._data['position'], self.Turnbits[1])
                    self._data['position'] = None

                if 'touchprobe' in self._data.keys() and self._data['touchprobe'] is not None:
                    self.TouchprobeWord = self._data['touchprobe']
                    self._data['touchprobe'] = None

                # pid controller
                if 'control' in self._data.keys() and self._data['control'] is not None:
                    if self._controller is not None: 
                        enabled = self._controller.Enabled
                        self._controller.config(self._data['control'])   
                        if enabled and not self._controller.Enabled:
                            self.Velocity = 0
                    self._data['control'] = None

        except Exception as ex:
            EcatLogger.error(f"-- run {ex}")
        
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
            pass            
        finally:
            self._lock.release()        
        return rc
    
    def callback(self, *args):
        if self._controller is not None and self._controller._updatable and self._controller.Source.name is not None:
            name = f"{args[0]['name']}.{args[0]['index']}"
            if name == self._controller.Source.name:
                addr = self._controller.Source.addr
                key = self._controller.Source.key
                value = args[0]['value']['value']
                if value:
                    if addr in value.keys():
                        data = value[addr]
                        if key in data.keys():                    
                            self._controller.update(data[key])                    

    def controllerFunc(self, value):
        self._lock.acquire()
        try:  
            EcatLogger.debug(f"++ update velocity {math.floor(value)} inc/s")
            self._data.update({
                'velocity': math.floor(value)
            })
        finally:
            self._lock.release()
            
    def isValid(self):
        return EcatSeverityController.isValid(self._severity)
    
    def severityFunc(self, value):
        self._severity = value        
        if not self.isValid():
            self._data = { 
                'velocity': 0,
                'command': AM8111Profile.SHUTDOWN
            }                
