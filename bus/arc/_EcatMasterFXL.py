
from _EcatMaster import EcatMaster, EcatLogger, ctypes, BeckhoffPressureController, pysoem, Beckhoff8SwitchController
from _EcatSeverity import SEVERITY_CRITICAL, SEVERITY_VERBOSE


class EcatMasterFXL(EcatMaster):

    def __init__(self):
        pass

    def severityEL2008(self, source, data, current=SEVERITY_VERBOSE):
        severity = current
        try:
            pos = -1
            if "index" in data.keys():
                pos = data["index"]
            if pos in self._beckhoffSwitchController.keys():
                self._beckhoffSwitchController[pos].severityFunc(severity)
        except:
            pass
        return severity

    def configEL3164(self, pos, slave):

        rc = super().configEL3164(pos, slave)

        if rc:

            if self.isSlot("fxl", (2, pos)):

                presentation = [1, 1, 1, 1]
                for i, a in enumerate([0x8000, 0x8010, 0x8020, 0x8030]):
                    # filter setting FIR 50Hz
                    slave.sdo_write(a, 0x15, bytes(ctypes.c_uint16(0)))
                    # enable filter
                    slave.sdo_write(a, 0x06, bytes(ctypes.c_bool(1)))
                    # 
                    slave.sdo_write(a, 0x02, bytes(ctypes.c_uint8(presentation[i])))

        EcatLogger.debug(f"    -- done")        
        return rc
    
    def configEL2008(self, pos, slave):

        rc = super().configEL2008(pos, slave)

        if rc:
            if self.isSlot("fxl", (4, pos)):
                self._beckhoffSwitchController[pos] = Beckhoff8SwitchController(pos, slave, self.ProcessLock)
                self.SeverityController.register("EL2008.4")

        EcatLogger.debug(f"    -- done")

        return rc    
    
    def configEL2809(self, pos, slave):

        rc = super().configEL2809(pos, slave)

        if rc:
            if self.isSlot("fxl", (6, pos)):
                pass

        EcatLogger.debug(f"    -- done")

        return rc        
    
    def configEL3124(self, pos, slave):

        rc = super().configEL3124(pos, slave)

        if rc:

            if self.isSlot("fxl", (2, pos)):
                
                # filter setting FIR 50Hz
                slave.sdo_write(0x8000, 0x15, bytes(ctypes.c_uint16(0)))
                # enable filter (all channels)
                slave.sdo_write(0x8000, 0x06, bytes(ctypes.c_bool(1)))

        EcatLogger.debug(f"    -- done")

        return rc  
            
    def configEL3314(self, pos, slave):

        rc = super().configEL3314(pos, slave)

        if rc:
            
            # Types; 0: K, 4: T
            if self.isSlot("fxl", (5, pos)):

                t = [0, 0, 0, 0]
                for i, a in enumerate([0x8000, 0x8010, 0x8020, 0x8030]):
                    slave.sdo_write(a, 0x19, bytes(ctypes.c_uint16(t[i])))

        EcatLogger.debug(f"    -- done")
        
        return rc
    
    def configEL2502(self, pos, slave):

        rc = super().configEL2502(pos, slave)

        if rc:

            if self.isSlot("fxl", (1, pos)):
                pass             
                
        EcatLogger.debug(f"    -- done")

        return rc
    
    def configEL6021(self, pos, slave):

        rc = super().configEL6021(pos, slave)

        if rc:

            if self.isSlot("fxl", (3, pos)):                
                pass

        EcatLogger.debug(f"    -- done")

        return rc
