from _AnalogController import BeckhoffAnalogController
from _EcatMaster import EcatMaster, EcatLogger, AM81111MotionController, BeckhoffCouplerController, EsiModbusController, BeckhoffMultimeterController
from _EcatSeverity import SEVERITY_VERBOSE, SEVERITY_CRITICAL, SEVERITY_REASON_SYSTEM, \
    SEVERITY_REASON_PRESSURE, SEVERITY_REASON_TEMPERATURE, SEVERITY_REASON_TIME, SEVERITY_REASON_DISTANCE, SeverityLogger
from _EcatStates import EcatStates

import pysoem, time, ctypes

from _MultimeterController import MultimeterController


class EcatMasterESI(EcatMaster):

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
    
    def severityEL3751(self, source, data, current, config: dict):
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
                                
                                SeverityLogger.debug(f"3751.{target} {addr} {key} {value[addr][key]}")

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
                case "EL6021":
                    severity = self.severityEL6021(source, data, severity, config._raw[alias][pos])                
                case "EL3751":
                    severity = self.severityEL3751(source, data, severity, config._raw[alias][pos])                
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
   
    # pressure by modbus
     
    def configEL6021(self, pos, slave):

        rc = super().configEL6021(pos, slave)

        if rc:

            slots = [1]
            for slot in slots:
                if self.isSlot("drive", (slot, pos)):
                    
                    addr = [
                        (0x11, "743513"),
                        (0x12, "743522")
                            ]

                    self._esiModbusController[pos] = EsiModbusController(pos, slave, self.ProcessLock, addr)
                    self._esiModbusController[pos].initConfig()

                    self.SeverityController.register(f"EL6021.{slot}")
                    
                    EcatLogger.debug(f"init EsiModbusController @ {slot} with {addr}")

        EcatLogger.debug(f"done")

        return rc
    
    # analog measurement

    def configEL3751(self, pos, slave):

        rc = super().configEL3751(pos, slave)
        if rc:
            slots = [2,3]
            for slot in slots:

                if self.isSlot("drive", (slot, pos)):

                    self._beckhoffMultimeterController[pos] = BeckhoffMultimeterController(pos, slave, self.ProcessLock)
                    self._beckhoffMultimeterController[pos].initConfig()

                    self.SeverityController.register(f"EL3751.{slot}")

                    EcatLogger.debug(f"init BeckhoffMultimeterController @ {slot}")
        
        EcatLogger.debug(f"done")

        return rc

    def configSeverity(self):
        if self.SeverityLimit.enabled == 1:
            config = self.SeverityLimit.config
            # severity channel
            for target in range(config.control.channel):
                self.SeverityController.register(f"{config.control.item}.{target}", self.SeverityController.controlFunc)
            # severity limit data reload
            self.SeverityController.register(f"{config.control.item}.99")    
    