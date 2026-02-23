from _EcatMaster import EcatMaster, EcatLogger, Ed1fMotionController
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

    def severityFunc(self, source, data, current):

        config = self.SeverityLimit

        if 0 == config.enabled:
            return current

        alias, pos = source.split(".")
        severity = current.copy()
        
        if pos in list(config._raw[alias].keys()):

            match alias:
                
                case _:
                    pass
        
        for channel, _ in enumerate(severity):
            if severity[channel] > current[channel]:
                current[channel] = severity[channel]

        return current    

    # motion control

    def configED1F(self, pos, slave):

        rc = super().configED1F(pos, slave)

        if rc:

            if self.isSlot("drive", (0, pos)):
                
                self._hiwinMotionController[pos] = Ed1fMotionController(pos, slave, self.ProcessLock)
                self._hiwinMotionController[pos].initEx(source=[
                    { "key": "p", "name": "EL6021.3", "addr": 0x0C, "low": 0, "high": 700 }
                    ])
                self._hiwinMotionController[pos].initConfig()
                self.SeverityController.register(f"ED1F.{pos}", self._hiwinMotionController[pos].severityFunc)

                EcatLogger.debug(f"init Ed1fMotionController @ {pos}; {EcatStates.desc(slave.state, desc=True)}")
                    
        EcatLogger.debug(f"done with {rc}")
        
        return rc      
   
    