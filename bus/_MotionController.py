
import ctypes, time
import pysoem
import numpy as np
from threading import Lock,Event

from _EcatObject import EcatLogger

from _EcatSeverity import SEVERITY_VERBOSE, EcatSeverityController, SeverityLogger



class MotionController(object):

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

    def severityFunc(self, value):
        pass    
    

class NanotecMotionController(MotionController):

    class MOTION_TYPE:

        ABSOLUTE = 0x01
        RELATIVE = 0x02
        ENDLESS_PLUS = 0x03
        ENDLESS_MINUS = 0x04
        ADDITIVE = 0x05

        @staticmethod
        def isin(type):
            return np.any(type == t for t in [NanotecMotionController.MOTION_TYPE.ABSOLUTE, NanotecMotionController.MOTION_TYPE.RELATIVE,
                                              NanotecMotionController.MOTION_TYPE.ENDLESS_PLUS, NanotecMotionController.MOTION_TYPE.ENDLESS_MINUS,
                                              NanotecMotionController.MOTION_TYPE.ADDITIVE])
        
    class RxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            ('stm_control', ctypes.c_uint16),   #  2 1602
            ('pos_control', ctypes.c_uint16),   #  2 1606 ff
            ('position', ctypes.c_uint32),      #  4
            ('velocity', ctypes.c_int16),       #  2
            ('start', ctypes.c_uint16),         #  2
            ('acceleration', ctypes.c_uint16),  #  2
            ('deceleration', ctypes.c_uint16),  #  2
                                                # 16
        ]

    class TxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [            
            ('stm_status', ctypes.c_uint16),    #  2 1a03
            ('pos_status', ctypes.c_uint16),    #  2 1a06
            ('position', ctypes.c_uint32),      #  4
            ('velocity', ctypes.c_int16),       #  2
            ('time', ctypes.c_uint32),          #  4
                                                # 14
        ]  

    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)

    _data = None
    
    STM_ENABLE =    '0000000000000001'
    STM_DISABLE =   '0000000000000000'
    STM_RESET =     '0000000000000010'

    POS_EXECUTE =   '0000000000000001'
    POS_DISABLE =   '0000000000000000'

    POS_HALT =      '0000000000000010'

    def diag(self):

        rc = {}

        try:

            a = 0xf900
            for o in [0x04,0x05,0x06]:            
                rc[f"{hex(a)}.{hex(o)}"] = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(a,o)).value
            for o in [0x02]:
                rc[f"{hex(a)}.{hex(o)}"] = ctypes.c_int8.from_buffer_copy(self.Device.sdo_read(a,o)).value

            a = 0xf80f
            for o in [0x01,0x02,0x03,0x06]:
                rc[f"{hex(a)}.{hex(o)}"] = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(a,o)).value

            for o in [0x04,0x05]:
                rc[f"{hex(a)}.{hex(o)}"] = ctypes.c_int8.from_buffer_copy(self.Device.sdo_read(a,o)).value

            a = 0xa010
            for o in [0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a]:
                rc[f"{hex(a)}.{hex(o)}"] = ctypes.c_bool.from_buffer_copy(self.Device.sdo_read(a,o)).value

            a = 0x8010
            for o in [0x01,0x02,0x03,0x04,0x05,0x06,0x09,0x10,0x11]:
                rc[f"{hex(a)}.{hex(o)}"] = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(a,o)).value

            #
            a = 0x9010
            for o in [0x01,0x02,0x03]:
                rc[f"{hex(a)}.{hex(o)}"] = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(a,o)).value
            for o in [0x04,0x05,0x08]:
                rc[f"{hex(a)}.{hex(o)}"] = ctypes.c_int16.from_buffer_copy(self.Device.sdo_read(a,o)).value
            for o in [0x06,0x07]:
                rc[f"{hex(a)}.{hex(o)}"] = ctypes.c_int8.from_buffer_copy(self.Device.sdo_read(a,o)).value
            for o in [0x13]:
                rc[f"{hex(a)}.{hex(o)}"] = ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(a,o)).value

            #
            a, o = 0x6010, 0x11
            for v in [0,1,2,3,4,5,6,7,101,103,104,150,150,151,152,153]:
                self.Device.sdo_write(0x8012, 0x11, bytes(ctypes.c_uint8(v)))
                rc[f"{hex(a)}.{hex(o)}.{hex(v)}"] = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x6010,0x11)).value

        except Exception as ex:
            EcatLogger.error(f"NanotecMotionController.diag {ex}")

        return rc
    
    _sign = None
    def _get_sign(self):
        if self._sign is None:
            self._sign = -1 if ctypes.c_bool.from_buffer_copy(self.Device.sdo_read(0x8012, 0x09)).value else +1
        return self._sign
    def _set_sign(self, value):
        self._sign = value
        self.Device.sdo_write(0x8012, 0x09, bytes(ctypes.c_bool(self._sign <0)))
    Sign = property(fget=_get_sign, fset=_set_sign)

    _motorSettings = None
    def _get_motorSettings(self):
        if self._motorSettings == None:
            try:
                self._motorSettings = dict(
                    maximalCurrent = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8010, 0x01)).value,
                    reducedCurrent = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8010, 0x02)).value,
                    nominalVoltage = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8010, 0x03)).value,
                    coilResistance = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8010, 0x04)).value,
                    fullSteps = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8010, 0x06)).value,
                    speedRange = 1000 * 2**ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(0x8012, 0x05)).value,
                    acceleration = [ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8020, 0x03)).value, ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8020, 0x04)).value],
                    deceleration = [ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8020, 0x05)).value, ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8020, 0x06)).value],
                    calibrationPosition = ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x8020, 0x08)).value
                )
            except Exception as ex:
                self._motorSettings = None
        return self._motorSettings
    MotorSettings = property(fget=_get_motorSettings)

    _infoData = None
    def _get_infoData(self):
        self._infoData = {}
        for src1,src2 in [(0x01,0x02),(0x03,0x04),(0x05,0x06),(0x07,0x65)]:
            self.Device.sdo_write(0x8012, 0x11, bytes(ctypes.c_uint8(src1)) )
            self.Device.sdo_write(0x8012, 0x19, bytes(ctypes.c_uint8(src2)) )
            self._infoData[src1] = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x6010, 0x11)).value            
            self._infoData[src2] = ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x6010, 0x12)).value            
        return self._infoData
    InfoData = property(fget=_get_infoData)    

    def _get_pdoInput(self):        
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(MotionController.TxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(MotionController.TxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]
    
    def _set_pdoInput(self, values):
        self.Device.sdo_write(MotionController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values):
            self.Device.sdo_write(MotionController.TxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(MotionController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))
    
    PdoInput = property(fget=_get_pdoInput,fset=_set_pdoInput)
        
    def _get_pdoOutput(self):        
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(MotionController.RxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(MotionController.RxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]

    def _set_pdoOutput(self, values):        
        self.Device.sdo_write(MotionController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values): 
            self.Device.sdo_write(MotionController.RxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(MotionController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))

    PdoOutput = property(fget=_get_pdoOutput,fset=_set_pdoOutput)

    out = None
    
    def run(self):

        if (self.Device.state & pysoem.PREOP_STATE) == self.Device.state:
            _ = self.MotorSettings
            _ = self.Acceleration
            _ = self.Deceleration
            return None

        if (self.Device.state & pysoem.OP_STATE) != self.Device.state:
            return None

        self._lock.acquire()

        try:

            data = None

            if self.out is None:
                self.out = NanotecMotionController.RxMap()
            else:    

                buff =  NanotecMotionController.TxMap.from_buffer_copy(self.Device.input)                
                data  = {
                    'stm_status': bin(buff.stm_status)[2:].zfill(16),
                    'pos_status': bin(buff.pos_status)[2:].zfill(16),
                    'position': buff.position,
                    'velocity': buff.velocity,
                    'sign': self.Sign,
                    'time': buff.time,
                    'settings': self.MotorSettings,
                    'info_data': self.InfoData
                }        
                self.Moving = data["stm_status"]
                self.Position = data["position"]

            if self._data is not None:

                if 'command' in self._data.keys():           

                    if self._data['command']['type'] == 'stm':
                        self.out.stm_control = ctypes.c_uint16(int(self._data['command']['value'],2))
                    elif self._data['command']['type'] == 'pos':
                        self.out.pos_control = ctypes.c_uint16(int(self._data['command']['value'],2))
                    self.write(self.out)
                    del self._data['command']

                if 'clear' in self._data.keys():

                    self.write(bytearray(len(self.Device.output)))
                    del self._data['clear']

                if 'disable' in self._data.keys():
                    
                    self.out.pos_control = ctypes.c_uint16(int(NanotecMotionController.POS_DISABLE,2))
                    self.write(self.out)
                    del self._data['disable']

                if 'enable' in self._data.keys():
                    
                    self.out.stm_control = ctypes.c_uint16(int(NanotecMotionController.STM_ENABLE,2))
                    self.write(self.out)
                    del self._data['enable']
                                
                if 'reset' in self._data.keys():

                    self.out.stm_control = ctypes.c_uint16(int(NanotecMotionController.STM_RESET,2))
                    self.write(self.out)
                    del self._data['reset']

                if 'adjust' in self._data.keys():
                                        
                    self.out = NanotecMotionController.RxMap()
                    self.out.stm_control = ctypes.c_uint16(int(NanotecMotionController.STM_ENABLE,2))
                    self.out.pos_control = ctypes.c_uint16(int(NanotecMotionController.POS_DISABLE,2))
                    self.out.start = ctypes.c_uint16(self._data['adjust']['type'])
                    self.write(self.out)

                    del self._data['adjust']

                if 'sign' in self._data.keys():    
                    self.Sign = int(self._data['sign'])
                    del self._data['sign']
                
                if 'motion' in self._data.keys():
                    
                    self.out = NanotecMotionController.RxMap()
                    self.out.stm_control = ctypes.c_uint16(int(NanotecMotionController.STM_ENABLE,2))
                    self.out.pos_control = ctypes.c_uint16(int(NanotecMotionController.POS_DISABLE,2))
                    self.out.position = ctypes.c_uint32(self._data['motion']['position'])
                    self.out.velocity = ctypes.c_int16(self._data['motion']['velocity']) 
                    self.out.start = ctypes.c_uint16(self._data['motion']['type']) 
                    self.write(self.out)

                    del self._data['motion']

                if 'execute' in self._data.keys():
                    
                    self.out.pos_control = ctypes.c_uint16(int(NanotecMotionController.POS_EXECUTE,2))
                    self.write(self.out)
                    del self._data['execute']                

                if 'halt' in self._data.keys():

                    self.out.pos_control = ctypes.c_uint16(int(NanotecMotionController.POS_HALT,2))
                    self.write(self.out)

                    del self._data['halt']

        except Exception as ex:
            self.error(ex)
        
        finally:
            self._lock.release()

        return data

    def write(self, data):
        self.DeviceLock.acquire()
        try:
            self.Device.output = bytes(data)
        finally:
            self.DeviceLock.release()

    def error(self, value):

        EcatLogger.debug(f"### {value}")
        EcatLogger.debug(f"    {value.__doc__}")

        if isinstance(value, pysoem.Emergency):
            
            EcatLogger.debug(f"    {value.error_code}")
            EcatLogger.debug(f"    {pysoem.al_status_code_to_string(value.error_code)}")

            EcatLogger.debug(f"    {value.error_reg}")

            b1, w1, w2 = ctypes.c_uint8(value.b1).value, ctypes.c_uint16(value.w1).value, ctypes.c_uint16(value.w2).value

            EcatLogger.debug(f"    {b1} {pysoem.al_status_code_to_string(b1)}")
            EcatLogger.debug(f"    {w1} {pysoem.al_status_code_to_string(w1)}")
            EcatLogger.debug(f"    {w2} {pysoem.al_status_code_to_string(w2)}")

    def output(self, data):

        if not self.Enabled:
            return False
        
        self._lock.acquire()
        try:
            self._data = data.copy()            

        except Exception as ex:
            EcatLogger.error(f"NanotecMotionController.output {ex}")

        finally:
            self._lock.release()
            return True
        
    _moving = False
    def _get_moving(self):
        return self._moving
    def _set_moving(self, value):
        value = list(value)[::-1]
        self._moving = value[4] == '1' or value[5] == '1'
    Moving = property(fget=_get_moving, fset=_set_moving)

    _position = None
    def _get_position(self):
        return self._position
    def _set_position(self, value):
        self._position = value
    Position = property(fget=_get_position, fset=_set_position)
                
    def callback(self, *args):

        arg = args[0]        
        
        name = arg["name"]

        if name == "EL6090":
            
            button = arg["value"]["value"]["button"]

            # _ up (unlock brake), D down, L left, R right, M motor

            #      _
            #      
            # L    M    R
            #       
            #      D

            steps = 12800 # 360°
            ratio = 50
                        
            position = {                
                "D": 0, 
                "L": steps * ratio / 4, 
                "R": -1 * steps * ratio / 4
            }  
            
            velocity = 500

            # down
            if button[1]:
                self.output({ "motion": { "position": int(position["D"]), "velocity": velocity, "type": 0 } })

                EcatLogger.debug(f"{velocity} {button} {position}")

            # left
            elif button[2]:
                self.output({ "motion": { "position": int(position["L"]), "velocity": velocity, "type": 0 } })
            # right
            elif button[3]:
                self.output({ "motion": { "position": int(position["R"]), "velocity": velocity, "type": 0 } })
            
            # enter
            if button[4]:                
                if not self.Moving:                    
                    self.output({ "execute": 1 })
                else:
                    self.output({ "halt": 1 })
            

class HiwinMotionController(MotionController):

    class RxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            ('control', ctypes.c_uint16),
            ('mode', ctypes.c_uint8),
            ('torque', ctypes.c_uint16),
            ('position', ctypes.c_int32),
            ('touch', ctypes.c_uint16),
            ('digital', ctypes.c_uint32)
        ]

    class TxMap(ctypes.Structure):
        _pack_ = 1
        _fields_ = [            
            ('errorcode', ctypes.c_uint16),
            ('status', ctypes.c_uint16),
            ('mode', ctypes.c_uint8),
            ('position', ctypes.c_int32),
            ('touch', ctypes.c_uint16),
            ('edge', ctypes.c_int32),
            ('error', ctypes.c_int32),
            ('digital', ctypes.c_uint32),
        ]  

    mode = {
        'none': ( 0,'none'),
        'pp':   ( 1,'profile position'),
        'vv':   ( 2,'velocity'),
        'pv':   ( 3,'profile velocity'),
        'tq':   ( 4,'profile torque'),
        'hm':   ( 6,'homing'),
        'csp':  ( 8,'cyclic synchronous position'),
        'csv':  ( 9,'cyclic synchronous velocity'),
        'cst':  (10,'cyclic synchronous torque'),
    }

    _mode = mode['pv']

    UINT32_MAX = 4_294_967_295
    TORQUE_MAX = 8000
    RPM_MAX = 10000

    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)
    
    _initialized = False
    def _init(self): 

        # 0 free run, 1 synchronous mode
        self.Device.dc_sync(act=0, sync0_cycle_time=250_000)

        self.Device.sdo_write(0x6072, 0, bytes(ctypes.c_uint16(HiwinMotionController.TORQUE_MAX)))
        self.Device.sdo_write(0x2502, 0, bytes(ctypes.c_uint16(HiwinMotionController.RPM_MAX)))
        
        self._initialized = True

    def input(self):

        step = -1

        try:

            cw = bin(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x6040,0x00)).value)[2:].zfill(16)
            sw = bin(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x6041,0x00)).value)[2:].zfill(16)

            step = 0

            vv = [ctypes.c_int32.from_buffer_copy(self.Device.sdo_read(a,0x00)).value for a in [0x606C,0x606B,0x60FF,0x607F]]
            pp = [ctypes.c_int32.from_buffer_copy(self.Device.sdo_read(a,0x00)).value for a in [0x6064,0x6062,0x607A]]

            step = 1

            tt = [ctypes.c_int16.from_buffer_copy(self.Device.sdo_read(a,0x00)).value for a in [0x6077,0x6074,0x6071,0x6072]]

            step = 2

            # motor rated current mA, motor rated torque mNm
            mo = [ctypes.c_int32.from_buffer_copy(self.Device.sdo_read(a,0x00)).value for a in [0x6075,0x6076]]

            step = 3

            # Ut054 motor current
            ut054 = ctypes.c_float.from_buffer_copy(self.Device.sdo_read(0x4054,0x00)).value
            mo = mo + [np.nan_to_num(ut054)]

            step = 4

            # device
            dv = [
                # firmware major.medium.minor
                ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(0x4097,0x00)).value,
                ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x2502,0x00)).value
                ]

            step = 5

            md = self._mode

            ec = bin(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x603f,0x00)).value)[2:].zfill(16)
            em = f'0x{hex(int(ec,2))[2:].zfill(4)}'

            step = 6

            wc, wm = 0,'0x0000'
            for a in [0x3110,0x3111]:
                wc = bin(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(a,0x00)).value)[2:].zfill(16)        
                wm = f'0x{hex(a+int(wc,2))[2:].zfill(4)}'

            step = 7

            if wm == '0x3111':
                wc, wm = 0,'0x0000'

            return {

                'mode': md,

                'status': sw,
                'control': cw,

                'error': em,
                'warn': wm,

                'velocity': vv,
                'position': pp,
                'torque': tt,
                'motor': mo,

                'device': dv
            }

        except Exception as ex:
            EcatLogger.error(f"-- HiwinMotionController.input {step} {ex}")
            return None

    _data = None

    def run(self):

        self._lock.acquire()

        data = None

        try:

            if not self._initialized:
                self._init()

            data = self.input()
        
            if self._data is not None:

                if 'control' in self._data.keys() and self._data['control'] is not None:

                    out = HiwinMotionController.RxMap()
                    out.control = ctypes.c_uint16(int(self._data['control'],2))
                    out.mode = ctypes.c_uint8(self._mode[0])
                    out.torque = ctypes.c_uint16(HiwinMotionController.TORQUE_MAX)
                    self.write(out)

                    self._data['control'] = None

                if 'velocity' in self._data.keys() and self._data['velocity'] is not None:

                    # mode
                    self.Device.sdo_write(0x6060, 0, bytes(ctypes.c_uint8(self._mode[0])))

                    # accel
                    v = int(0.9*HiwinMotionController.UINT32_MAX)
                    self.Device.sdo_write(0x6083, 0, bytes(ctypes.c_uint32(v)))
                    self.Device.sdo_write(0x60C5, 0, bytes(ctypes.c_uint32(v)))
                    # decel
                    v = int(0.9*HiwinMotionController.UINT32_MAX)
                    self.Device.sdo_write(0x6084, 0, bytes(ctypes.c_uint32(v)))
                    self.Device.sdo_write(0x60C6, 0, bytes(ctypes.c_uint32(v)))
                    # quick stop
                    v = int(0.1*HiwinMotionController.UINT32_MAX)
                    self.Device.sdo_write(0x6067, 0, bytes(ctypes.c_uint32(v)))
                    self.Device.sdo_write(0x6068, 0, bytes(ctypes.c_uint32(v)))

                    # target                    
                    v = self._data['velocity']
                    self.Device.sdo_write(0x60FF, 0, bytes(ctypes.c_int32(v)))
                    self.Device.sdo_write(0x607F, 0, bytes(ctypes.c_int32(v)))

                    self._data['velocity'] = None

        except Exception as ex:
            EcatLogger.error(f"-- HiwinMotionController.run {ex}")
        
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
            EcatLogger.error(f"-- HiwinMotionController.output {ex}")

        finally:
            self._lock.release()
        
        return True
            
    def callback(self, *args):
        pass

    def isValid(self):
        return EcatSeverityController.isValid(self._severity)
    
    def severityFunc(self, value):
        self._severity = value        
        if not EcatSeverityController.isValid(self._severity):            
            self._data = { 
                'control': '0000000000000110', 
                'velocity': 0 
            }                