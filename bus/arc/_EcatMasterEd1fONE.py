from _EcatMaster import EcatMaster, EcatLogger, HiwinMotionController
from _EcatSeverity import SEVERITY_VERBOSE


class EcatMasterEd1fONE(EcatMaster):

    def __init__(self):
        pass

    def configED1F(self, pos, slave):

        rc = super().configED1F(pos, slave)

        if rc:

            EcatLogger.debug(f"    ** init HiwinMotionController @ {pos}")
            
            self._hiwinMotionController[pos] = HiwinMotionController(pos, slave, self.ProcessLock)
            self.SeverityController.register(f"ED1F.{pos}", self._hiwinMotionController[pos].severityFunc)
            
        
        EcatLogger.debug(f"    -- done")
        
        return rc      
