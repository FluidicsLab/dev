from narwhals import UInt32

from _BeckhoffMemoryController import NOVRAMMemoryController
from _EcatMaster import EcatMaster, EcatLogger, BeckhoffCouplerController, NanotecMotionController, BeckhoffDisplayController
from _EcatSeverity import SEVERITY_VERBOSE, SEVERITY_CRITICAL, SEVERITY_REASON_SYSTEM, \
    SEVERITY_REASON_PRESSURE, SEVERITY_REASON_TEMPERATURE, SEVERITY_REASON_TIME, SEVERITY_REASON_DISTANCE, SeverityLogger
from _EcatStates import EcatStates

import pysoem, time, ctypes, math


class EcatMasterNOT(EcatMaster):

    def describe(self):

        EcatLogger.debug(f"{self.Master.__class__.__name__}")
        EcatLogger.debug(f"always release gil   {self.Master.always_release_gil}")
        EcatLogger.debug(f"context initialized  {self.Master.context_initialized}")
        EcatLogger.debug(f"dc time              {self.Master.dc_time}")
        EcatLogger.debug(f"do check state       {self.Master.do_check_state}")
        EcatLogger.debug(f"expected wkc         {self.Master.expected_wkc}")
        EcatLogger.debug(f"in op                {self.Master.in_op}")
        EcatLogger.debug(f"manual state change  {self.Master.manual_state_change}")
        EcatLogger.debug(f"sdo read timeout     {self.Master.sdo_read_timeout}")
        EcatLogger.debug(f"sdo write timeout    {self.Master.sdo_write_timeout}")
        EcatLogger.debug(f"state                {self.Master.state}")

    def __init__(self):
        self.describe()

    #
    # severity section
    #
    
    # motion control

    # TODO
    
    # coupler; several external
    
    def severityEK1100(self, source, data, current, config: dict):        
        severity = current.copy()
        value = data['value']['value']
        if value:
            for addr in list(config.keys()):
                key = "p"
                targets = config[f"{addr}"][key]["channel"]
                limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                if limit is not None:
                    critical = (value[addr][key] < limit["low"] or value[addr][key] > limit["high"])
                    if critical:
                        for target in targets:
                            severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_SYSTEM

                            SeverityLogger.debug(f"1100.{target} {addr} {key} {value[addr][key]}")                               

        return severity
    
    #          

    def severityFunc(self, source, data, current):

        config = self.SeverityLimit

        if 0 == config.enabled:
            return current

        alias, pos = source.split(".")
        severity = current.copy()
        
        if pos in list(config._raw[alias].keys()):

            match alias:
                case "EK1100":
                    severity = self.severityEK1100(source, data, severity, config._raw[alias][pos])
                case _:
                    pass
        
        for channel, _ in enumerate(severity):
            if severity[channel] > current[channel]:
                current[channel] = severity[channel]

        return current

    #
    # config section
    #
    
    # coupler; system

    def configEK1100(self, pos, slave):

        rc = super().configEK1100(pos, slave)

        if rc:
            if self.isSlot("drive", (0, pos)):  

                self._beckhoffCouplerController[pos] = BeckhoffCouplerController(pos, slave, self.ProcessLock, enabled=False)

                self.SeverityController.register(f"EK1100.{pos}")
                
                EcatLogger.debug(f"init BeckhoffCouplerController @ {pos}")
            
        EcatLogger.debug(f"done with {rc}")

        return rc    

    # motion controller

    def configEL7031(self, pos, slave):

        rc = super().configEL7031(pos, slave)

        if rc:

            slot = 1
            if self.isSlot("drive", (slot, pos)):

                self._nanotecMotionController[pos] = NanotecMotionController(pos, slave, self.ProcessLock)
                self._nanotecMotionController[pos].initConfig()              

                EcatLogger.debug(f"init NanotecMotionController @ {pos}")
        
        EcatLogger.debug(f"done with {rc}")
        
        return rc      
    
    # memory controller
    
    def configEL6080(self, pos, slave):

        rc = super().configEL6080(pos, slave)

        if rc:

            if self.isSlot("drive", (2, pos)):

                #self._beckhoffMemoryController[pos] = NOVRAMMemoryController(pos, slave, self.ProcessLock)
                #self._beckhoffMemoryController[pos].initConfig()

                # TODO severity callback

                EcatLogger.debug(f"init  @ {pos}")
        
        EcatLogger.debug(f"done with {rc}")
        
        return rc      
    
    def configEL6090(self, pos, slave):

        def callback(*args):

            controller = self._beckhoffDisplayController[pos]
        
            if not controller.CallbackEnabled:
                return

            arg = args[0]
            name = arg['name']
            
            if 'value' in list(arg['value'].keys()):
            
                value = arg['value']['value']

                if isinstance(value, dict):

                    keys = list(value.keys())

                    if len(keys) > 0:

                        if name == "EL7031":

                            code = controller.Code.copy()
                            code[0]["value"] = controller.CodeMap['DEGREE']
                            code[0]["digit"] = 0
                            controller.Code = code.copy()

                            val = value['position']
                            val = 1 - (0xFFFFFFFF - val) / 12800 if val > 12800 else val / 12800

                            val *= 360.0 * 100

                            vel = value['velocity']
                            vel *= 100
                            
                            data = controller.Data.copy()
                            data[0] =  int(val)
                            data[1] =  int(vel)
                            controller.Data = data.copy()

        rc = super().configEL6090(pos, slave)

        if rc:

            if self.isSlot("drive", (3, pos)):

                EcatLogger.debug(f"** init BeckhoffDisplayController")
                
                self._beckhoffDisplayController[pos] = BeckhoffDisplayController(pos, slave, self.ProcessLock)
                self._beckhoffDisplayController[pos].initConfig()
                self._beckhoffDisplayController[pos].callback = callback
                self._beckhoffDisplayController[pos].CallbackEnabled = True
                
                for (item, ctrl) in [("EL7031.1","EL6090.3")]:
                    self.CallbackController.register(ctrl, item, self._beckhoffDisplayController[pos].callback)
                    self.CallbackController.register(item, ctrl, self._nanotecMotionController[1].callback)
                
                EcatLogger.debug(f"init BeckhoffDisplayController @ {pos}")
        
        EcatLogger.debug(f"done with {rc}")
        
        return rc      

        return True         

    def configSeverity(self):
        if self.SeverityLimit.enabled == 1:
            config = self.SeverityLimit.config
            # severity channel
            for target in range(config.control.channel):
                self.SeverityController.register(f"{config.control.item}.{target}", self.SeverityController.controlFunc)
            # severity limit data reload
            self.SeverityController.register(f"{config.control.item}.99")    
    