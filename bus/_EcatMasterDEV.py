from _BeckhoffMotionController import AM8111ProfilePosition
from _EcatMaster import EcatMaster, EcatLogger, AM8111MotionController, BeckhoffCouplerController, KellerModbusController
from _EcatSeverity import SEVERITY_VERBOSE, SEVERITY_CRITICAL, SEVERITY_REASON_SYSTEM, \
    SEVERITY_REASON_PRESSURE, SEVERITY_REASON_TEMPERATURE, SEVERITY_REASON_TIME, SEVERITY_REASON_DISTANCE, SeverityLogger
from _EcatStates import EcatStates

import pysoem, time, ctypes


class EcatMasterDEV(EcatMaster):

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

    #
    # severity section
    #

    # pressure and temperature

    def severityEL6021(self, source, data, current, config: dict):
        severity = current.copy()
        value = data['value']['value']
        if value:
            for addr in map(int, list(config.keys())):
                key = "p"
                targets = config[f"{addr}"][key]["channel"]            
                limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                if addr in list(value.keys()):
                    if limit is not None and key in list(value[addr].keys()) and value[addr][key] is not None:
                        critical = value[addr][key] > limit['high'] or value[addr][key] < limit['low']
                        if critical:
                            for target in targets:
                                severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_PRESSURE
                                
                                SeverityLogger.debug(f"6021.{target} {addr} {key} {value[addr][key]}")

                key = "T"
                targets = config[f"{addr}"][key]["channel"]            
                limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                if addr in list(value.keys()):
                    if limit is not None and key in list(value[addr].keys()) and value[addr][key] is not None:
                        critical = value[addr][key] > limit['high'] or value[addr][key] < limit['low']
                        if critical:
                            for target in targets:
                                severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_TEMPERATURE
                                
                                SeverityLogger.debug(f"6021.{target} {addr} {key} {value[addr][key]}")                                

                key = "t"
                if key in list(config[f"{addr}"].keys()):
                    targets = config[f"{addr}"][key]["channel"]            
                    limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                    if addr in list(value.keys()):
                        if limit is not None and key in list(value[addr].keys()) and value[addr][key] is not None:
                            delta = (time.time_ns() - value[addr][key]) / 1e6
                            critical = delta > limit['high'] or delta < limit['low']
                            if critical:
                                for target in targets:
                                    severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_TIME
                                    
                                    SeverityLogger.debug(f"6021.{target} {addr} {key} {value[addr][key]}")  

        return severity

    # position

    def severityEL3124(self, source, data, current, config: dict):
        severity = current.copy()
        if EcatMaster._find_(data, 'value.value') is not None:            
            for addr in map(int, list(config.keys())):
                raw = data['value']['value'][addr]
                key = "d"
                targets = config[f"{addr}"][key]["channel"]            
                limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                if limit is not None:
                    critical = (raw < limit["low"] or raw > limit["high"]) and 1 == (1 if raw is None or (limit["def"] is not None and raw != limit["def"]) else 0)
                    if critical:
                        for target in targets:
                            severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_DISTANCE

                            SeverityLogger.debug(f"3124.{target} {addr} {key} {raw}")                            

        return severity

    def severityEL7201(self, source, data, current, config: dict):
        severity = current.copy()
        if EcatMaster._find_(data, 'value.value') is not None:            
            for addr in map(int, list(config.keys())):
                key = "d"
                targets = config[f"{addr}"][key]["channel"]            
                limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                if limit is not None:
                    raw = data['value']['value']['position']['raw']                                        
                    
                    critical = (raw < limit["low"] or raw > limit["high"]) and \
                        1 == (1 if raw is None or (limit["def"] is not None and raw != limit["def"]) else 0)                    
                    
                    if critical:
                        for target in targets:
                            severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_DISTANCE

                            SeverityLogger.debug(f"7201.{target} {addr} {key} {raw}")

        return severity

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
                case "EL6021":
                    severity = self.severityEL6021(source, data, severity, config._raw[alias][pos])
                case "EL3124":
                    severity = self.severityEL3124(source, data, severity, config._raw[alias][pos])
                case "EL7201":
                    pass #severity = self.severityEL7201(source, data, severity, config._raw[alias][pos])
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

                self._beckhoffCouplerController[pos] = BeckhoffCouplerController(pos, slave, self.ProcessLock)           
                self.SeverityController.register(f"EK1100.{pos}")
                EcatLogger.debug(f"init BeckhoffCouplerController @ {pos}")
            
        EcatLogger.debug(f"done with {rc}")

        return rc    

    # motion controller; AM8111 

    def configEL7201(self, pos, slave):

        rc = super().configEL7201(pos, slave)

        if rc:

            if self.isSlot("drive", (1, pos)):

                self._beckhoffMotionController[pos] = AM8111MotionController(pos, slave, self.ProcessLock)

                self._beckhoffMotionController[pos].initEx({ "name": "EL6021.3", "addr": 0x0B, "key": "p", "low": 0, "high": 700 })
                self._beckhoffMotionController[pos].init()

                self.SeverityController.register(f"EL7201.{pos}", self._beckhoffMotionController[pos].severityFunc)
                self.CallbackController.register(f"EL7201.{pos}", "EL6021.3", self._beckhoffMotionController[pos].callback)

                EcatLogger.debug(f"init EL7201 MotionController @ {pos}")
        
        EcatLogger.debug(f"done with {rc}")
        
        return rc      
    
    # pressure by modbus
     
    def configEL6021(self, pos, slave):

        rc = super().configEL6021(pos, slave)

        if rc:

            slot = 3
            if self.isSlot("drive", (slot, pos)):
                
                addr = [0x0B]

                self._kellerModbusController[pos] = KellerModbusController(pos, slave, self.ProcessLock, addr)                
                self.SeverityController.register(f"EL6021.{slot}")
                
                EcatLogger.debug(f"init KellerModbusController @ {addr}")

        EcatLogger.debug(f"done")

        return rc
    
    # position by laser
    
    def configEL3124(self, pos, slave):

        rc = super().configEL3124(pos, slave)

        if rc:
            slot = 4
            if self.isSlot("drive", (slot, pos)):
                    
                # filter setting FIR 60Hz
                slave.sdo_write(0x8000, 0x15, bytes(ctypes.c_uint16(0)))                    
                # enable filter (all channels)
                slave.sdo_write(0x8000, 0x06, bytes(ctypes.c_bool(1)))

                self.SeverityController.register(f"EL3124.{slot}")

                # presentation
                for i, a in enumerate([0x8000, 0x8010, 0x8020, 0x8030]):
                    slave.sdo_write(a, 0x02, bytes(ctypes.c_uint8(0)))

        EcatLogger.debug(f"done")

        return rc     
    
    def configEL2008(self, pos, slave):

        rc = super().configEL2008(pos, slave)

        if rc:

            slot = 5
            if self.isSlot("drive", (slot, pos)):
                pass

        EcatLogger.debug(f"done")

        return rc
    