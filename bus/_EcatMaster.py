
from doctest import debug
from numpy import indices, int32
import pysoem
import time, datetime
from time import perf_counter_ns, perf_counter
import struct,ctypes

from types import SimpleNamespace

from threading import Thread,Event,Lock

import sys

from _EcatObject import EcatObject,EcatError,EcatLayoutError,EcatLogger,EcatSlaveSet
from _EcatSettings import EcatConfig,EcatLayout
from _EcatAdapter import EcatAdapter
from _EcatStates import EcatStates

from _EcatSeverity import EcatSeverityLimit, EcatSeverityController, SEVERITY_VERBOSE

from _EcatBrokerController import EcatBrokerController, EcatCallbackController

from _ModbusController import KellerModbusController, Sth01ModbusController, Wt901cModbusController
from _SerialController import GscSerialController
from _MotionController import NanotecMotionController, HiwinMotionController
from _LightController import CcsLightController

from _DisplayController import BeckhoffDisplayController
from _SwitchController import Beckhoff8SwitchController
from _PressureController import BeckhoffPressureController
from _MultimeterController import BeckhoffMultimeterController
from _TemperatureController import BeckhoffTemperatureController

from _HeatingController import BeckhoffHeatingController
from _AnalogController import BeckhoffAnalogController
from _CouplerController import BeckhoffCouplerController

from _IOLinkController import ifmIOLinkController

from _BeckhoffMotionController import AM8111MotionController

"""

[]_STATE

 0 NONE
 1 INIT
 2 PREOP
 4 SAFEOP
 8 OP
16 ACK
16 ERROR 

"""

TIMEOUT_RECEIVE = 4_000
TIMEOUT_FPWR = 4_000

DELAY_ALIVE_LOOP = 0.5
DELAY_INPUT_LOOP = 0.1
DELAY_OUTPUT_LOOP = 0.1

DELAY_PROCESS_LOOP  = 0.01      # 0.01
DELAY_TOGGLE_LOOP   = 1.0       # 
DELAY_CHECK_LOOP    = 0.1       # 0.01

VERBOSE = 1

PYSOEM_VERSION = [int(v) for v in pysoem.__version__.split('.')]

'''
WATCHDOG_MP = 2498
WATCHDOG_SM = 0.0
WATCHDOG_PD = 0.0
WATCHDOG_FC = 1000 # watchdog factor
'''

class EcatMaster(EcatObject):

    _processLock: Lock = None
    def _get_processLock(self): 
        if self._processLock is None:
            self._processLock = Lock()
        return self._processLock
    ProcessLock: Lock = property(fget=_get_processLock)

    _toggleLock: Lock = None
    def _get_toggleLock(self): 
        if self._toggleLock is None:
            self._toggleLock = Lock()
        return self._toggleLock
    ToggleLock: Lock = property(fget=_get_toggleLock)

    _wkc = 0
    _template = '_EcatLayout'
    _platform = "STD"
    _topic = 'bus'
    _ports = []

    def isTopic(self, topic):
        return self._topic == topic

    def isSlot(self, topic, pos = (0, 0)):
        return self._topic == topic and pos[0] == pos[1]

    _layout = None
    def _get_layout(self):
        if self._layout is None:
            self._layout = {}
            power = 0            
            for i,row in enumerate(EcatLayout(self._template).Data):
                consumption = int(row[4])
                power = consumption if consumption >0 else power +consumption
                alias = row[1]
                valid = power >0 or (power == 0 and alias == 'ED1F')
                prio = int(row[5])
                self._layout[i] = EcatSlaveSet(row[0], alias, int(row[2],16), int(row[3],16), consumption, power, valid, prio)
        return self._layout
    Layout = property(fget=_get_layout)

    _indizes = None
    def _get_indizes(self):
        if self._indizes is None:
            self._indizes = dict()
            for n in self.Layout:
                key = self.Layout[n].alias
                if key not in self._indizes.keys():
                    self._indizes[key] = []
                self._indizes[key].append(n)
            self._indizes = SimpleNamespace(**self._indizes)
        return self._indizes
    Indizes = property(fget=_get_indizes)
        
    _adapter:EcatAdapter = None
    def _get_adapter(self): 
        return self._adapter
    Adapter:EcatAdapter = property(fget=_get_adapter)

    _master:pysoem.Master = None
    def _get_master(self):
        if self._master is None:
            self._master = pysoem.Master()
            self._master.in_op = False
            self._master.do_check_state = True
        return self._master
    Master:pysoem.Master = property(fget=_get_master)

    _watchdog = { "mp": 2498, "fc": 1000.0, "sm": 0.0, "pd": 0.0 }
    def _get_watchdog(self):
        return self._watchdog
    Watchdog = property(fget=_get_watchdog)

    _brokerController: EcatBrokerController = None
    def _get_brokerController(self):
        return self._brokerController
    BrokerController = property(fget=_get_brokerController)
        
    _callbackController: EcatCallbackController = None
    def _get_callbackController(self):
        return self._callbackController
    CallbackController = property(fget=_get_callbackController)

    _severityController: EcatSeverityController = None
    def _get_severityController(self):
        return self._severityController
    SeverityController = property(fget=_get_severityController)   

    """
    
    """    
    def _set_state(self, value):
        EcatLogger.debug(f'--- set state')
        self.Master.state = value
        wkc = self.Master.write_state() 
        state = self.Master.state_check(value, timeout=2_000_000)  
        EcatLogger.debug(f'    {wkc:03d} {EcatStates.desc(value)} ~ {EcatStates.desc(state)}')        
    def _get_state(self): 
        return self.Master.state    
    State = property(fget=_get_state,fset=_set_state)

    """
    
    """        
    def _get_readState(self): 
        # lowest
        state = EcatStates.desc(self.Master.read_state())
        # all
        states = [EcatStates.desc(d.state) for d in self.Devices]
        return state, states
    ReadState = property(fget=_get_readState)

    def debugState(self):
        EcatLogger.debug(f"    >>> debug states")
        rs = self.ReadState[0]
        EcatLogger.debug(f"    {'MASTER':15s} :: {rs} :: {EcatStates.desc(int(rs,2), desc=True)}")
        for i,rs in enumerate(self.ReadState[1]):
            al_status = self.Devices[i].al_status
            al_status_desc = pysoem.al_status_code_to_string(al_status)
            EcatLogger.debug(f"    {self.Devices[i].name:15s} :: {rs} :: {EcatStates.desc(int(rs,2), desc=True):20s} :: {hex(al_status)} :: {al_status_desc}")
        EcatLogger.debug(f"    <<<")

    @staticmethod
    def writeSlaveState(slave, state):
        rc = True
        slave.state = state
        slave.write_state()
        #master.send_processdata()
        #master.receive_processdata(2000)
        # wait on <state>
        timeout = time.time() + 5
        while slave.state != state:
            if time.time() > timeout:                
                rc = False
            if not rc:
                break
            time.sleep(0.1)
        return rc, slave.state   
    
    """
    
    """    
    def _get_devices(self):
        return self.Master.slaves
    Devices = property(fget=_get_devices)

    """
    set terminal watchdog

    pd 0x410
    sm 0x420

       0x400 multiplier 2498 ~ 100 µs

    pd = pd ms
    sm = sm ms
    
    """
    def setWatchDog(self, slave, pd=None, sm=None):

        try:
            if PYSOEM_VERSION[-1] < 6:
                # multiplier
                slave._fpwr(0x400, struct.pack('H',self.Watchdog["mp"]), timeout_us=TIMEOUT_FPWR)
                # process data
                if pd is not None:
                    slave._fpwr(0x410, struct.pack('H',int(pd*10)), timeout_us=TIMEOUT_FPWR)
                # sync manager
                if sm is not None:
                    slave._fpwr(0x420, struct.pack('H',int(sm*10)), timeout_us=TIMEOUT_FPWR)
            else:                
                # process data
                if pd is not None:
                    slave.set_watchdog('pdi', int(pd))
                # sync manager
                if sm is not None:
                    slave.set_watchdog('processdata', int(sm))

            rc = self.getWatchDog(slave)
                        
        except Exception as ex:
            EcatLogger.debug(f"   ! set watchdog failed {sm} {pd}")
        
        finally:
            return rc

    def getWatchDog(self, slave):
        # multiplier, process data, sync manager
        return [struct.unpack("H",slave._fprd(a, 2, timeout_us=TIMEOUT_FPWR)) for a in [0x400,0x410,0x420]]
    
    def setDcSync(self, slave, value):
        slave.dc_sync(value[0], value[1])

    def setPreset(self, slave):
        slave.sdo_write(0x1011,0x01,struct.pack('I',int('0x64616F6C',16)))

    def describe(self):
        pass

    #
    # controller
    #

    _kellerModbusController = {}
    _sht01ModbusController = {}
    _wt901cModbusController = {}
    
    _ifmIOLinkController = {}

    _gscSerialController = {}
    
    _nanotecMotionController = {}
    _hiwinMotionController = {}
    _beckhoffMotionController = {}

    _ccsLightController = {}

    _beckhoffDisplayController = {}
    _beckhoffSwitchController = {}
    _beckhoffMultimeterController = {}
    _beckhoffTemperatureController = {}
    _beckhoffPressureController = {}
    _beckhoffHeatingController = {}
    _beckhoffAnalogController = {}

    _beckhoffCouplerController = {}
    
    #
    # terminal
    #

    def configEK1100(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")
        
        # config by derived class

        return True

    def configEL1008(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")
        
        # config by derived class

        return True

    def configEL1809(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")
        
        # config by derived class

        return True        

    def configEL2809(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")
        
        if (slave.state & pysoem.PREOP_STATE) != pysoem.PREOP_STATE:
            EcatLogger.debug(f"    -- failed")
            return False
    
        # config by derived class
        
        return True

    def configEL2819(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")
        
        if (slave.state & pysoem.PREOP_STATE) != pysoem.PREOP_STATE:
            EcatLogger.debug(f"    -- failed")
            return False
    
        # config by derived class
        
        return True

    def configEL2008(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")
        
        if (slave.state & pysoem.PREOP_STATE) != pysoem.PREOP_STATE:
            EcatLogger.debug(f"    -- failed")
            return False

        # config by derived class

        return True

    def configEL2068(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")
        
        if (slave.state & pysoem.PREOP_STATE) != pysoem.PREOP_STATE:
            EcatLogger.debug(f"    -- failed")
            return False

        # config by derived class

        return True

    def configEL2022(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")
        
        EcatLogger.debug(f"    -- done")
        return True
    
    def configEL4104(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")
        
        if (slave.state & pysoem.PREOP_STATE) != pysoem.PREOP_STATE:
            EcatLogger.debug(f"    -- failed")
            return False

        # config by derived class
        
        return True

    def configEL4002(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")
        
        if (slave.state & pysoem.PREOP_STATE) != pysoem.PREOP_STATE:
            EcatLogger.debug(f"    -- failed")
            return False

        # config by derived class

        return True

    def configEL6021(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False

        for (a,o,v) in [
            
            (0x8000,0x11,6),    # baud rate 9600
            
            (0x8000,0x15,3),    # data frame 8N1
            
            (0x8000,0x06,1),    # half duplex
            (0x8000,0x05,0),    # rate optimization
            
            (0x8000,0x04,0),    # fifo continuous
            (0x8000,0x07,0),    # point to point
            
        ]:  
            try:
                c = slave.sdo_read(a,o)        
                s = len(c)                                                                                                                
                slave.sdo_write(a,o,struct.pack(f'{s}B',v))
            except Exception as ex:
                EcatError.error(f'{a}{o} {ex}')

        # explicit baudrate
        slave.sdo_write(0x8000, 0x1B, bytes(ctypes.c_uint32(9600)))
        
        # config by derived class
                
        return True
    
    def configEL6001(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False

        for (a,o,v) in [
            
            (0x8000,0x11,6), # baud rate 9600            
            (0x8000,0x15,3), # data frame 8N1            
            (0x8000,0x01,1), # rts/cts
            (0x8000,0x02,1), # xon/xoff

            (0x8000,0x04,0), # fifo continuous
            (0x8000,0x05,1), # rate optimization
                        
        ]:  
            try:
                c = slave.sdo_read(a,o)        
                s = len(c)                                                                                                                
                slave.sdo_write(a,o,struct.pack(f'{s}B',v))
            except Exception as ex:
                EcatError.error(ex)
        
        if 3 == pos:
            self._gscSerialController[pos] = GscSerialController(pos, slave, self.ProcessLock)
            EcatLogger.debug(f"    ** init GscSerialController")
        
        EcatLogger.debug(f"    -- done")

        return True    

    def configEL6080(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False
                
        EcatLogger.debug(f"    -- done")

        return True   
    
    def configEL6224(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False

        self._ifmIOLinkController[pos] = ifmIOLinkController(pos, slave, self.ProcessLock)
        self._ifmIOLinkController[pos].PdoInput = [0x1a00]
                
        EcatLogger.debug(f"    -- done")

        return True      

    def configEL6090(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False

        EcatLogger.debug(f"    ** init BeckhoffDisplayController")
        self._beckhoffDisplayController[pos] = BeckhoffDisplayController(pos, slave, self.ProcessLock)
        for item in ["EL7041.3"]:
            self.CallbackController.register(BeckhoffDisplayController.CTRL[0], item, self._beckhoffDisplayController[pos].callback)
                
        EcatLogger.debug(f"    -- done")

        return True        
    
    def configEL3124(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False

        # config by derived class

        return True
    
    def configEL3164(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False

        # config by derived class

        return True
    
    def configEL3314(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False

        # derived class
        
        return True
    
    def configEL3318(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False        
        
        self.setPreset(slave)

        # 0: Type K, 4: Type T
        t = [0, 0]
            
        for i, a in enumerate([0x8000, 0x8010]):
            slave.sdo_write(a, 0x19, bytes(ctypes.c_uint16(t[i])))

        EcatLogger.debug(f"    -- done")
        
        return True    

    def configEL3681(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False        
        
        # config by derived class

        return True    

    def configEL7031(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False
             
        """

        self._nanotecMotionController[pos] = NanotecMotionController(pos, slave, self.ProcessLock)

        if 1 == pos:

            '''
            rotation unit
            '''

            # max. current mA
            slave.sdo_write(0x8010, 0x01, bytes(ctypes.c_int16(710)))
            # nominal voltage mV
            slave.sdo_write(0x8010, 0x03, bytes(ctypes.c_int16(6600)))

            # operation mode 0 automatic            
            slave.sdo_write(0x8012, 0x01, bytes(ctypes.c_uint8(0)))
            # speed range 1000 fullsteps/s
            slave.sdo_write(0x8012, 0x05, bytes(ctypes.c_uint8(0)))
            
            # velocity min
            slave.sdo_write(0x8020, 0x01, bytes(ctypes.c_int16(100)))
            # velocity max
            slave.sdo_write(0x8020, 0x02, bytes(ctypes.c_int16(10_000)))
            # calib. position
            slave.sdo_write(0x8020, 0x08, bytes(ctypes.c_uint32(0)))

            # configure PDO register
            self._nanotecMotionController[pos].PdoInput = [0x1a03, 0x1a06]
            self._nanotecMotionController[pos].PdoOutput = [0x1602, 0x1606]

        elif 3 == pos:

            '''
            beam splitter
            '''

            # max. current mA
            slave.sdo_write(0x8010, 0x01, bytes(ctypes.c_int16(500)))
            # nominal voltage mV
            slave.sdo_write(0x8010, 0x03, bytes(ctypes.c_int16(1850)))

            # operation mode 0 automatic            
            slave.sdo_write(0x8012, 0x01, bytes(ctypes.c_uint8(0)))
            # speed range 1000 fullsteps/s
            slave.sdo_write(0x8012, 0x05, bytes(ctypes.c_uint8(0)))
            
            # velocity min
            slave.sdo_write(0x8020, 0x01, bytes(ctypes.c_int16(50)))
            # velocity max
            slave.sdo_write(0x8020, 0x02, bytes(ctypes.c_int16(500)))
            # calib. position
            slave.sdo_write(0x8020, 0x08, bytes(ctypes.c_uint32(0)))

            # configure PDO register
            self._nanotecMotionController[pos].PdoInput = [0x1a03, 0x1a06]
            self._nanotecMotionController[pos].PdoOutput = [0x1602, 0x1606]

        EcatLogger.debug(f"    -- done")

        """

        # derived class

        return True
    
    def configEL7041(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False
             
        # derived class

        return True
    
    def configEL7201(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False
                     
        # derived class

        return True
    
    def configEL3751(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False
        
        if pos == 21:
            # interface; 15: 0..5V        
            slave.sdo_write(0x8000, 0x01, bytes(ctypes.c_uint16(15)))
            # RTD; none
            slave.sdo_write(0x8000, 0x14, bytes(ctypes.c_uint16(0)))
                
        EcatLogger.debug(f"    -- done")
        return True    
    
    def configED1F(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed; slave not in PREOP state")
            return False        

        # derived class
        
        return True      
    
    def configEL2596(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")
        
        if pos == 15:
            # current control
            slave.sdo_write(0x8004, 0x01, bytes(ctypes.c_uint8(0)))
            # output voltage 2.4W/0.7A = 3.42 white, 3.71 blue
            slave.sdo_write(0x8000, 0x04, bytes(ctypes.c_uint16(342)))
            # target current 700mA
            slave.sdo_write(0x8000, 0x02, bytes(ctypes.c_uint16(700)))
        
        self._ccsLightController[pos] = CcsLightController(pos, slave, self.ProcessLock)
        
        EcatLogger.debug(f"    -- done")
        return True
           
    def configEL2502(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False

        # derived class  

        return True
    
    def configEM3702(self, pos, slave):

        EcatLogger.debug(f"    ++ configure {pos:03d} {slave.name} {slave.state}")

        if (slave.state & pysoem.PREOP_STATE) != slave.state:
            EcatLogger.debug(f"    -- failed")
            return False

        # derived class                

        return True
    
    def configSeverity(self):
        pass    
    
    def configFunc(self, pos): 

        slave = self.Master.slaves[pos]

        if EcatStates.has(pysoem.STATE_ERROR, slave.state):
            try:
                _ = slave.mbx_receive()
            except Exception as ex:
                pass

        alias = self.Layout[pos].alias

        match alias:
            
            case w if w in ['EL1124', 'EL2124']:                
                pass

            case "EK1100":
                self.configEK1100(pos, slave)
                if 0 == pos:
                    self.configSeverity()

            case 'EL1008':
                self.configEL1008(pos, slave)
            case 'EL1809':
                self.configEL1809(pos, slave)

            case 'EL2008':
                self.configEL2008(pos, slave)
            case 'EL2068':
                self.configEL2068(pos, slave)
            case 'EL2022':
                self.configEL2022(pos, slave)
            case 'EL2502':
                self.configEL2502(pos, slave)
            case 'EL2596':
                self.configEL2596(pos, slave)
            
            case 'EL2809':
                self.configEL2809(pos, slave)
            case 'EL2819':
                self.configEL2819(pos, slave)                

            case 'EL6001':                
                self.configEL6001(pos, slave)
            case 'EL6021':                
                self.configEL6021(pos, slave)
            case 'EL6080':
                self.configEL6080(pos, slave)
            case 'EL6090':
                self.configEL6090(pos, slave)

            case 'EL6224':
                self.configEL6224(pos, slave)

            case 'EL4002':
                self.configEL4002(pos, slave)
            case 'EL4104':
                self.configEL4104(pos, slave)

            case 'EL3124':
                self.configEL3124(pos, slave)

            case 'EL3164':
                self.configEL3164(pos, slave)

            case 'EL3314':
                self.configEL3314(pos, slave)
            case 'EL3318':
                self.configEL3318(pos, slave)

            case 'EL3681':
                self.configEL3681(pos, slave)

            case 'EL3751':
                self.configEL3751(pos, slave)

            case 'EL7031':
                self.configEL7031(pos, slave)
            case 'EL7041':
                self.configEL7041(pos, slave)
            case 'EL7201':
                self.configEL7201(pos, slave)

            case 'ED1F':
                self.configED1F(pos, slave)

            case 'EM3702':
                self.configEM3702(pos, slave)

            case _:
                pass    

    _severityLimit = None
    def _get_severityLimit(self):
        if self._severityLimit is None:
            self._severityLimit = EcatSeverityLimit(self._platform).Data
        return self._severityLimit
    SeverityLimit = property(fget=_get_severityLimit)    
    
    def severityFunc(self, source, data, current):        
        return current

    def config_watchdog(self):
        EcatLogger.debug("    + config watchdog")        
        for i,slave in enumerate(self.Master.slaves):            
            wd = self.setWatchDog(slave, sm=self.Watchdog["sm"]*self.Watchdog["fc"], pd=self.Watchdog["pd"]*self.Watchdog["fc"])
            EcatLogger.debug(f"    - {(i):03d} {slave.name} WD {wd}")     
        EcatLogger.debug(f"    - done")
    
    def config_mailbox(self):
        EcatLogger.debug("    + config mailbox")  
        for i,slave in enumerate(self.Master.slaves):            
            slave.add_emergency_callback(self.emergency_callback)
            EcatLogger.debug(f"    - {(i):03d} {slave.name}")     
        EcatLogger.debug(f"    - done")

    def emergency_callback(self, e: pysoem.Emergency):
        EcatLogger.debug("    + emergency callback")
        EcatLogger.debug(e)

    def send(self):        
        return self.Master.send_processdata()
        
    def receive(self):
        return self.Master.receive_processdata(timeout=TIMEOUT_RECEIVE)

    def layoutCheck(self):
        
        EcatLogger.debug(f"    + layout check by {self._template}")
        try:    

            hh = ['no','name','alias','power',' ', 'prio', 'vld', 'state', 'rev']
            EcatLogger.debug(f"    {hh[0]:>3} {hh[1]:<15} {hh[2]:<11} {hh[7]:>4} {hh[3]:>6} {hh[4]:>6} {hh[5]:>6}   {hh[6]:<5} {hh[7]:<8}")

            for n,slave in enumerate(self.Master.slaves):                
                
                term = self.Layout[n]
                
                consumption = str(term.consumption)
                power = str(term.power)
                valid = term.valid
                prio = term.priority
                state = EcatStates.desc(slave.state)

                rev = int(hex(slave.rev)[:4],16)
                
                EcatLogger.debug(f"    {n:03d} {slave.name:<15} {term.alias:<11} {rev:>4} {power:>6} {consumption:>6} {prio:>6}   {str(valid):<5} {state:<8}")

                if (slave.name != term.name) or (slave.man != term.vendor_id) or (slave.id != term.product_code):
                    raise EcatLayoutError(f"unexpected layout at position {n} {slave.name}")
                
                slave.config_func = self.configFunc                
                slave.is_lost = False

            EcatLogger.debug("    - done")

        except Exception as ex:
            EcatError.error(ex)
            EcatLogger.debug("    - failed")
            return False
                   
        return True
    
    def failsafe(self):

        self.Master.state = pysoem.SAFEOP_STATE
        
        self.send()
        self.receive()
    
        self.Master.write_state()
            
    def writeMasterState(self, state=pysoem.OP_STATE):
    
        EcatLogger.debug(f"    + switch to {EcatStates.desc(state, desc=True)} from {EcatStates.desc(self.Master.state_check(pysoem.SAFEOP_STATE, 50_000), desc=True)}")

        rc = True

        self.Master.state = state
        self.Master.write_state()
        
        timeout = 5.0  # seconds
        start_time = time.time()
        while self.Master.state_check(state, timeout=50_000) != state:
            if time.time() - start_time > timeout:
                rc = False
                break
        EcatLogger.debug(f"    - done OP={rc} by {time.time() - start_time}s")

        """
        rc = False
        k = 0
        for _ in range(40):
            self.Master.state_check(pysoem.OP_STATE, 50_000)
            if self.Master.state == pysoem.OP_STATE:
                rc = True
                break
            k += 1

        EcatLogger.debug(f"    - done OP={rc} by {k}x50ms")
        """
        return rc
    
    _running = False
    
    def run(self):

        EcatLogger.debug("--- run")

        if not self.layoutCheck():
            return False
        
        EcatLogger.debug("    + start alive threading")

        self._aliveThread = Thread(target=self._aliveLoop)
        self._aliveThread.start()        

        EcatLogger.debug(f"    - done")

        self.config_mailbox()
        self.config_watchdog()
        self.config_map()  

        if self.Master.state_check(pysoem.SAFEOP_STATE, 500_000) != pysoem.SAFEOP_STATE:      
            EcatLogger.debug("    -- master NOT in SAFEOP_STATE")    
        else:
            EcatLogger.debug("    ++ master in SAFEOP_STATE")    
        
        # config dc
        self.config_dc()
        EcatLogger.debug(f"    ++ master dc time {self.Master.dc_time}") 

        self._running = self.writeMasterState(pysoem.OP_STATE)
        if self.Master.state_check(pysoem.OP_STATE, 500_000) != pysoem.OP_STATE:      
            EcatLogger.debug("    -- master NOT in OP_STATE") 
        else:
            EcatLogger.debug("    ++ master in OP_STATE") 

        #
        #
        #

        EcatLogger.debug("    + start process threading")

        self._processThread = Thread(target=self._processLoop)
        self._toggleThread = Thread(target=self._toggleLoop)
        self._checkThread = Thread(target=self._checkLoop)
        
        self._processThread.start()
        self._toggleThread.start()
        self._checkThread.start()

        self._inputThread = Thread(target=self._inputLoop)
        self._inputThread.start()

        self._outputThread = Thread(target=self._outputLoop)
        self._outputThread.start()
        
        EcatLogger.debug(f"    - done")
            
        self._runningLoop()

        EcatLogger.debug("    + stop process threading")

        self._checkEvent.set()
        self._toggleEvent.set()
        self._processEvent.set()

        self._inputEvent.set()
        self._outputEvent.set()

        self._checkThread.join()
        self._toggleThread.join()
        self._processThread.join()

        self._inputThread.join()
        self._outputThread.join()

        EcatLogger.debug(f"    - done")

        self._aliveEvent.set()

        EcatLogger.debug("    + stop alive threading")
        self._aliveThread.join()

        EcatLogger.debug(f"    - done")

        self.Master.state = pysoem.INIT_STATE
        self.Master.write_state()
        
        return True
    
    _runningEvent = Event()    
    def _runningLoop(self):

        EcatLogger.debug("    + start running loop")

        try:
            while not self._runningEvent.is_set():
                self._runningEvent.wait(.1)

        except KeyboardInterrupt:
            EcatLogger.debug('    * ctrl+c')
            self._runningEvent.set()

        EcatLogger.debug("    - end running loop")
    
    def aliveValues(self):

        values = []

        try:      

            for n,slave in enumerate(self.Master.slaves):                
                term = self.Layout[n]                                
                values.append({
                    'index': n,
                    'name': term.name,
                    'alias': term.alias,
                    'vendor': term.vendor_id,
                    'product': term.product_code,
                    'power': term.power,
                    'priority': term.priority,
                    'consumption': term.consumption,
                    'esm': EcatStates.desc(slave.state,desc=True),
                    'lost': slave.is_lost,
                    'modified': time.time_ns(),
                    'wkc': self._wkc
                    }
                )
        except:
            pass
                   
        return values

    _aliveEvent = Event()
    _aliveThread = None
    
    def _aliveLoop(self):

        EcatLogger.debug(f"    + start alive loop by {self._topic}")

        while not self._aliveEvent.is_set():

            values = self.aliveValues()
            self.publish(
                self._topic,
                -1,
                {
                    'name': self._topic,
                    'index': -1,
                    'value': values,
                }
            )
                        
            self._aliveEvent.wait(DELAY_ALIVE_LOOP)

        EcatLogger.debug("    - end alive loop")

        return True
    
    # --------------------------------------
    # output / callback
    # --------------------------------------

    def callback(self, *args):
        if self.BrokerController is not None:
            return self.BrokerController.pop(args[0], args[1])

    _outputEvent = Event()
    _outputThread = None  

    def write_(self, slave, data):
        self.ProcessLock.acquire()
        try:
            slave.output = data
        finally:
            self.ProcessLock.release()
        
    def _outputLoop(self):

        self.Master.in_op = True

        EcatLogger.debug("    + start output loop")

        keys = self.Indizes.__dict__.keys()

        n_count = 0
        loop_count = 0
        severity_count = 0

        slaves = self.Master.slaves
        nn = sorted(self.Layout, key=lambda n: (self.Layout[n].priority, n), reverse=False)

        while not self._outputEvent.is_set():

            start_time = perf_counter_ns()

            # severity 
            
            if self.SeverityLimit.enabled == 1:

                alias = self.SeverityLimit.config.control.item
                for n in range(self.SeverityLimit.config.control.channel):
                    data = self.callback(alias, n)
                    if data is None:
                        continue
                    self.emit(
                        alias, 
                        n, 
                        {
                            'name': alias,
                            'index': n,
                            'value': data
                        })
                n = 99
                data = self.callback(alias, n)
                if data is not None:
                    self.SeverityLimit.reset()
                    self._severityLimit = None

            severity_time = perf_counter_ns()

            # slave loops

            for n in nn:

                slave = slaves[n]
                state = slave.state
                
                if (pysoem.OP_STATE & state) != state:
                    continue

                alias = self.Layout[n].alias
                data = self.callback(alias, n)

                if data is None:
                    continue

                if 'EL2124' in keys and n in self.Indizes.EL2124:
                    v = int("".join([str(v) for v in data]),2)                    
                    self.write_(slave, struct.pack('1B', v))

                elif 'EL2809' in keys and n in self.Indizes.EL2809:           
                    h = "".join([str(v) for v in data[7::-1]])
                    l = "".join([str(v) for v in data[:7:-1]])
                    self.write_(slave, struct.pack('2B', int(h,2), int(l,2)))

                elif 'EL2819' in keys and n in self.Indizes.EL2819:
                    h = "".join([str(v) for v in data[7::-1]])
                    l = "".join([str(v) for v in data[:7:-1]])
                    self.write_(slave, struct.pack('2B', int(h,2), int(l,2)))

                elif 'EL2008' in keys and n in self.Indizes.EL2008:
                    if n in self._beckhoffSwitchController.keys():
                        self._beckhoffSwitchController[n].output(data)
                    else:
                        b = "".join([str(v) for v in data])                    
                        self.write_(slave, struct.pack('1B', int(b,2)))

                elif 'EL2068' in keys and n in self.Indizes.EL2068:
                    b = "".join([str(v) for v in data])                    
                    self.write_(slave, struct.pack('1B', int(b,2)))

                elif 'EL2022' in keys and n in self.Indizes.EL2022:                    
                    b = "".join([str(v) for v in data])                    
                    self.write_(slave, struct.pack('1B', int(b,2)))      

                # 
                # controller based
                #                   
                elif 'EK1100' in keys and n in self.Indizes.EK1100:
                    if n in self._beckhoffCouplerController.keys():
                        self._beckhoffCouplerController[n].output(data)

                elif 'EL4002' in keys and n in self.Indizes.EL4002:
                    if n in self._beckhoffAnalogController.keys():
                        self._beckhoffAnalogController[n].output(data)

                elif 'EL4104' in keys and n in self.Indizes.EL4104:
                    if n in self._beckhoffAnalogController.keys():
                        self._beckhoffAnalogController[n].output(data)              

                elif 'EL2502' in keys and n in self.Indizes.EL2502:
                    if n in self._beckhoffHeatingController.keys():
                        self._beckhoffHeatingController[n].output(data)
                                    
                elif 'EL3681' in keys and n in self.Indizes.EL3681:
                    if n in self._beckhoffMultimeterController.keys():
                        self._beckhoffMultimeterController[n].output(data)

                elif 'EL6001' in keys and n in self.Indizes.EL6001:
                    if n in self._gscSerialController.keys():
                        self._gscSerialController[n].subscribe(data)

                elif 'EL6090' in keys and n in self.Indizes.EL6090:
                    if n in self._beckhoffDisplayController.keys():
                        self._beckhoffDisplayController[n].output(data)

                elif 'EL2596' in keys and n in self.Indizes.EL2596:
                    if n in self._ccsLightController.keys():
                        self._ccsLightController[n].output(data)

                #
                # motion
                #                
                
                elif 'EL7031' in keys and n in self.Indizes.EL7031:
                    if n in self._nanotecMotionController.keys():
                        self._nanotecMotionController[n].output(data)

                elif 'EL7041' in keys and n in self.Indizes.EL7041:
                    if n in self._nanotecMotionController.keys():
                        self._nanotecMotionController[n].output(data)

                elif 'EL7201' in keys and n in self.Indizes.EL7201:
                    if n in self._beckhoffMotionController.keys():
                        self._beckhoffMotionController[n].output(data)

                elif 'ED1F' in keys and n in self.Indizes.ED1F:
                    if n in self._hiwinMotionController.keys():
                        self._hiwinMotionController[n].output(data)
                
                self.emit(
                    alias, 
                    n, 
                    {
                        'name': alias,
                        'index': n,
                        'value': data
                    })
                
            loop_time = perf_counter_ns()
            
            n_count = 1 if n_count == 0 else 2
            
            loop_count = (loop_count + loop_time - severity_time) / n_count
            severity_count = (severity_count + severity_time - start_time) / n_count
            
            # loop

            self._outputEvent.wait(DELAY_OUTPUT_LOOP)

        EcatLogger.debug("    - end output loop")

    def emit(self, *args):

        if self.CallbackController is not None:
            self.CallbackController.push(args[0], args[1], args[2])

        if self.SeverityController is not None and \
            self.SeverityLimit.enabled == 1:
                self.SeverityController.push(args[0], args[1], args[2], self.SeverityLimit.config)            

    # --------------------------------------
    # input / publish 
    # --------------------------------------

    def publish(self, *args):
        if self.BrokerController is not None:
            self.BrokerController.push(args[0], args[1], args[2])
        self.emit(*args)
               
    _inputEvent = Event()
    _inputThread = None

    def _inputLoop(self):

        EcatLogger.debug("    + start input loop")

        self.Master.in_op = True
                    
        keys = self.Indizes.__dict__.keys()
        slaves = self.Master.slaves
        nn = sorted(self.Layout, key=lambda n: (self.Layout[n].priority, n), reverse=False)
                
        while not self._inputEvent.is_set():
            
            for n in nn:

                slave = slaves[n]
                state = slave.state

                if (pysoem.OP_STATE & state) != state:
                    continue

                alias = self.Layout[n].alias

                data = None

                # analog in

                if 'EL6021' in keys and n in self.Indizes.EL6021:                                        
                    # pressure/temperature values pumps
                    if n in self._kellerModbusController.keys(): 
                        data = self._kellerModbusController[n].run() 
                    # temperature and humidity
                    if n in self._sht01ModbusController.keys(): 
                        data = self._sht01ModbusController[n].run()                    
                    # gyro
                    if n in self._wt901cModbusController.keys(): 
                        data = self._wt901cModbusController[n].run()

                elif 'EL6001' in keys and n in self.Indizes.EL6001:
                    # gsc-01 controller
                    if n in self._gscSerialController.keys(): 
                        data = self._gscSerialController[n].run()

                elif 'EL2008' in keys and n in self.Indizes.EL2008:
                    if n in self._beckhoffSwitchController.keys(): 
                        data = self._beckhoffSwitchController[n].run()

                elif 'EL6090' in keys and n in self.Indizes.EL6090:
                    if n in self._beckhoffDisplayController.keys(): 
                        data = self._beckhoffDisplayController[n].run()

                elif 'EL6224' in keys and n in self.Indizes.EL6224:

                    if n in self._ifmIOLinkController.keys():
                        data = self._ifmIOLinkController[n].run()

                elif 'EL7031' in keys and n in self.Indizes.EL7031:
                    # motion control
                    if n in self._nanotecMotionController.keys():
                        data = self._nanotecMotionController[n].run()

                elif 'EL7041' in keys and n in self.Indizes.EL7041:
                    # motion control
                    if n in self._nanotecMotionController.keys():
                        data = self._nanotecMotionController[n].run()

                elif 'EL7201' in keys and n in self.Indizes.EL7201:
                    # motion control
                    if n in self._beckhoffMotionController.keys():
                        data = self._beckhoffMotionController[n].run()

                elif 'ED1F' in keys and n in self.Indizes.ED1F:
                    # motion control
                    if n in self._hiwinMotionController.keys():
                        data = self._hiwinMotionController[n].run()

                elif 'EL2596' in keys and n in self.Indizes.EL2596:
                    # light control
                    if n in self._ccsLightController.keys():
                        data = self._ccsLightController[n].run()

                elif 'EL3681' in keys and n in self.Indizes.EL3681:
                    # 
                    if n in self._beckhoffMultimeterController.keys():
                        data = self._beckhoffMultimeterController[n].run()

                elif 'EL3314' in keys and n in self.Indizes.EL3314:
                        
                    # thermocouples 
                    
                    data = slave.input
                    
                    if len(data) == 16:

                        ch = 4
                        fact = 1.0                        

                        data = struct.unpack(f'{2*ch}h', data)
                        data = [data[2*i+1]*fact for i in range(ch)]

                    else:
                        data = None                        

                elif 'EL3318' in keys and n in self.Indizes.EL3318:
                        
                    # thermocouples 
                    
                    data = slave.input
                    
                    if len(data) == 32:

                        ch = 8
                        fact = 1.0                        

                        data = struct.unpack(f'{2*ch}h', data)
                        data = [data[2*i+1]*fact for i in range(ch)]

                    else:
                        data = None                        

                elif 'EL3124' in keys and n in self.Indizes.EL3124:
                        
                    # laser values
                    
                    data = slave.input
                    if len(data) == 16:
                        
                        ch = 4
                        fact = (20.-4.)/0x7fff                                
                        
                        raw = struct.unpack(f'{2*ch}h', data)
                        data = [raw[2*i+1]*fact for i in range(ch)]
                    
                    else:
                        data = None

                elif 'EL3164' in keys and n in self.Indizes.EL3164:
                        
                    # supply values
                    
                    data = slave.input
                    if len(data) == 16:
                        
                        ch = 4
                        fact = (10.-0.)/0x7fff                                
                        
                        data = struct.unpack(f'{2*ch}h', data)
                        data = [data[2*i+1]*fact for i in range(ch)] 

                    else:
                        data = None

                elif 'EL3751' in keys and n in self.Indizes.EL3751:

                    try:

                        data = [                        
                            # adc raw value
                            ctypes.c_int32.from_buffer_copy(slave.sdo_read(0x9000,0x02)).value, 
                            # calibration value
                            ctypes.c_int32.from_buffer_copy(slave.sdo_read(0x9000,0x03)).value, 
                            # temperature value
                            ctypes.c_int16.from_buffer_copy(slave.sdo_read(0x9000,0x01)).value, 
                            # proper timestamp
                            time.time_ns() // 1_000_000
                        ]
                    except Exception as ex:
                        EcatLogger.debug(f"{ex}")

                # digital in

                elif 'EL1809' in keys and n in self.Indizes.EL1809:
                    # status values
                    data = slave.input
                    data = struct.unpack(f'2B', data)                    
                    data = [int(n) for n in bin(data[1])[2:].zfill(8)] + [int(n) for n in bin(data[0])[2:].zfill(8)]
                    data = data[::-1]

                elif 'EL1008' in keys and n in self.Indizes.EL1008:
                    # status values
                    data = slave.input
                    data = struct.unpack(f'1B', data)                    
                    data = [int(n) for n in bin(data[0])[2:].zfill(8)]
                    data = data[::-1]

                elif 'EL1124' in keys and n in self.Indizes.EL1124:
                    # status values
                    data = slave.input
                    data = struct.unpack(f'1B', data)[0]

                elif 'EL3202' in keys and n in self.Indizes.EL3202:
                    if n in self._beckhoffTemperatureController.keys():
                        data = self._beckhoffTemperatureController[n].run()  

                # analog in                     

                elif 'EL4002' in keys and n in self.Indizes.EL4002:
                    if n in self._beckhoffAnalogController.keys():
                        data = self._beckhoffAnalogController[n].run()

                elif 'EL4104' in keys and n in self.Indizes.EL4104:
                    if n in self._beckhoffAnalogController.keys():
                        data = self._beckhoffAnalogController[n].run()

                elif 'EM3702' in keys and n in self.Indizes.EM3702:
                    if n in self._beckhoffPressureController.keys():
                        data = self._beckhoffPressureController[n].run()

                # coupler

                elif 'EK1100' in keys and n in self.Indizes.EK1100:
                    if n in self._beckhoffCouplerController.keys():
                        data = self._beckhoffCouplerController[n].run()                        

                else:
                    pass
                        
                if data is None:
                    continue

                self.publish(
                    alias, 
                    n, 
                    {
                        'name': alias,
                        'index': n,
                        'value': data
                    })

            # severity

            if self.SeverityLimit.enabled == 1:

                self.publish(
                        "SEVERITY", 
                        -1,
                        {
                            'name': "SEVERITY",
                            "index": -1,
                            "value": self._severityController.Severity
                        }
                        )

            self._inputEvent.wait(DELAY_INPUT_LOOP)

        EcatLogger.debug("    - end input loop")
            
    _processEvent = Event()
    _processThread = None

    def _processLoop(self, enabled=True):

        EcatLogger.debug("    + start process loop")

        while not self._processEvent.is_set():

            self.ProcessLock.acquire()
            try:

                self.send()    
                self._wkc = self.receive()                       
                        
                if (self._wkc != self.Master.expected_wkc) and self._wkc != -1:
                    EcatLogger.debug(f'    WKC {self._wkc} != {self.Master.expected_wkc} (expected)')
                    for slave in self.Master.slaves:
                        EcatLogger.debug(f'        {slave.name} {slave.al_status} {slave.state} {slave.is_lost}')

            finally:
                self.ProcessLock.release()

            self._processEvent.wait(DELAY_PROCESS_LOOP)

        EcatLogger.debug("    - end process loop")

    _toggleEvent = Event()
    _toggleThread = None

    def _toggleLoop(self, enabled=True):

        EcatLogger.debug("    + start toggle loop")

        keys = self.Indizes.__dict__.keys()
        slaves = self.Master.slaves
        nn = sorted(self.Layout, key=lambda n: (self.Layout[n].priority, n), reverse=False)

        while not self._toggleEvent.is_set():

            self.ToggleLock.acquire()
            try:

                for n in nn:

                    slave = slaves[n]
                    state = slave.state

                    if (pysoem.OP_STATE & state) != state:
                        continue

                    if 'EL7201' in keys and n in self.Indizes.EL7201:
                        # motion control
                        if n in self._beckhoffMotionController.keys():
                            self._beckhoffMotionController[n].toggle()

            finally:
                self.ToggleLock.release()

            self._toggleEvent.wait(DELAY_TOGGLE_LOOP)

        EcatLogger.debug("    - end toggle loop")    
    
    _checkEvent = Event()
    _checkThread = None

    @staticmethod
    def _checkSlave(slave, pos, verbose=0):

        name = slave.name
        state = slave.state
        al_status = slave.al_status
        title = f"{pos:03d} {name} {EcatStates.desc(state,desc=1)} [{hex(al_status)}]"
        
        if state == (pysoem.SAFEOP_STATE + pysoem.STATE_ERROR):
            if verbose:
                EcatLogger.debug(f'    {title} -> {EcatStates.desc(pysoem.SAFEOP_STATE+pysoem.STATE_ACK,desc=1)}')        
            slave.state = pysoem.SAFEOP_STATE + pysoem.STATE_ACK
            slave.write_state()        
        elif slave.state == pysoem.SAFEOP_STATE:

            if verbose:
                EcatLogger.debug(f'    {title} -> {EcatStates.desc(pysoem.OP_STATE,desc=1)}')
            
            slave.state = pysoem.OP_STATE
            slave.write_state()

        elif slave.state > pysoem.NONE_STATE:
            if slave.reconfig():
                slave.is_lost = False
                if verbose:
                    EcatLogger.error(f'    {title} reconfigured')
        elif not slave.is_lost:
            slave.state_check(pysoem.OP_STATE)
            if slave.state == pysoem.NONE_STATE:
                slave.is_lost = True
                if verbose:
                    EcatLogger.error(f'    {title} lost')
        if slave.is_lost:
            if slave.state == pysoem.NONE_STATE:
                if slave.recover():
                    slave.is_lost = False
                    if verbose:
                        EcatLogger.error(f'    {title} recovered')
            else:
                slave.is_lost = False
                if verbose:
                    EcatLogger.debug(f'    {title} found')

    def _hasLost(self):
        for i, slave in enumerate(self.Master.slaves):
            if slave.is_lost:
                return True
        return False
    
    def _checkLoop(self):

        EcatLogger.debug("    + start check loop")

        while not self._checkEvent.is_set():
            
            if self.Master.in_op and ((self._wkc < self.Master.expected_wkc) or self.Master.do_check_state):
                    
                self.Master.do_check_state = False
                self.Master.read_state()
                
                for i, slave in enumerate(self.Master.slaves):

                    if (slave.state & pysoem.OP_STATE) != pysoem.OP_STATE:

                        self.Master.do_check_state = True
                        EcatMaster._checkSlave(slave, i, verbose=VERBOSE)
                
                #if not self.Master.do_check_state:
                #    EcatLogger.debug(f'    all slaves resumed OP')
            
            self._checkEvent.wait(DELAY_CHECK_LOOP)

        EcatLogger.debug("    - end check loop")

    def config_map(self):
        EcatLogger.debug("    + config map")
        size = -1
        try: 
            size = self.Master.config_map()
        except Exception as ex:
            EcatError.error(ex)
        finally:
            EcatLogger.debug(f"    - done {size} < 4096")
        return size

    def config_dc(self):
        EcatLogger.debug("--- config dc")
        rc = -1,0
        try:
            rc = self.Master.config_dc()            
        except Exception as ex:
            EcatError.error(ex)
        finally:
            EcatLogger.debug(f"    {rc}")
        return rc
   
    def config_init(self):

        EcatLogger.debug("--- config_init")
        rc = -1
        try:
            rc = self.Master.config_init()
            EcatLogger.debug(f"    {rc:03d}")
                     
        except Exception as ex:
            EcatError.error(ex)
            rc = -1        
        finally:
            return rc
        
    def open(self):
        EcatLogger.debug("--- open")
        try:
            self.Master.open(self.Adapter.Name)                        
            return True        
        except Exception as ex:
            EcatError.error(ex)
            return False
        
    def close(self):
        EcatLogger.debug("--- close")       
        try:
            self.Master.close()
            return True        
        except Exception as ex:
            EcatError.error(ex)
            return False
                
    def startup(self):        

        if self.open():
            
            self._brokerController = EcatBrokerController(ports=self._ports)
            self._brokerController.startup()

            self._callbackController = EcatCallbackController()
            self._callbackController.startup()

            self._severityController = EcatSeverityController(self, self.SeverityLimit)
            self._severityController.startup()            

    def release(self):
        
        if self._brokerController is not None:
            self._brokerController.release()
        
        if self._callbackController is not None:
            self._callbackController.release()

        if self._severityLimit is not None:
            self._severityLimit.release()
        if self._severityController is not None:
            self._severityController.release()            
        
        self.close()

        for key in self._gscSerialController.keys():
            if self._gscSerialController[key] is not None:
                self._gscSerialController[key].release()
                self._gscSerialController[key] = None

        for key in self._kellerModbusController.keys():
            if self._kellerModbusController[key] is not None:
                self._kellerModbusController[key].release()
                self._kellerModbusController[key] = None

        for key in self._sht01ModbusController.keys():
            if self._sht01ModbusController[key] is not None:
                self._sht01ModbusController[key].release()
                self._sht01ModbusController[key] = None

        for key in self._wt901cModbusController.keys():
            if self._wt901cModbusController[key] is not None:
                self._wt901cModbusController[key].release()
                self._wt901cModbusController[key] = None

        for key in self._nanotecMotionController.keys():
            if self._nanotecMotionController[key] is not None:
                self._nanotecMotionController[key].release()
                self._nanotecMotionController[key] = None

        for key in self._beckhoffMotionController.keys():
            if self._beckhoffMotionController[key] is not None:
                self._beckhoffMotionController[key].release()
                self._beckhoffMotionController[key] = None

        for key in self._hiwinMotionController.keys():
            if self._hiwinMotionController[key] is not None:
                self._hiwinMotionController[key].release()
                self._hiwinMotionController[key] = None                

        for key in self._ccsLightController.keys():
            if self._ccsLightController[key] is not None:
                self._ccsLightController[key].release()
                self._ccsLightController[key] = None

        for key in self._beckhoffDisplayController.keys():
            if self._beckhoffDisplayController[key] is not None:
                self._beckhoffDisplayController[key].release()
                self._beckhoffDisplayController[key] = None

        for key in self._beckhoffMultimeterController.keys():
            if self._beckhoffMultimeterController[key] is not None:
                self._beckhoffMultimeterController[key].release()
                self._beckhoffMultimeterController[key] = None

        for key in self._beckhoffSwitchController.keys():
            if self._beckhoffSwitchController[key] is not None:
                self._beckhoffSwitchController[key].release()
                self._beckhoffSwitchController[key] = None

        for key in self._beckhoffTemperatureController.keys():
            if self._beckhoffTemperatureController[key] is not None:
                self._beckhoffTemperatureController[key].release()
                self._beckhoffTemperatureController[key] = None    

        for key in self._beckhoffPressureController.keys():
            if self._beckhoffPressureController[key] is not None:
                self._beckhoffPressureController[key].release()
                self._beckhoffPressureController[key] = None

        for key in self._beckhoffHeatingController.keys():
            if self._beckhoffHeatingController[key] is not None:
                self._beckhoffHeatingController[key].release()
                self._beckhoffHeatingController[key] = None           

        for key in self._beckhoffAnalogController.keys():
            if self._beckhoffAnalogController[key] is not None:
                self._beckhoffAnalogController[key].release()
                self._beckhoffAnalogController[key] = None               

        for key in self._beckhoffCouplerController.keys():
            if self._beckhoffCouplerController[key] is not None:
                self._beckhoffCouplerController[key].release()
                self._beckhoffCouplerController[key] = None               

        for key in self._ifmIOLinkController.keys():
            if self._ifmIOLinkController[key] is not None:
                self._ifmIOLinkController[key].release()
                self._ifmIOLinkController[key] = None
        
    def setup(self, adapter:EcatAdapter, platform:str, mandant:str, template:str, topic:str,ports:list):
        self._adapter = adapter
        self._template = template
        self._mandant = mandant
        self._platform = platform
        self._topic = topic
        self._ports = ports

    def watchdog(self, mp:int, fc:float, sm:float, pd:float):
        self._watchdog = {
            "mp": mp,
            "fc": fc,
            "sm": sm,
            "pd": pd
        }

    def _get_names(self):
        return [s.name for s in self.Master.slaves]
    Names = property(fget=_get_names)

    def _get_enabled(self):
        return self.State == pysoem.STATE_OP
    Enabled = property(fget=_get_enabled)

    def __init__(self):
        pass

    def __init__(self,adapter:EcatAdapter, platform:str, mandant:str, template:str, topic:str, ports:list, **kwargs):
        super().__init__()
        self._adapter = adapter
        self._template = template
        self._platform = platform
        self._mandant = mandant
        self._topic = topic
        self._ports = ports
                
    def __str__(self):
        return f"{EcatStates.describe(self.State)} {len(self.Devices)}"
    
    def __desc__(self):

        EcatLogger.debug(f"    {self.Adapter.Address}")
        EcatLogger.debug(f"    {self.Adapter.Desc}")

        for i,device in enumerate(self.Devices):

            state = device.state
            states = EcatStates.describe(state)
           
            EcatLogger.debug(f"{i:>3} {str(device.name)} {states}")


def instance(mandant:str="STD"):

    rc = 0

    module_name = f"_EcatMaster{mandant}" 
    class_name = f"EcatMaster{mandant}"
    
    module = __import__(module_name)
    instance = getattr(module, class_name)()

    if not instance:
        mandant = "STD"
        module_name = f"_EcatMaster{mandant}" 
        class_name = f"EcatMaster{mandant}"
        module = __import__(module_name)
        instance = getattr(module, class_name)()

    if instance:
        EcatLogger.debug(f"--- class {class_name} from module {module_name} instantiated")
    else:
        EcatLogger.debug(f"--- could not instanciate class {class_name} from module {module_name}")
        rc = -4

    return rc, instance


def main():
    
    import os
    os.system('cls')

    rc = 0

    EcatLogger.debug(f"--- pysoem {pysoem.__version__} ({PYSOEM_VERSION})") 
    EcatLogger.debug(f"    process {DELAY_PROCESS_LOOP}s check {DELAY_CHECK_LOOP}") 

    config = EcatConfig(name=sys.argv[1] if len(sys.argv) >1 else "_EcatSettings")

    EcatLogger.debug(f"--- connect adapter {config.Application.display} ({config.Application.version})")   
    
    adapters = EcatAdapter.adapters2(config.Adapter.exclude, active=config.Adapter.active, shift='    ')     
    if len(adapters) == 0:
        EcatLogger.debug(f"    adapter {config.Adapter.active + ' ' if config.Adapter.active is not None else ''}not found")   
        rc = -1
    EcatLogger.debug(f"    {'done' if rc == 0 else 'failed'}")

    if rc == 0:

        adapterNo = 0
        adapter:EcatAdapter = adapters[adapterNo]['value'] 

        EcatLogger.debug(f"--- ping relais {config.Master.ports}")   
        if not EcatBrokerController.ping(config.Master.hosts,config.Master.ports,shift='    '):
            EcatLogger.debug(f"    relais ports not found")   
            rc = -2
        EcatLogger.debug(f"    {'done' if rc == 0 else 'failed'}")

    if rc == 0:

        EcatLogger.debug(f"--- using template {config.Master.template}; mandant {config.Master.mandant}; topic {config.Master.topic}")   

        rc, master = instance(config.Master.mandant)

        if rc == 0:

            master.setup(adapter, config.Master.platform, config.Master.mandant, config.Master.template, config.Master.topic, config.Master.ports)
            master.watchdog(config.Watchdog.mp, config.Watchdog.fc, config.Watchdog.sm, config.Watchdog.pd)
            master.startup()

            if master.config_init() >0:
                master.run()
            else:
                rc = -3
            
            EcatLogger.debug(f"    {'done' if rc == 0 else 'failed'}")

            master.release()

    return rc

if __name__ == '__main__':
    
    main()  


