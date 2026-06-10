
import ctypes, time, struct
from types import SimpleNamespace

import pysoem
import numpy as np
from threading import Lock, Event, Thread

from _EcatObject import EcatLogger

from _EcatSeverity import SEVERITY_VERBOSE, EcatSeverityController, SeverityLogger
from _EcatStates import EcatStates

from collections import deque


class AM81111PidController(object):
    
    TIMEOUT_CONTROL = 0.05
    TIME_RANGE = (0.001, 1.0)

    FRACTION = 50
    MODE_DEFAULT = 'p'
    MODES = ['d', 'p']

    # inc/s
    INCS_MAX = 24_185_993

    # scale by mode to compute in range of 0..1
    _scaler = {
        'input': {
            'p': { "low": 0, "high": 700 },             # bar   (pressure)         
            'd': { "low": 0, "high": 1_306_460_160 }    # cycle (distance)         
        },
        'output': { "low": 0, "high": INCS_MAX }        # inc/s (velocity)
    }

    _limit = {                                          # inc/s (velocity)
        'output': { "low": -INCS_MAX * 3/4, "high": INCS_MAX * 3/4 }  
    }

    _lock: Lock = Lock()
    _exit = Event()

    # computation task loop
    _task: Thread = None

    # by mode
    _processvalue = {}
    _setpoint = {}

    # p pressure
    # d distance / volume
    _mode = MODE_DEFAULT              
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

    _target = 0

    _error = { 'p': 0.0, 'd': 0.0 }

    _demand = { 'p': 0.0, 'd': 0.0 }
    _integral = { 'p': [], 'd': [] }
    _time = { 'p': time.monotonic(), 'd': time.monotonic() }
    
    # Kp, Ki, Kd
    _params = {
        'p': [0.5, 0.001, 0.0001],
        'd': [10.0, 0.001, 0.0001]
    }

    # 'direction' factor for mode
    _factor = { 'p': +1, 'd': -1 }
    # 
    _updatable = True
    # callback function for demand value
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
    # controller source by mode
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

            if 'target' in config.keys() and config['target'] is not None:
                self._target = config['target']

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
        for mode in AM81111PidController.MODES:
            
            self._error[mode] = 0.0
            self._demand[mode] = 0.0
            self._integral[mode] = []
            self._time[mode] = time.monotonic()
            
        self._mode = AM81111PidController.MODE_DEFAULT

    def compute(self):

        # scale input to 0..1
        def scale(value):
            low = self._scaler['input'][self._mode]['low']
            high = self._scaler['input'][self._mode]['high']
            return (value - low) / (high - low)

        # unscale and limit output from 0..1
        def unscale(value):
            low = self._scaler['output']['low']
            high = self._scaler['output']['high']
            return low + (high - low) * value
        
        def limit(value):
            low = self._limit['output']['low']
            high = self._limit['output']['high']
            return max(low, min(high, value))
        
        def adapt(mode, dt, dv, params):

            adaption_rate = 0.01
            adaption_mode = 'mit'

            kp, ki, kd = params

            errors = self._errors[mode]

            if adaption_mode == 'mit':

                if len(errors) > 5:                    
                    
                    err = errors[-1]

                    error_rate = (err - errors[-2]) / dt                    
                    
                    kp += adaption_rate * err * dv
                    ki += adaption_rate * err * sum(self._integral[mode])
                    kd += adaption_rate * err * error_rate

                    kp = np.clip(kp, 0.01, 10.0)
                    ki = np.clip(ki, 0.0, 5.0)
                    kd = np.clip(kd, 0.0, 2.0)

            elif adaption_mode == 'grad':

                if len(errors) > 10:                    

                    err = errors[-1]
                    
                    error_gradient = (err - errors[-10]) / (10 * dt)
                    
                    kp -= adaption_rate * err * error_gradient
                    
                    kp = np.clip(self.kp, 0.01, 10.0)

            return [kp, ki, kd]
        
        enabled = False
        zero = False        # zero quick stop

        while not self._exit.is_set():

            if enabled and not self._enabled:
                if self._callback is not None:
                    self._callback(None)

            if self._enabled:

                self._lock.acquire()
                try:

                    mode = self.Mode

                    sp = scale(self._setpoint[mode])
                    pv = scale(max(0, self._processvalue[mode]))

                    err = (pv - sp) * self._factor[mode]

                    params = self._params[mode].copy()

                    now = time.monotonic()
                    dt = now - self._time[mode]
                    dt = max(AM81111PidController.TIME_RANGE[0], min(AM81111PidController.TIME_RANGE[1], dt))
                    self._time[mode] = now

                    kp = params[0] * err
                    ki = params[1] * err * dt
                    kd = params[2] * (err - self._error[mode]) / dt

                    self._integral[mode].append(ki)                    
                    while len(self._integral[mode]) > AM81111PidController.FRACTION:
                        self._integral[mode].pop(0)
                    ki = sum(self._integral[mode])
                    self._error[mode] = err

                    dv = kp + ki + kd      

                    #self._errors[mode].append(err)
                    #self._params[mode] = adapt(mode, dt, dv, params)                                        
                    #EcatLogger.debug(f"{err:0.8f} {self._processvalue[mode]} {self._setpoint[mode]}")

                    dv = unscale(dv)
                    dv = limit(dv)
                
                    if self._callback is not None:
                        if self._demand[mode] != dv:
                            self._callback(dv, mode, err, params)
                            zero = False
                        else:
                            if dv == 0 and not zero:
                                self._callback(dv, mode, err, params)
                                zero = True

                    self._demand[mode] = dv

                finally:
                    self._lock.release()

            self._exit.wait(AM81111PidController.TIMEOUT_CONTROL)

            enabled = self._enabled


class AM81111ProfileMode:

    MODE_NONE               = 0

    MODE_CSP                = 8     # cyclic synchronous position
    MODE_CSV                = 9     # cyclic synchronous velocity
    MODE_CST                = 10    # cyclic synchronous torque
    MODE_CSTCA              = 11    # cyclic synchronous torque with commutation angle

    name = ['none'] + ['unknown'] * 7 + [
        'cyclic synchronous position', 
        'cyclic synchronous velocity', 
        'cyclic synchronous torque', 
        'cyclic synchronous torque with commutation angle'
        ]
    
    @staticmethod
    def __str__(value: int):        
        return AM81111ProfileMode.name[value] if value >=0 and value < len(AM81111ProfileMode.name) else 'unknown'
    
    @staticmethod
    def valid(value):
        return (value >= AM81111ProfileMode.MODE_CSP and value <= AM81111ProfileMode.MODE_CSTCA) or AM81111ProfileMode.MODE_NONE == value
    
    @staticmethod
    def velocity(value):
        return value == AM81111ProfileMode.MODE_CSV

    @staticmethod
    def position(value):
        return value == AM81111ProfileMode.MODE_CSP
    
    @staticmethod
    def torque(value):
        return value == AM81111ProfileMode.MODE_CST or value == AM81111ProfileMode.MODE_CSTCA


class AM81111ProfilePosition:

    """
    precision:  360°/2^bits
    cycles:     2^(32-bits)
    """
    @staticmethod
    def precision(bits, range=32):
        return 360 / (2**bits - 1) if bits > 0 else 360

    @staticmethod
    def cycles(bits, range=32):
        return 2**(range - bits - 1)  

    @staticmethod
    def split(value, bits, range=32):            
        value = bin(value)[2:].zfill(range)
        return [
            int(value[:range-bits].zfill(range),2), 
            int(value[-bits:].zfill(range),2)
            ]
    
    @staticmethod
    def merge(value, bits, range=32, verbose=False):          
        rc = AM81111ProfilePosition.value(int("".join([
            bin(value[0])[2:].zfill(range-bits), 
            bin(value[1])[2:].zfill(bits)]), 2), range)
        return rc
    
    @staticmethod
    def value(value, range=32):
        rc = (2**range - 1) + value if value < 0 else value
        return rc
        
    @staticmethod
    def compare(raw, value, bits, range=32):
        raw = AM81111ProfilePosition.split(raw, bits, range)
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
    
    @staticmethod
    def sub(a, b, bits):
        return AM81111ProfilePosition.merge(a, bits) - AM81111ProfilePosition.merge(b, bits)

    @staticmethod
    def add(a, b, bits):
        return AM81111ProfilePosition.merge(a, bits) + AM81111ProfilePosition.merge(b, bits)    
    

class AM81111ProfileTorque:

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


class AM81111Profile:

    # status word
    NOT_READY_TO_SWITCH_ON  = 0     # xxx0 xxxx x0xx 0000
    READY_TO_SWITCH_ON      = 1     # xxx0 xxxx x01x 0001
    SWITCHED_ON             = 2     # xxx0 xxxx x1xx 0011
    OPERATION_ENABLED       = 4     # xxx0 xxxx x1xx 0111
    FAULT                   = 8     # xxx0 xxxx x0xx 1000
    
    QUICK_STOP              = 32
    SWITCH_ON_DISABLED      = 64    # xxx0 xxxx x1xx 0000
    WARNING                 = 128
    LIMIT_ACTIVE            = 2_048

    # control word LoByte
    FAULT_RESET             = '10000000'    # 1xxx xxxx 15
    SHUTDOWN                = '00000110'    # 0xxx x110 2,6,8
    SWITCH_ON               = '00000111'    # 0xxx 0111 3,5
    ENABLE_OPERATION        = '00001111'    # 0xx0 1111 4

    control = ['10000000','00000110','00000111','00001111']
    control_name = ['FAULT_RESET','SHUTDOWN','SWITCH_ON','ENABLE_OPERATION']

    @staticmethod
    def __control__(value):
        for i,c in enumerate(AM81111Profile.control):
            if int(value,2) == int(c,2):
                return value, AM81111Profile.control_name[i]
        return value, 'UNKNOWN'
    
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
        FAULT, QUICK_STOP, SWITCH_ON_DISABLED, WARNING, LIMIT_ACTIVE]
    
    status_name = [
        'NOT_READ_TO_SWITCH_ON','READY_TO_SWITCH_ON', 'SWITCHED_ON', 'OPERATION_ENABLED', 
        'FAULT', 'QUICK_STOP', 'SWITCH_ON_DISABLED', 'WARNING', 'LIMIT_ACTIVE']
    
    @staticmethod
    def __status__(state):
        return ",".join([f"{AM81111Profile.status_name[i]}" 
                        for i,s in enumerate(AM81111Profile.status) 
                            if ((s & state) == s) and (s not in [0])
                        ])
    @staticmethod
    def __get__(state):
        return [s for s in AM81111Profile.status if ((s & state) == s) and (s not in [0])]

    @staticmethod
    def __has__(value, state):
        return (state | value) == value

    @staticmethod
    def __transit__(value):

        # transition, state, index

        if AM81111Profile.__has__(value, AM81111Profile.FAULT):
            return [
                (AM81111Profile.FAULT_RESET, AM81111Profile.SWITCH_ON_DISABLED, 15)
                ]

        if AM81111Profile.__has__(value, AM81111Profile.OPERATION_ENABLED):
            return [
                (AM81111Profile.SWITCH_ON, AM81111Profile.SWITCHED_ON, 5), 
                (AM81111Profile.SHUTDOWN, AM81111Profile.READY_TO_SWITCH_ON, 8)
                ]
        
        if AM81111Profile.__has__(value, AM81111Profile.SWITCHED_ON):
            return [                
                (AM81111Profile.ENABLE_OPERATION, AM81111Profile.OPERATION_ENABLED, 4),
                (AM81111Profile.SHUTDOWN, AM81111Profile.READY_TO_SWITCH_ON, 6)
                ]
        
        if AM81111Profile.__has__(value, AM81111Profile.SWITCHED_ON):
            return [
                (AM81111Profile.ENABLE_OPERATION, AM81111Profile.OPERATION_ENABLED, 4)
                ]   
        
        if AM81111Profile.__has__(value, AM81111Profile.READY_TO_SWITCH_ON):
            return [
                (AM81111Profile.SWITCH_ON, AM81111Profile.SWITCHED_ON, 3),                
                ]

        if AM81111Profile.__has__(value, AM81111Profile.SWITCH_ON_DISABLED):
            return [
                (AM81111Profile.SHUTDOWN, AM81111Profile.READY_TO_SWITCH_ON, 2)
                ]    

        return []    
    
    warning_name = [None, None, 'UNDER_VOLTAGE', 'OVER_VOLTAGE', 'OVER_TEMPERATURE', 
                    'I2T_AMPLIFIER', 'I2T_MOTOR', 'ENCODER']
    
    error_name = ['ADC_ERROR', 'OVER_CURRENT', 'UNDER_VOLTAGE', 'OVER_VOLTAGE', 'OVER_TEMPERATURE', 
                  'I2T_AMPLIFIER', 'I2T_MOTOR', 'ENCODER', 'WATCHDOG']
    
    touch_name = ['TP1_ENABLE', 'TP1_POS', 'TP1_NEG', None, None, None, None, 'TP1_INPUT',
                  'TP2_ENABLE', 'TP2_POS', 'TP2_NEG', None, None, None, None, 'TP2_INPUT']

    @staticmethod
    def __info__(value, mode='e'):
        value = bin(value)[2:].zfill(16)[::-1]
        value = list(map(lambda x: int(x), value))
        if mode == 'w':            
            return ",".join([f"{AM81111Profile.warning_name[i]}" 
                        for i,n in enumerate(AM81111Profile.warning_name) 
                            if n is not None and value[i] == 1
                        ])
        if mode == 'e':            
            return ",".join([f"{AM81111Profile.error_name[i]}" 
                        for i,n in enumerate(AM81111Profile.error_name) 
                            if n is not None and value[i] == 1
                        ])
        if mode == 't':
            return ",".join([f"{AM81111Profile.touch_name[i]}" 
                        for i,n in enumerate(AM81111Profile.touch_name) 
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

    _severity = []
    
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


class AM81111:

    encoderUnit = SimpleNamespace(**{ 
        'bits': [26, 6] # multiturn, singleturn
    })

    driveUnit = SimpleNamespace(**{ 
        'gearBoxGearRatio': 1000.0,        
        'timingBeltTransmissionGearRatio': 2.0,
        'spindlePitch': 5.0,
        'motorIncrementPositions': 262_144, 
        'cylinderDiameter': 15.0,
        'limit': {
            'low': 0,
            'high': 24_185_993 
        }
    })

    cylinderUnit = SimpleNamespace(**{ 
        'limit': {
            'low':   81.3,  # mm bottom
            'high': 131.1   # mm top
        }
    })
    
    """
    precision:  360°/2^bits
    cycles:     2^(32-bits)
    """    
    def precision(self):
        return 360 / (2**self.encoderUnit.bits[1] - 1) if self.encoderUnit.bits[1] > 0 else 360
    
    def cycles(self):
        return 2**(self.encoderUnit.bits[0] - 1)

    def gearRatio(self):
        return self.driveUnit.timingBeltTransmissionGearRatio * self.driveUnit.gearBoxGearRatio

    def cylinderArea(self):
        return np.pow(self.driveUnit.cylinderDiameter,2) * np.pi / 4.
    
    def pitchVolume(self):
        return self.driveUnit.spindlePitch * self.cylinderArea()

    def mulmin2incs(self, value):        
        transmission = self.driveUnit.spindlePitch / self.gearRatio() # mm/r        
        injectionRateRotation = transmission * self.cylinderArea() # µl/r        
        injectionRateIncrement = injectionRateRotation / self.driveUnit.motorIncrementPositions # µl/inc        
        return np.clip(value / (injectionRateIncrement * 60), self.driveUnit.limit['low'], self.driveUnit.limit['high']) # µl/min
    
    def incs2mulmin(self, value):        
        transmission = self.driveUnit.spindlePitch / self.gearRatio() # mm/r        
        injectionRateRotation = transmission * self.cylinderArea() # mm³/r ~ µl/r        
        injectionRateIncrement = injectionRateRotation / self.driveUnit.motorIncrementPositions # µl/inc
        return (value * injectionRateIncrement * 60.0)
    
    def mms2mulmin(self, value):        
        return value * self.cylinderArea() * 60 # mm³/s ~ µl/s
    
    def turn2ml(self, value):
        bitRange = 2** self.encoderUnit.bits[1] -1        
        mtb = value[0] * self.pitchVolume() / self.gearRatio()
        stb = value[1] / bitRange * self.pitchVolume() / self.gearRatio() if bitRange > 0 else 0
        return (mtb + stb) / 1000

    def ml2turn(self, value):
        bitRange = 2** self.encoderUnit.bits[1] -1
        mtb = round(np.trunc(value / self.pitchVolume() * self.gearRatio() * 1000), 0)
        stb = round(bitRange * (value - self.turn2ml([mtb, 0])) / self.pitchVolume() * self.gearRatio() * 1000, 0) if bitRange > 0 else 0
        return [mtb, stb]


class AM81111MotionController(BeckhoffMotionController):

    TIMEOUT_SLAVE_STATE = 5.0
    TIMEOUT_STATE_CHECK = 50_000
    
    SYNC_MODE = 0x0002
    # ns   
    SYNC_SHIFT_TIME = 0
    SYNC0_CYCLE_TIME = 10_000_000
    SYNC1_CYCLE_TIME = 0

    ENCODER_TURNBITS = [26, 6]  # multiturn, singleturn; default 12, 20
    POSITION_OFFSET = [63, 29]  # 0x17 uint32

    POSITION_OFFSET_DISABLED = 0x00
    POSITION_OFFSET_DRIVE_MEMORY = 0x02

    POSITION_OFFSET_ENABLED = POSITION_OFFSET_DRIVE_MEMORY
        
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
    INT32_MIN = -2_147_483_648
    
    _controller: AM81111PidController = None
    
    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)
        self._controller = AM81111PidController(self.controllerFunc)

    def release(self):
        super().release()
        if self._controller is not None:
            self._controller.release()

    _encoder = None
    def _get_encoder(self):
        if self._encoder is None:
            self._encoder = [
                # revision no
                self.Device.sdo_read(0x9008, 0x16).decode('utf-8'),
                # revision date
                self.Device.sdo_read(0x9008, 0x17).decode('utf-8'),
                # serial no
                self.Device.sdo_read(0x9008, 0x15).decode('utf-8'),
                # type code name
                self.Device.sdo_read(0x9008, 0x14).decode('utf-8')
            ]
        return self._encoder
    Encoder = property(fget=_get_encoder)

    _drive = None
    def _get_drive(self):
        if self._drive is None:
            self._drive = [                
                # serial no
                self.Device.sdo_read(0x9009, 0x03).decode('utf-8'),
                # type code name
                self.Device.sdo_read(0x9009, 0x02).decode('utf-8')
            ]
        return self._drive
    Drive = property(fget=_get_drive)

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
            value = AM81111ProfileTorque.set(value, self.TorqueConfig)
            self.Device.sdo_write(0x7010, 0x0B, bytes(ctypes.c_uint16(value)))
        except Exception as ex:
            EcatLogger.error(f"{ex}")
        self._torqueLimit = None
    def _get_torqueLimit(self):
        if self._torqueLimit is None:
            try:
                value = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x7010, 0x0B)).value
                self._torqueLimit = AM81111ProfileTorque.get(value, self.TorqueConfig)
            except Exception as ex:
                EcatLogger.error(f"{ex}")
        return self._torqueLimit
    TorqueLimit = property(fget=_get_torqueLimit, fset=_set_torqueLimit)

    _mode = None
    def _get_mode(self):
        try:
            if len(self.Device.input) == ctypes.sizeof(AM81111MotionController.TxMap):
                buff = AM81111MotionController.TxMap.from_buffer_copy(self.Device.input)
                self._mode = buff.mode
            else:
                self._mode = AM81111ProfileMode.MODE_CSV
        except Exception as ex:
            EcatLogger.error(f"{ex}")
        return self._mode
    def _set_mode(self, value):
        if AM81111ProfileMode.valid(value):
            try:
                out = AM81111MotionController.RxMap()
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
            buff = AM81111MotionController.TxMap.from_buffer_copy(self.Device.input)                
            return buff.velocity
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    def _set_velocity(self, value):
        try:
            out = AM81111MotionController.RxMap()
            out.control = ctypes.c_uint16(int(self.ControlWord,2))
            out.velocity = max(-self.VelocityLimit, min(self.VelocityLimit, ctypes.c_int32(value)))            
            out.position = self.Position
            out.touchprobe = ctypes.c_uint16(int(self.TouchprobeWord,2))
            out.mode = self.Mode
            self.write(out)            
        except Exception as ex:            
            EcatLogger.error(f"{ex}")
    Velocity = property(fset=_set_velocity,fget=_get_velocity)

    _velocitySetpoint = None
    def _get_velocitySetpoint(self):
        return self._velocitySetpoint
    def _set_velocitySetpoint(self,value):
        self._velocitySetpoint = value
    VelocitySetpoint = property(fget=_get_velocitySetpoint, fset=_set_velocitySetpoint) 
     
    def _get_positionLimit(self):
        return AM81111MotionController.UINT32_MAX
    PositionLimit = property(fget=_get_positionLimit)

    _positionOffset = None
    def _get_positionOffset(self):
        if self._positionOffset is None:
            self._positionOffset = ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x8000,0x17)).value
        return self._positionOffset
    def _set_positionOffset(self, value):
        try:
            value = AM81111ProfilePosition.merge(value, AM81111MotionController.ENCODER_TURNBITS[1])
            self.Device.sdo_write(0x8000, 0x17, bytes(ctypes.c_uint32(value)))
            self._positionOffset = None
        except Exception as ex:
            EcatLogger.error(f"PositionOffset {EcatStates.desc(self.Device.state, desc=True)}; {ex}")
    PositionOffset = property(fget=_get_positionOffset,fset=_set_positionOffset)

    _positionOffsetEnabled = None
    def _get_positionOffsetEnabled(self):
        if self._positionOffsetEnabled is None:
            self._positionOffsetEnabled = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(0x8000,0x0D)).value
        return self._positionOffsetEnabled
    def _set_positionOffsetEnabled(self, value):
        try:
            self.Device.sdo_write(0x8000, 0x0D, bytes(ctypes.c_uint8(value)))
            self._positionOffsetEnabled = None
        except Exception as ex:
            EcatLogger.error(f"PositionOffsetEnabled {ex}")
    PositionOffsetEnabled = property(fget=_get_positionOffsetEnabled,fset=_set_positionOffsetEnabled)

    def _get_position(self):
        try:
            buff = AM81111MotionController.TxMap.from_buffer_copy(self.Device.input)                
            return buff.position
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None    
    def _set_position(self, value):
        try:
            out = AM81111MotionController.RxMap()
            out.control = ctypes.c_uint16(int(self.ControlWord,2))
            out.velocity = self.Velocity
            out.position = ctypes.c_int32(value)
            out.touchprobe = ctypes.c_uint16(int(self.TouchprobeWord,2))
            out.mode = self.Mode
            self.write(out)            
        except Exception as ex:            
            EcatLogger.error(f"Position {ex}")
    Position = property(fget=_get_position, fset=_set_position)

    _positionSetpoint = None
    def _get_positionSetpoint(self):
        return self._positionSetpoint
    def _set_positionSetpoint(self,value):
        self._positionSetpoint = value
    PositionSetpoint = property(fget=_get_positionSetpoint, fset=_set_positionSetpoint)

    _status = None

    def _get_statusWord(self):
        try:
            buff = AM81111MotionController.TxMap.from_buffer_copy(self.Device.input)                
            return bin(buff.status)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    StatusWord = property(fget=_get_statusWord)

    def _get_controlWord(self):
        try:
            buff =  AM81111MotionController.RxMap.from_buffer_copy(self.Device.output)                
            return bin(buff.control)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    def _set_controlWord(self, value):
        try:            
            EcatLogger.info(f"control {AM81111Profile.__control__(value)}")
            out = AM81111MotionController.RxMap()
            out.control = ctypes.c_uint16(int(value,2))
            out.position = self.Position
            out.velocity = self.Velocity
            out.touchprobe = ctypes.c_uint16(0)
            out.mode = self.Mode
            self.write(out)            
        except Exception as ex:
            EcatLogger.error(f"{ex}")
    ControlWord = property(fget=_get_controlWord, fset=_set_controlWord)

    def _get_touchprobeWord(self):
        try:
            buff = AM81111MotionController.RxMap.from_buffer_copy(self.Device.output)                
            return bin(buff.touchprobe)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    def _set_touchprobeWord(self, value):
        try:            
            out = AM81111MotionController.RxMap()
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
            buff = AM81111MotionController.TxMap.from_buffer_copy(self.Device.input)                
            return bin(buff.tpstatus)[2:].zfill(16)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
    TouchprobeStatusWord = property(fget=_get_touchprobeStatusWord)

    _turnbits = None
    def _get_turnbits(self):
        if self._turnbits is None:
            self._turnbits = [
                ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(0x8000,0x13)).value,
                ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(0x8000,0x12)).value
            ]
        return self._turnbits
    def _set_turnbits(self, value):
        self.Device.sdo_write(0x8000, 0x13, bytes(ctypes.c_uint8(value[0])))
        self.Device.sdo_write(0x8000, 0x12, bytes(ctypes.c_uint8(value[1])))        
        self._turnbits = None
    Turnbits = property(fget=_get_turnbits,fset=_set_turnbits)

    _toggle = None
    def _get_toggle(self):
        if self._toggle is None:
            self._toggle = ctypes.c_bool.from_buffer_copy(self.Device.sdo_read(0x8010,0x01)).value
        return self._toggle
    def _set_toggle(self,value):
        self.Device.sdo_write(0x8010, 0x01, bytes(ctypes.c_bool(value)))
        self._toggle = None
    Toggle = property(fget=_get_toggle,fset=_set_toggle)

    _controllerInfo = {}
    def _get_controllerInfo(self):
        return self._controllerInfo
    def _set_controllerInfo(self, value:dict):
        self._controllerInfo = {}
        self._controllerInfo.update(value)
    ControllerInfo = property(fget=_get_controllerInfo,fset=_set_controllerInfo)

    def debug(self):
        
        EcatLogger.debug(f"--- debug")
        
        bits = self.Turnbits
        EcatLogger.debug(f"bits      {bits} {2**bits[0]}, {2**bits[1]}")
        EcatLogger.debug(f"toggle    {self.Toggle}")
        EcatLogger.debug(f"offset    {self.PositionOffset} {self.PositionOffsetEnabled}")

    _initialized = False

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
                self.Device.sdo_write(AM81111MotionController.TxMapEx.register, 0, bytes(ctypes.c_uint8(0)))
                self.Device.sdo_write(AM81111MotionController.RxMapEx.register, 0, bytes(ctypes.c_uint8(0))) 
            else:
                # ENABLE pdo mapping assignment
                self.Device.sdo_write(AM81111MotionController.TxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(AM81111MotionController.TxMapEx.address))))
                self.Device.sdo_write(AM81111MotionController.RxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(AM81111MotionController.RxMapEx.address)))) 
        except Exception as ex:
            EcatLogger.error(f"{ex}")

    def setState(self, state):
        rc = True
        self.Device.state = state
        timeout = AM81111MotionController.TIMEOUT_SLAVE_STATE
        start_time = time.time()
        while self.Device.state_check(state, timeout=AM81111MotionController.TIMEOUT_STATE_CHECK) != state:
            if time.time() - start_time > timeout:
                rc = False
                break
        return rc
    
    def hasState(self, state):
        return self.Device.state & state == state
    
    def updateOffset(self, value=None, enabled=None):

        #if self._status is not None and AM81111Profile.__has__(int(self._status,2), AM81111Profile.READY_TO_SWITCH_ON):
        try:

            if enabled is not None:
                self.PositionOffsetEnabled = enabled
            if value is not None:
                self.PositionOffset = value
            
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

    def initConfig(self, dc_time=None): 

        """                
        :param self: 
        """
        
        try:
                
            self._enablePdoAssignment(False)   

            #
            # amplifier settings
            #
            self.Toggle = True
            
            # mode of operation
            self.Device.sdo_write(0x7010, 0x03, bytes(ctypes.c_uint8(self.Mode)))

            #
            # PDO
            #

            # inputs; read; slave-master
            addr = AM81111MotionController.TxMapEx.register            
            for i,value in enumerate(AM81111MotionController.TxMapEx.address):
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))

            # outputs; write; master-slave  
            addr = AM81111MotionController.RxMapEx.register            
            for i,value in enumerate(AM81111MotionController.RxMapEx.address): 
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))      

            self._enablePdoAssignment(True)
            # ESM PREOP -> SAFEOP TxPDO effective
            # ESM SAFEOP -> OP TxPDO effective

            #
            # startup AM8111
            #
            ca = True

            self.Device.sdo_write(0x8011, 0x13, bytes(ctypes.c_uint8(3)), ca)           # motor pole pairs
            self.Device.sdo_write(0x8011, 0x12, bytes(ctypes.c_uint32(2710)), ca)       # rated current
            self.Device.sdo_write(0x8011, 0x11, bytes(ctypes.c_uint32(8600)), ca)       # max. current
            self.Device.sdo_write(0x8011, 0x16, bytes(ctypes.c_uint32(70)), ca)         # torque const. mNm/A
            self.Device.sdo_write(0x8011, 0x19, bytes(ctypes.c_uint16(15)), ca)         # winding inductance 0.1 mH
            self.Device.sdo_write(0x8011, 0x18, bytes(ctypes.c_uint32(33)), ca)         # rotor moment of inertia g cm^2
            self.Device.sdo_write(0x8011, 0x2D, bytes(ctypes.c_uint16(341)), ca)        # motor thermal time constant 0.1s      ~ 
            self.Device.sdo_write(0x8011, 0x15, bytes(ctypes.c_int16(270)), ca)         # commutation offset
            self.Device.sdo_write(0x8011, 0x1B, bytes(ctypes.c_uint32(4855)), ca)       # motor speed limitation 1/min          ~ 291_780 1/s
            self.Device.sdo_write(0x8011, 0x2B, bytes(ctypes.c_uint16(1200)), ca)       # motor temperature warn level 0.1°C    ~ 120°C
            self.Device.sdo_write(0x8011, 0x2C, bytes(ctypes.c_uint16(1400)), ca)       # motor temperature error level 0.1°C   ~ 140°C

            # current controller
            self.Device.sdo_write(0x8010, 0x13, bytes(ctypes.c_uint16(100)), ca)        # P 0.1 V/A                     177
            self.Device.sdo_write(0x8010, 0x12, bytes(ctypes.c_uint16(5)), ca)          # I 0.1 ms Tn   integral time   5
            # velocity controller
            self.Device.sdo_write(0x8010, 0x15, bytes(ctypes.c_uint32(43)), ca)         # P mA/(rad/s)  
            self.Device.sdo_write(0x8010, 0x14, bytes(ctypes.c_uint32(150)), ca)        # I 0.1 ms Tn   integral time
            # position controller
            self.Device.sdo_write(0x8010, 0x17, bytes(ctypes.c_uint32(2)), ca)          # P (rad/s)/rad
                        
            self.Device.sdo_write(0x8010, 0x31, bytes(ctypes.c_uint32(262_144)), ca)    # velocity limitation
            
            # torque limitation
            self.Device.sdo_write(0x7010, 0x0B, bytes(ctypes.c_uint16(0x02)), ca)

            # enable TxPDO toggle
            self.Device.sdo_write(0x8010, 0x01, bytes(ctypes.c_bool(1)))
            # enable input cycle counter
            self.Device.sdo_write(0x8010, 0x02, bytes(ctypes.c_bool(1)))

            shift_time = AM81111MotionController.SYNC_SHIFT_TIME
            cycle_time_0 = AM81111MotionController.SYNC0_CYCLE_TIME
            cycle_time_1 = AM81111MotionController.SYNC1_CYCLE_TIME


            if dc_time is not None and dc_time > 0:
                cycle_time_0 = dc_time

            EcatLogger.debug(f"setup cycle time 1 | 2 {cycle_time_0} | {cycle_time_1}; shift time {shift_time}")
            
            self.Device.dc_sync(act=True, 
                                sync0_cycle_time=cycle_time_0, sync0_shift_time=shift_time, 
                                sync1_cycle_time=cycle_time_1
                                )
            
            self.debugCycleTime()
            self.debugWatchDog()
    
            # info data
            self.Device.sdo_write(0x8010, 0x39, bytes(ctypes.c_uint16(0x05)), ca)   # errors
            self.Device.sdo_write(0x8010, 0x3A, bytes(ctypes.c_uint16(0x06)), ca)   # warnings

            _ = self.TorqueConfig
            _ = self.TorqueLimit

            self.Turnbits = AM81111MotionController.ENCODER_TURNBITS   
            _ = self.Turnbits
            
            _ = self.VelocityLimit
            _ = self.Encoder
            _ = self.Drive
  
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

    def init(self, status):

        self._initialized = False
                
        if AM81111Profile.__has__(int(status,2), AM81111Profile.READY_TO_SWITCH_ON):
        
            try:
        
                #self.PositionOffset = AM81111MotionController.POSITION_OFFSET
                #self.PositionOffsetEnabled = AM81111MotionController.POSITION_OFFSET_ENABLED

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

    _detected = False
    _watchTime = 0

    def debugCycleTime(self):
        
        v = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x1c32, 0x01)).value
        EcatLogger.info(f"{v} current sync. mode")

        v = ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x1c32, 0x02)).value
        EcatLogger.info(f"{v} cycle time [ns] SYNC0/SYNC1")

        v = ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x1c32, 0x03)).value
        EcatLogger.info(f"{v} time between SYNC0 event and output of the outputs")


    def debugWatchDog(self):     

        for (a, s) in [(0x1c32, "input"), (0x1c33, "output")]:
            
            EcatLogger.warning(f"0x{hex(a)} sm {s}")

            # 16 bit
            for (b, s) in [
                (0x01, "sync mode"),
                (0x04, "modes"),
                (0x0b, "num. of missed SM events in OP"),
                (0x0c, "num. of occasions the cycle time was exceeded in OP; cycle was not compl. in time or next cycle began to early"),
                (0x0d, "num. of occasions that the interval between SYNC0 and SYNC1 event was to shoort")
            ]:
                EcatLogger.debug(f"{ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(a, b)).value} {s}")

            # 32 bit
            for (b, s) in [
                (0x02, "cycle time"),
                (0x03, "shift time"),
                (0x05, "min. cycle time"),
                (0x06, "calc and copy time"),
                (0x07, "min. delay time"),
                (0x09, "max. delay time"),
            ]:
                EcatLogger.debug(f"{ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(a, b)).value} {s}")

            # bool
            for (b, s) in [
                (0x20, "the sync. was not correct in the last cycle; outputs where output to late")
            ]:
                EcatLogger.debug(f"{ctypes.c_bool.from_buffer_copy(self.Device.sdo_read(a, b)).value} {s}")

    def debugDiagnostics(self):
        
        a = 0x10f3   

        count = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(a, 0x01)).value
        EcatLogger.info(f"{count} information and diagnostics")
             
        for n in range(count):
            pass
            #s = bytes(self.Device.sdo_read(a, 0x06 + n, 'utf-8'))
            #EcatLogger.debug(f"{n:5d} {s}")

    def input(self):

        # pdo read
        try:

            buff =  AM81111MotionController.TxMap.from_buffer_copy(self.Device.input)
            
            status = bin(buff.status)[2:].zfill(16)  
            status_text = AM81111Profile.__status__(int(status,2))
            self._status = status

            if not self._initialized:      
                self.init(status)  

            bits = self.Turnbits[1]

            position = AM81111ProfilePosition.value(buff.position)
            torque = AM81111ProfileTorque.get(buff.torque, self.TorqueConfig)

            watchdog = 0
            watchdog_time = 0
            
            error = buff.info1
            error_text = AM81111Profile.__info__(error, 'e')

            if "WATCHDOG" in error_text.split(","):
                
                if not self._detected:

                    watchdog = 1
                    watchdog_time = (time.time_ns() - self._watchTime) / 1e9
                    EcatLogger.warning(f"watchdog {error_text} {status_text} {watchdog_time:.9f}") 
                    
                    self.debugWatchDog() 
                    self.debugDiagnostics()   

                self._detected = True
            else:
                self._detected = False
                            
            data  = {
                'mode': {
                    'raw': buff.mode,
                    'value': buff.mode,
                    'text': AM81111ProfileMode.__str__(buff.mode)
                },
                'position': {
                    'raw': position,
                    'value': AM81111ProfilePosition.split(position, bits),
                    'setpoint': { 
                        'raw': self.PositionSetpoint, 
                        'value': AM81111ProfilePosition.split(self.PositionSetpoint, bits) if self.PositionSetpoint is not None else None 
                    },
                    'offset': { 
                        'raw': self.PositionOffset, 
                        'value': AM81111ProfilePosition.split(self.PositionOffset, bits),
                        'enabled': self.PositionOffsetEnabled 
                    }                    
                },
                'velocity':{
                    'raw': buff.velocity,
                    'limit': self.VelocityLimit,
                    'setpoint': self.VelocitySetpoint
                },
                'info': {
                    'error': error, 
                    'error_text': error_text,
                    'warning': buff.info2, 
                    'warning_text': AM81111Profile.__info__(buff.info2, 'w'),
                    'watchdog': watchdog, 
                    'watchdog_time': watchdog_time
                },
                'torque': {
                    'raw': buff.torque, 
                    'value': torque, 
                    'limit': self.TorqueLimit
                },
                'touch': {
                    'status': { 
                        'value': buff.tpstatus, 
                        'text': AM81111Profile.__info__(buff.tpstatus, 't') 
                    },
                    'probe1': {
                        'positive': { 
                            'raw': buff.tp1pos, 
                            'value': AM81111ProfilePosition.split(buff.tp1pos, bits) 
                        },
                        'negative': { 
                            'raw': buff.tp1neg, 
                            'value': AM81111ProfilePosition.split(buff.tp1neg, bits) 
                        }
                    },
                    'probe2': {
                        'positive': { 
                            'raw': buff.tp2pos, 
                            'value': AM81111ProfilePosition.split(buff.tp2pos, bits) 
                            },
                        'negative': { 
                            'raw': buff.tp2neg, 
                            'value': AM81111ProfilePosition.split(buff.tp2neg, bits) 
                        }
                    }
                },
                'status': {
                    'value':status, 
                    'text': status_text,
                },
                'encoder': { 
                    'type': 'multiturn',
                    'bits': self.Turnbits,
                    'info': self.Encoder
                },
                'drive': {
                    'info': self.Drive
                },
                'controller': self.ControllerInfo,
                # severity callback position
                '0x01': { 
                    'd': position 
                }
            }

            return data

        except Exception as ex:
            EcatLogger.error(f"{ex}")
            return None
        
    _toggleState = False
    def toggle(self, byte_offset=2, bit_mask=0x01):
        
        self.DeviceLock.acquire()
        try:
            
            current = bytearray(self.Device.output)
            
            if len(current) > byte_offset:
                if self._toggleState:
                    current[byte_offset] |= bit_mask
                else:
                    current[byte_offset] &= ~bit_mask
                
                self.Device.output = bytes(current)
                self._toggleState = not self._toggleState
                
        except Exception as ex:
            EcatLogger.error(f"toggle {ex}")
        finally:
            self.DeviceLock.release()     
            
    def write(self, data):
        # pdo write
        self.DeviceLock.acquire()
        try:
            output = AM81111MotionController.RxMap()
            ctypes.memmove(ctypes.byref(output), ctypes.byref(data), ctypes.sizeof(AM81111MotionController.RxMap))
            self.Device.output = bytes(output)
        except Exception as ex:
            EcatLogger.error(f"{ex}")
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

                    self.debugWatchDog() 

                    self.ControlWord = self._data['command']                    
                    self._data['command'] = None

                if 'mode' in self._data.keys() and self._data['mode'] is not None:   
                    self.Mode = self._data['mode']
                    self._data['mode'] = None

                if 'velocity' in self._data.keys() and self._data['velocity'] is not None:   
                    self.VelocitySetpoint = self._data['velocity']
                    self.Velocity = self.VelocitySetpoint
                    self._data['velocity'] = None

                if 'position' in self._data.keys() and self._data['position'] is not None:   
                    # unused
                    self._data['position'] = None

                if 'offset' in self._data.keys() and self._data['offset'] is not None:   
                    self.updateOffset(
                        value=self._data['offset']['value'] if 'value' in self._data['offset'].keys() else None, 
                        enabled=self._data['offset']['enabled'] if 'enabled' in self._data['offset'].keys() else None
                    )
                    self._data['offset'] = None

                if 'touchprobe' in self._data.keys() and self._data['touchprobe'] is not None:
                    self.TouchprobeWord = self._data['touchprobe']
                    self._data['touchprobe'] = None

                if 'controller' in self._data.keys() and self._data['controller'] is not None:
                    self.ControllerInfo = self._data['controller']
                    self._data['controller'] = None

                # pid controller
                if 'control' in self._data.keys() and self._data['control'] is not None:                    
                    if self._controller is not None: 
                        enabled = self._controller.Enabled
                        self._controller.config(self._data['control'])   
                        if enabled and not self._controller.Enabled:
                            # disable velocity
                            self.VelocitySetpoint = 0
                            self.Velocity = self.VelocitySetpoint
                            self.ControlWord = AM81111Profile.SWITCH_ON
                    self._data['control'] = None

        except Exception as ex:
            EcatLogger.error(f"run {ex}")
        
        finally:
            self._lock.release()

        self._watchTime = time.time_ns()

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
    
    def callback(self, *args):
        """
        callback from controller data source

        :param args: mqt telegram data
        """
        if self._controller is not None and self._controller._updatable and len(self._controller.Source) != 0:
            name = f"{args[0]['name']}.{args[0]['index']}"
            for source in self._controller.Source:
                if name == source.name:
                    addr = source.addr
                    key = source.key
                    if 'value' in list(args[0]['value']):
                        value = args[0]['value']['value']
                        if value:
                            if addr in value.keys():
                                data = value[addr]
                                if key in data.keys():                    
                                    self._controller.update(key, data[key])                    

    def controllerFunc(self, value, mode='', error=0, params=[]):
        """
        callback from PID
        
        :param self: 
        :param value: velocity inc/s
        :param mode: pid controller mode
        :param error: error py pid controller calc.
        :param params: pid parameters
        """
        self._lock.acquire()
        try:  
            self._data.update({
                'velocity': round(value),
                'controller': {
                    'modified': time.time_ns(),
                    'mode': mode,
                    'error': error,                    
                    'params': params
                }
            })
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
            self._data = { 
                'velocity': 0,
                'command': AM81111Profile.SHUTDOWN
            }
