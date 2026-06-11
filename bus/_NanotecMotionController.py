
import ctypes, time
import pysoem
import numpy as np
from threading import Lock,Event

from _EcatObject import EcatLogger
from _EcatSeverity import SEVERITY_VERBOSE, EcatSeverityController, SeverityLogger


class NanotecMotionControllerBase(object):

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
    

class NanotecMotionController(NanotecMotionControllerBase):

    STM_ENABLE =    '0000000000000001'
    STM_DISABLE =   '0000000000000000'
    STM_RESET =     '0000000000000010'

    POS_EXECUTE =   '0000000000000001'
    POS_DISABLE =   '0000000000000000'

    POS_HALT =      '0000000000000010'

    class NanotecMotionType:

        ABSOLUTE = 0x01
        RELATIVE = 0x02
        ENDLESS_PLUS = 0x03
        ENDLESS_MINUS = 0x04
        ADDITIVE = 0x05

        @staticmethod
        def isin(type):
            return np.any(type == t for t in [NanotecMotionController.NanotecMotionType.ABSOLUTE, 
                                              NanotecMotionController.NanotecMotionType.RELATIVE,
                                              NanotecMotionController.NanotecMotionType.ENDLESS_PLUS,
                                              NanotecMotionController.NanotecMotionType.ENDLESS_MINUS,
                                              NanotecMotionController.NanotecMotionType.ADDITIVE])
        
    class RxMapEx:
        register = 0x1C12
        address = [0x1602,0x1606]

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

    class TxMapEx:
        register = 0x1C13
        address = [0x1A03,0x1A06]

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

    _initialized = False

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
            
            #
            # PDO
            #

            # inputs; read; slave-master
            addr = NanotecMotionController.TxMapEx.register            
            for i,value in enumerate(NanotecMotionController.TxMapEx.address):
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))

            # outputs; write; master-slave  
            addr = NanotecMotionController.RxMapEx.register            
            for i,value in enumerate(NanotecMotionController.RxMapEx.address): 
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))      

            self._enablePdoAssignment(True)
            # ESM PREOP -> SAFEOP TxPDO effective
            # ESM SAFEOP -> OP TxPDO effective

            #
            # startup
            #

            '''
            STF2818X0504-A
            '''

            # max. current mA            
            self.Device.sdo_write(0x8010, 0x01, bytes(ctypes.c_uint16(500)))
            # reduced current mA
            self.Device.sdo_write(0x8010, 0x01, bytes(ctypes.c_uint16(250)))

            # nominal voltage mV 
            # (rated motor voltage at standstill ~ 1850 mV; 3.7Ohm * 0.5A)
            self.Device.sdo_write(0x8010, 0x03, bytes(ctypes.c_uint16(2000)))
            # motor coil resitance 0.01 Ohm
            self.Device.sdo_write(0x8010, 0x04, bytes(ctypes.c_uint16(400)))
            # motor fullsteps 360° / 1.8° ~ 200
            self.Device.sdo_write(0x8010, 0x06, bytes(ctypes.c_uint16(200)))

            # operation mode 0 automatic            
            self.Device.sdo_write(0x8012, 0x01, bytes(ctypes.c_uint8(0)))
            # speed range 1000 fullsteps/s
            self.Device.sdo_write(0x8012, 0x05, bytes(ctypes.c_uint8(0)))
                        
            # velocity min
            self.Device.sdo_write(0x8020, 0x01, bytes(ctypes.c_int16(50)))
            # velocity max
            self.Device.sdo_write(0x8020, 0x02, bytes(ctypes.c_int16(500)))
            # calib. position
            self.Device.sdo_write(0x8020, 0x08, bytes(ctypes.c_uint32(0)))
  
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
        
        try:
    
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

    _data = None

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
                    acceleration = [ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8020, 0x03)).value, 
                                    ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8020, 0x04)).value],
                    deceleration = [ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8020, 0x05)).value, 
                                    ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(0x8020, 0x06)).value],
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
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(NanotecMotionController.TxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(NanotecMotionController.TxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]
    
    def _set_pdoInput(self, values):
        self.Device.sdo_write(NanotecMotionController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values):
            self.Device.sdo_write(NanotecMotionController.TxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(NanotecMotionController.TxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))
    
    PdoInput = property(fget=_get_pdoInput,fset=_set_pdoInput)
        
    def _get_pdoOutput(self):        
        num = ctypes.c_uint8.from_buffer_copy(self.Device.sdo_read(NanotecMotionController.RxPDO_MAP_ADDRESS, 0)).value
        return [hex(ctypes.c_uint16.from_buffer_copy(self.Device.sdo_read(NanotecMotionController.RxPDO_MAP_ADDRESS, i + 1)).value).replace("0x","").zfill(4) for i in  range(num)]

    def _set_pdoOutput(self, values):        
        self.Device.sdo_write(NanotecMotionController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(0)))
        for i,value in enumerate(values): 
            self.Device.sdo_write(NanotecMotionController.RxPDO_MAP_ADDRESS, i+1, bytes(ctypes.c_uint16(value)))
        num = len(values)
        self.Device.sdo_write(NanotecMotionController.RxPDO_MAP_ADDRESS, 0, bytes(ctypes.c_uint8(num)))

    PdoOutput = property(fget=_get_pdoOutput,fset=_set_pdoOutput)

    def _enablePdoAssignment(self, enable=False):
        try:
            if not enable:
                # DISABLE pdo mapping assignment
                self.Device.sdo_write(NanotecMotionController.TxMapEx.register, 0, bytes(ctypes.c_uint8(0)))
                self.Device.sdo_write(NanotecMotionController.RxMapEx.register, 0, bytes(ctypes.c_uint8(0))) 
            else:
                # ENABLE pdo mapping assignment
                self.Device.sdo_write(NanotecMotionController.TxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(NanotecMotionController.TxMapEx.address))))
                self.Device.sdo_write(NanotecMotionController.RxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(NanotecMotionController.RxMapEx.address)))) 
        except Exception as ex:
            EcatLogger.error(f"{ex}")

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

        EcatLogger.critical(f"{value}")
        EcatLogger.critical(f"{value.__doc__}")

        if isinstance(value, pysoem.Emergency):
            
            EcatLogger.critical(f"{value.error_code}")
            EcatLogger.critical(f"{pysoem.al_status_code_to_string(value.error_code)}")

            EcatLogger.critical(f"{value.error_reg}")

            b1, w1, w2 = ctypes.c_uint8(value.b1).value, ctypes.c_uint16(value.w1).value, ctypes.c_uint16(value.w2).value

            EcatLogger.critical(f"{b1} {pysoem.al_status_code_to_string(b1)}")
            EcatLogger.critical(f"{w1} {pysoem.al_status_code_to_string(w1)}")
            EcatLogger.critical(f"{w2} {pysoem.al_status_code_to_string(w2)}")

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

            # U up, D down, L left, R right, M motor

            #      U
            #      
            # L    M    R
            #       
            #      D

            steps = 200 * 64 # 360°; 200 full steps / rotation; 64 micro steps ~ 200 * 64 = 12800
            offset = 0 # 45°
                        
            position = {                
                "D": offset + 0,                 
                "R": offset + steps / 4,
                "U": offset + steps * 2 / 4,                 
                "L": offset + steps * 3 / 4
            }  
            
            velocity = 500

            # up
            if button[0]:
                self.output({ "motion": { "position": int(position["U"]), "velocity": velocity, "type": 0 } })
            # down
            if button[1]:
                self.output({ "motion": { "position": int(position["D"]), "velocity": velocity, "type": 0 } })
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
       