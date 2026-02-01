
from _EcatMaster import EcatMaster, EcatLogger, KellerModbusController, Sth01ModbusController, ctypes, BeckhoffPressureController
from _EcatSeverity import SEVERITY_CRITICAL, SEVERITY_VERBOSE

import numpy as np


class EcatMasterBusONE(EcatMaster):

    def __init__(self):
        pass

    #
    # severity section
    #

    def severityEL6021(self, source, data, current):
        severity = current.copy()
        value = data['value']['value']
        if value:
            for (stroke, addr, key) in [
                (0, 11, "p"), (0, 11, "T"), 
                (1, 12, "p"), (1, 12, "T")
                ]:
                limit = self.SeverityLimit.find(f"{source}.0x{addr}.{key}")
                if limit is not None and key in list(value.keys()):
                    severity[stroke] |= SEVERITY_CRITICAL if value[addr][key] > limit['high'] or value[addr][key] < limit['low'] else current[stroke]
        return severity

    def severityEL3124(self, source, data, current):
        severity = current.copy()   
        value = data['value']['value']
        if value:
            for stroke, channel in enumerate([0, 1]):
                limit = self.SeverityLimit.find(f"{source}.{channel}")
                if limit is not None:
                    severity[stroke] |= SEVERITY_CRITICAL if value[channel] < limit["low"] or value[channel] > limit["high"] else current[stroke]
        return severity

    def severityFunc(self, source, data, current=SEVERITY_VERBOSE):
        
        severity = current

        alias, _ = source.split(".")

        match alias:
            case "EL6021":
                severity = self.severityEL6021(source, data, current)
            case "EL3124":
                severity = self.severityEL3124(source, data, current)
            case _:
                pass
        
        for stroke, s in enumerate(severity):
            if s & SEVERITY_CRITICAL == SEVERITY_CRITICAL:
                severity[stroke] = SEVERITY_CRITICAL

        return severity
    
    #
    # config section
    #
    
    def configEL2502(self, pos, slave):

        rc = super().configEL2502(pos, slave)

        if rc:

            if self.isSlot("bus", (6, pos)):
                pass

        EcatLogger.debug(f"    -- done")

        return rc    
    
    def configEL2008(self, pos, slave):

        rc = super().configEL2008(pos, slave)

        if rc:
            if self.isSlot("bus", (3, pos)):
                pass

            elif self.isSlot("bus", (4, pos)):
                pass

        EcatLogger.debug(f"    -- done")

        return rc    

    def configEL6021(self, pos, slave):

        rc = super().configEL6021(pos, slave)

        if rc:

            if self.isSlot("bus", (1, pos)):                
                addr = [0x0B,0x0C,0x0D,0xA1]
                
                self._kellerModbusController[pos] = KellerModbusController(pos, slave, self.ProcessLock, addr)
                self.SeverityController.register("EL6021.1")
                
                EcatLogger.debug(f"    ** init KellerModbusController @ {addr}")

            elif self.isSlot("bus", (8, pos)):
                addr = [0x13]
                self._sht01ModbusController[pos] = Sth01ModbusController(pos, slave, self.ProcessLock, addr)
                EcatLogger.debug(f"    ** init Wt901cModbusController @ {addr}")

        EcatLogger.debug(f"    -- done")

        return rc
    
    def configEL3124(self, pos, slave):

        rc = super().configEL3124(pos, slave)

        if rc:

            if self.isSlot("bus", (2, pos)):
                
                # filter setting FIR 50Hz
                slave.sdo_write(0x8000, 0x15, bytes(ctypes.c_uint16(0)))
                # enable filter (all channels)
                slave.sdo_write(0x8000, 0x06, bytes(ctypes.c_bool(1)))

                self.SeverityController.register("EL3124.2")

        EcatLogger.debug(f"    -- done")

        return rc  
    
    def configEL3314(self, pos, slave):

        rc = super().configEL3314(pos, slave)

        if rc:
            
            # Types; 0: K, 4: T
            if self.isSlot("bus", (7, pos)):

                t = [0, 0, 0, 0]
                for i, a in enumerate([0x8000, 0x8010, 0x8020, 0x8030]):
                    slave.sdo_write(a, 0x19, bytes(ctypes.c_uint16(t[i])))

        EcatLogger.debug(f"    -- done")
        
        return rc
    
    def configEM3702(self, pos, slave):

        rc = super().configEM3702(pos, slave)

        if rc:

            if self.isSlot("bus", (9, pos)):

                limit = { 'low': 5000, 'high': 10000 }

                for a in [0x8000, 0x8010]:
                    # set limit 1
                    slave.sdo_write(a, 0x13, bytes(ctypes.c_int16(limit['low'])))
                    # enable limit 1
                    slave.sdo_write(a, 0x07, bytes(ctypes.c_bool(1)))

                    # set limit 2
                    slave.sdo_write(a, 0x14, bytes(ctypes.c_int16(limit['high'])))
                    # enable limit 2
                    slave.sdo_write(a, 0x08, bytes(ctypes.c_bool(1)))

                self._beckhoffPressureController[pos] = BeckhoffPressureController(pos, slave, self.ProcessLock)
                EcatLogger.debug(f"    ** init BeckhoffPressureController")

        EcatLogger.debug(f"    -- done")  

        return rc    
        