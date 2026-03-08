from _EcatMaster import EcatMaster, EcatLogger, Ed1fMotionController, BeckhoffCouplerController, NOVRAMMemoryController
from _EcatSeverity import SEVERITY_VERBOSE, SEVERITY_CRITICAL, SEVERITY_REASON_SYSTEM, \
    SEVERITY_REASON_PRESSURE, SEVERITY_REASON_TEMPERATURE, SEVERITY_REASON_TIME, SEVERITY_REASON_DISTANCE, SeverityLogger
from _EcatStates import EcatStates

import pysoem, time, ctypes


class EcatMasterED1(EcatMaster):

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

    # motion control

    def configED1F(self, pos, slave):

        rc = super().configED1F(pos, slave)

        if rc:
            slot = 0
            if self.isSlot("drive", (slot, pos)):
                
                self._hiwinMotionController[pos] = Ed1fMotionController(pos, slave, self.ProcessLock)
                self._hiwinMotionController[pos].initEx(source=[
                    { "key": "p", "name": "EL6021.3", "addr": 0x0C, "low": 0, "high": 700 }
                    ])
                self._hiwinMotionController[pos].initConfig()                
                self.SeverityController.register(f"ED1F.{pos}", self._hiwinMotionController[pos].severityFunc)

                EcatLogger.debug(f"init Ed1fMotionController @ {pos}; {EcatStates.desc(slave.state, desc=True)}")
                    
        EcatLogger.debug(f"done with {rc}")
        
        return rc 
        
    # coupler; system

    def configEK1100(self, pos, slave):

        rc = super().configEK1100(pos, slave)

        if rc:
            slot = 1
            if self.isSlot("drive", (slot, pos)): 
                
                self.configSeverity()
                
                self._beckhoffCouplerController[pos] = BeckhoffCouplerController(pos, slave, self.ProcessLock)           
                self.SeverityController.register(f"EK1100.{pos}")
                EcatLogger.debug(f"init BeckhoffCouplerController @ {pos}")
            
        EcatLogger.debug(f"done with {rc}")

        return rc    

    
    def configEL6080(self, pos, slave):

        rc = super().configEL6080(pos, slave)

        if rc:
            slot = 2
            if self.isSlot("drive", (slot, pos)):                               
                self._beckhoffMemoryController[pos] = NOVRAMMemoryController(pos, slave, self.ProcessLock)
                self._beckhoffMemoryController[pos].initConfig()
                self.CallbackController.register(f"EL6080.{pos}", "ED1F.0", self._beckhoffMemoryController[pos].callback)
                EcatLogger.debug(f"init NOVRAMController")

        EcatLogger.debug(f"done with {rc}")

        return rc
    
    def configSeverity(self):
        if self.SeverityLimit.enabled == 1:
            config = self.SeverityLimit.config
            # severity channel
            for target in range(config.control.channel):
                self.SeverityController.register(f"{config.control.item}.{target}", self.SeverityController.controlFunc)
            # severity limit data reload
            self.SeverityController.register(f"{config.control.item}.99")    
   
    