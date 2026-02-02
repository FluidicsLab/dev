
import ctypes, time, struct
from types import SimpleNamespace

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
                self._updatable = False
                self._processvalue = config['processvalue']
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

        while not self._exit.is_set():

            if self._enabled:

                self._lock.acquire()
                try:

                    sp = scale(self._setpoint)
                    pv = scale(max(0, self._processvalue))

                    err = sp - pv

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


class AM8111Profile:

    MODE_CSP                = 8     # cyclic synchronous position
    MODE_CSV                = 9     # cyclic synchronous velocity
    MODE_CST                = 10    # cyclic synchronous torque
    MODE_CSTCA              = 11    # cyclic synchronous torque with commutation angle

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

    SHIFT_TIME = 250_000        # ns
    CYCLE_TIME = 10_000_000     # ns
  
    class RxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
           ('control', ctypes.c_uint16),    # 1600
           ('velocity', ctypes.c_int32),    # 1601
           ('touchprobe', ctypes.c_uint16)  # 1607
        ]

    class TxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [            
            ('position', ctypes.c_int32),   # 1A00
            ('status', ctypes.c_uint16),    # 1A01
            ('velocity', ctypes.c_int32),   # 1A02

            ('info1', ctypes.c_uint16),     # 1A04
            ('info2', ctypes.c_uint16),     # 1A05

            ('touchprobe', ctypes.c_uint16),# 1A07
            ('tp1pos', ctypes.c_uint32),    # 1A08
            ('tp1neg', ctypes.c_uint32),    # 1A09
            ('tp2pos', ctypes.c_uint32),    # 1A0A
            ('tp2neg', ctypes.c_uint32),    # 1A0B
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

    _velocityMax = None # inc/s
    def _get_velocityMax(self):
        try:
            if self._velocityMax is None:
                # velocity encoder resolution * motor speed limitation / 60s
                ver = ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x9010, 0x14)).value
                msl = ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x8011, 0x1B)).value
                self._velocityMax = np.int32(ver * msl / 60)
        except Exception as ex:
            pass
        return self._velocityMax
    VelocityMax = property(fget=_get_velocityMax)

    def _get_velocity(self):
        try:
            buff = AM8111MotionController.TxMap.from_buffer_copy(self.Device.input)                
            return buff.velocity
        except Exception as ex:
            return None
    def _set_velocity(self, value):
        try:
            out = AM8111MotionController.RxMap()
            out.control = ctypes.c_uint16(int(self.ControlWord,2))
            out.velocity = max(-self.VelocityMax, min(self.VelocityMax, ctypes.c_int32(value)))
            out.touchprobe = ctypes.c_uint16(int(self.TouchprobeWord,2))
            self.write(out)            
        except Exception as ex:            
            pass
    Velocity = property(fset=_set_velocity,fget=_get_velocity)
        
    def _get_statusWord(self):
        try:
            buff = AM8111MotionController.TxMap.from_buffer_copy(self.Device.input)                
            return bin(buff.status)[2:].zfill(16)
        except Exception as ex:
            return None
    StatusWord = property(fget=_get_statusWord)

    def _get_controlWord(self):
        try:
            buff =  AM8111MotionController.RxMap.from_buffer_copy(self.Device.output)                
            return bin(buff.control)[2:].zfill(16)
        except Exception as ex:
            return None
    def _set_controlWord(self, value):
        try:            
            out = AM8111MotionController.RxMap()
            out.control = ctypes.c_uint16(int(value,2))
            out.velocity = ctypes.c_int32(0)
            out.touchprobe = ctypes.c_uint16(0)
            self.write(out)            
        except Exception as ex:
            pass                
    ControlWord = property(fget=_get_controlWord, fset=_set_controlWord)

    def _get_touchprobeWord(self):
        try:
            buff = AM8111MotionController.RxMap.from_buffer_copy(self.Device.output)                
            return bin(buff.touchprobe)[2:].zfill(16)
        except Exception as ex:
            return None
    def _set_touchprobeWord(self, value):
        try:            
            out = AM8111MotionController.RxMap()
            out.control = ctypes.c_uint16(int(self.ControlWord,2))
            out.velocity = self.Velocity
            out.touchprobe = ctypes.c_uint16(int(value,2))
            self.write(out)            
        except Exception as ex:
            pass                
    TouchprobeWord = property(fget=_get_touchprobeWord, fset=_set_touchprobeWord)    

    _initialized = False

    def init(self, source=None): 

        """
                
        :param self: 
        :param source: dict with keys like { terminal, address, key, low, high }
        """

        try:

            if self._controller is not None:
                self._controller.Source = source

            def _set_state(state):
                rc = True
                timeout = 5.0  # seconds
                start_time = time.time()
                while self.Device.state_check(state, timeout=50_000) != state:
                    if time.time() - start_time > timeout:
                        rc = False
                        break
                return rc

            ca = True   # complete access

            if _set_state(pysoem.PREOP_STATE):
                EcatLogger.debug(f"    ++ PREOP_STATE reached")
            else:
                EcatLogger.debug(f"    -- PREOP_STATE NOT reached")

            self.Device.sdo_write(0x7010, 0x03, bytes(ctypes.c_uint8(AM8111Profile.MODE_CSV)))

            # outputs; write; master-slave                  
            addr = 0x1C12                    
            values = [
                0x1600, # control word
                0x1601, # velocity
                # touch probe
                0x1607  # control word
                ]
            self.Device.sdo_write(addr, 0, bytes(ctypes.c_uint8(0)))
            for i,value in enumerate(values): 
                self.Device.sdo_write(addr, i+1, bytes(ctypes.c_uint16(value)))
            num = len(values)
            self.Device.sdo_write(addr, 0, bytes(ctypes.c_uint8(num)))

            # inputs; read; slave-master
            addr = 0x1C13
            values = [
                0x1A00, # position
                0x1A01, # status word
                0x1A02, # velocity
                # info data
                0x1A04, # info 1 (errors)
                0x1A05, # info 2 (warnings)
                # touch probe
                0x1A07, # status
                0x1A08, # ch 1 pos position
                0x1A09, # ch 1 neg position
                0x1A0A, # ch 2 pos position
                0x1A0B  # ch 2 neg position
                ]
            self.Device.sdo_write(addr, 0, bytes(ctypes.c_uint8(0)))
            for i,value in enumerate(values):
                self.Device.sdo_write(addr, i+1, bytes(ctypes.c_uint16(value)))
            num = len(values)
            self.Device.sdo_write(addr, 0, bytes(ctypes.c_uint8(num)))                    

            # startup
            self.Device.sdo_write(0x8011, 0x13, bytes(ctypes.c_uint8(3)), ca)       # motor pole pairs
            self.Device.sdo_write(0x8011, 0x12, bytes(ctypes.c_uint32(2710)), ca)   # rated current
            self.Device.sdo_write(0x8011, 0x11, bytes(ctypes.c_uint32(8600)), ca)   # max. current
            self.Device.sdo_write(0x8011, 0x16, bytes(ctypes.c_uint32(70)), ca)     # torque const.
            self.Device.sdo_write(0x8011, 0x19, bytes(ctypes.c_uint16(15)), ca)     # winding inductance
            self.Device.sdo_write(0x8011, 0x18, bytes(ctypes.c_uint32(33)), ca)     # rotor moment of inertia g cm^2
            self.Device.sdo_write(0x8011, 0x2D, bytes(ctypes.c_uint16(341)), ca)    # thermal time of motor
            self.Device.sdo_write(0x8011, 0x15, bytes(ctypes.c_uint16(270)), ca)    # commutation offset
            self.Device.sdo_write(0x8011, 0x1B, bytes(ctypes.c_uint32(4863)), ca)   # motor speed limitation 1/min

            # amplifier settings
            self.Device.sdo_write(0x8010, 0x01, bytes(ctypes.c_bool(1)), ca)        # enable toggle

            # current loop
            self.Device.sdo_write(0x8010, 0x13, bytes(ctypes.c_uint16(178)), ca)    # P 0.1 V/A
            self.Device.sdo_write(0x8010, 0x12, bytes(ctypes.c_uint16(5)), ca)      # I 0.1 ms Tn
            # velocity loop
            self.Device.sdo_write(0x8010, 0x15, bytes(ctypes.c_uint32(43)), ca)     # P mA/(rad/s)
            self.Device.sdo_write(0x8010, 0x14, bytes(ctypes.c_uint32(150)), ca)    # I 0.1 ms Tn

            # torque limitation
            self.Device.sdo_write(0x7010, 0x0B, bytes(ctypes.c_uint16(0x02)), ca)

            shift_time = AM8111MotionController.SHIFT_TIME
            cycle_time = AM8111MotionController.CYCLE_TIME
            EcatLogger.debug(f"    ++ cycle time {cycle_time}; shift time {shift_time}")
            
            self.Device.dc_sync(act=True, 
                                sync0_cycle_time=cycle_time, sync0_shift_time=shift_time, 
                                sync1_cycle_time=cycle_time
                                )
            
            if _set_state(pysoem.SAFEOP_STATE):
                EcatLogger.debug(f"    ++ SAFEOP_STATE reached")
            else:
                EcatLogger.debug(f"    -- SAFEOP_STATE NOT reached")
    
            # info data
            self.Device.sdo_write(0x8010, 0x39, bytes(ctypes.c_uint16(0x05)), ca)   # errors
            self.Device.sdo_write(0x8010, 0x3A, bytes(ctypes.c_uint16(0x06)), ca)   # warnings

            _ = self.VelocityMax

            self._initialized = True

        except pysoem.SdoError as se:
            self._initialized = False
            EcatLogger.debug(f"    -- SdoError {se}")  
        except pysoem.PacketError as pe:
            self._initialized = False
            EcatLogger.debug(f"    -- PacketError {pe}")  
        except pysoem.MailboxError as me:
            self._initialized = False
            EcatLogger.debug(f"    -- MailboxError {me}")  
        except pysoem.WkcError as we:
            self._initialized = False
            EcatLogger.debug(f"    -- WkcError {we}")  
        except Exception as ex:
            self._initialized = False
            EcatLogger.debug(f"    -- Exception {ex}")  

        return self._initialized
   
    def input(self):

        # pdo read
        try:

            buff =  AM8111MotionController.TxMap.from_buffer_copy(self.Device.input)
            status = bin(buff.status)[2:].zfill(16)      
            
            data  = {
                'position': {
                    'raw': buff.position
                },
                'velocity':{
                    'raw': buff.velocity,
                    'max': self._velocityMax
                },
                'info': {
                    'error': buff.info1,
                    'error_text': AM8111Profile.__info__(buff.info1, 'e'),
                    'warning': buff.info2,
                    'warning_text': AM8111Profile.__info__(buff.info2, 'w')
                },
                'touch': {
                    'status': {
                        'value': buff.touchprobe,
                        'text': AM8111Profile.__info__(buff.touchprobe, 't')
                    },
                    'probe1': {
                        'pos': buff.tp1pos,
                        'neg': buff.tp1neg
                    },
                    'probe2': {
                        'pos': buff.tp2pos,
                        'neg': buff.tp2neg
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
            EcatLogger.error(f"-- AM8111MotionController.input {ex}")
            return None
            
    def write(self, data):
        # pdo write
        self.DeviceLock.acquire()
        try:
            self.Device.output = bytes(data)
        finally:
            self.DeviceLock.release()        
        
    _toggle = True     
    def toggle(self):

        self._toggle ^= True

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

                if 'velocity' in self._data.keys() and self._data['velocity'] is not None:                    
                    self.Velocity = self._data['velocity']
                    self._data['velocity'] = None

                if 'touchprobe' in self._data.keys() and self._data['touchprobe'] is not None:                    
                    self.TouchprobeWord = self._data['touchprobe']
                    self._data['touchprobe'] = None

                # pid controller
                if 'control' in self._data.keys() and self._data['control'] is not None:
                    if self._controller is not None:                    
                        self._controller.config(self._data['control'])
                    self._data['control'] = None

        except Exception as ex:
            pass
        
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
            EcatLogger.debug(f"    ++ update velocity {math.floor(value)} inc/s")
            self._data = {
                'velocity': math.floor(value)
            }
        finally:
            self._lock.release()
            
    def isValid(self):
        return EcatSeverityController.isValid(self._severity)
    
    def severityFunc(self, value):
        self._severity = value        
        if not self.isValid():            
            self._data = { 
                'control': AM8111Profile.FAULT_RESET
            }                
