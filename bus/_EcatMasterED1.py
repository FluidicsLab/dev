from _EcatMaster import EcatMaster, EcatLogger, HiwinMotionController
from _EcatSeverity import SEVERITY_VERBOSE, SEVERITY_CRITICAL, SEVERITY_REASON_SYSTEM, \
    SEVERITY_REASON_PRESSURE, SEVERITY_REASON_TEMPERATURE, SEVERITY_REASON_TIME, SEVERITY_REASON_DISTANCE, SeverityLogger
from _EcatStates import EcatStates

import pysoem, time, ctypes


class EcatMasterED1(EcatMaster):

    #
    #
    #

    def __init__(self):
        pass

    #
    #
    #
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
        EcatLogger.debug(f"slaves               {len(self.Master.slaves)}")

    def configED1F(self, pos, slave):

        rc = super().configED1F(pos, slave)

        if rc:

            EcatLogger.debug(f"    ** init HiwinMotionController @ {pos}")
            
            self._hiwinMotionController[pos] = HiwinMotionController(pos, slave, self.ProcessLock)
            self.SeverityController.register(f"ED1F.{pos}", self._hiwinMotionController[pos].severityFunc)
                    
        EcatLogger.debug(f"    -- done")
        
        return rc      
   
    