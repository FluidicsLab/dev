
from _EcatMaster import EcatMaster, EcatLogger, KellerModbusController, BeckhoffHeatingController, BeckhoffAnalogController, \
    BeckhoffPressureController, Wt901cModbusController, BeckhoffCouplerController, ctypes
from _EcatSeverity import SEVERITY_CRITICAL, SEVERITY_VERBOSE, \
    SEVERITY_REASON_DISTANCE, SEVERITY_REASON_PRESSURE, SEVERITY_REASON_TEMPERATURE, SEVERITY_REASON_TIME, \
        SEVERITY_REASON_SYSTEM, SEVERITY_REASON_LOCK, \
        SeverityLogger

import numpy as np
import time

from _ModbusController import Sth01ModbusController


class EcatMasterBusONE(EcatMaster):

    def __init__(self):
        pass

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
                                
                                SeverityLogger.debug(f"    6021.{target} {addr} {key} {value[addr][key]}")

                key = "T"
                targets = config[f"{addr}"][key]["channel"]            
                limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                if addr in list(value.keys()):
                    if limit is not None and key in list(value[addr].keys()) and value[addr][key] is not None:
                        critical = value[addr][key] > limit['high'] or value[addr][key] < limit['low']
                        if critical:
                            for target in targets:
                                severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_TEMPERATURE
                                
                                SeverityLogger.debug(f"    6021.{target} {addr} {key} {value[addr][key]}")                                

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
                                    
                                    SeverityLogger.debug(f"    6021.{target} {addr} {key} {value[addr][key]}")  

        return severity

    # position

    def severityEL3124(self, source, data, current, config: dict):
        severity = current.copy()
        value = data['value']['value']
        if value:
            for addr in map(int, list(config.keys())):
                key = "d"
                targets = config[f"{addr}"][key]["channel"]            
                limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                if limit is not None:
                    critical = (value[addr] < limit["low"] or value[addr] > limit["high"]) and 1 == (1 if value[addr] is None or \
                                                                                                     (limit["def"] is not None and value[addr] != limit["def"]) else 0)
                    if critical:
                        for target in targets:
                            severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_DISTANCE

                            SeverityLogger.debug(f"    3124.{target} {addr} {key} {value[addr]}")                            

        return severity
    
    # temperature
    
    def severityEL3314(self, source, data, current, config: dict):
        severity = current.copy()
        value = data['value']['value']
        if value:
            for addr in map(int, list(config.keys())):
                key = "T"
                targets = config[f"{addr}"][key]["channel"]            
                limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                if limit is not None:
                    critical = (value[addr] < limit["low"] or value[addr] > limit["high"]) and 1 == (1 if value[addr] is None or \
                                                                                                     (limit["def"] is not None and value[addr] != limit["def"]) else 0)
                    if critical:
                        for target in targets:
                            severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_TEMPERATURE

                            SeverityLogger.debug(f"    3314.{target} {addr} {key} {value[addr]}")

        return severity
    
    # pressure; supply
    
    def severityEL3164(self, source, data, current, config: dict):
        severity = current.copy()
        value = data['value']['value']
        if value:
            for addr in map(int, list(config.keys())):
                key = "p"
                targets = config[f"{addr}"][key]["channel"]            
                limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                if limit is not None:
                    critical = (value[addr] < limit["low"] or value[addr] > limit["high"])
                    if critical:
                        for target in targets:
                            severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_SYSTEM

                            SeverityLogger.debug(f"    3164.{target} {addr} {key} {value[addr]}")

        return severity 

    # state; binary   
    
    def severityEL1809(self, source, data, current, config: dict):
        severity = current.copy()
        value = data['value']['value']
        if value:
            for addr in map(int, list(config.keys())):
                key = "b"
                targets = config[f"{addr}"][key]["channel"]            
                limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                if limit is not None:
                    critical = (value[addr] < limit["low"] or value[addr] > limit["high"])
                    if critical:
                        for target in targets:
                            severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_LOCK

                            SeverityLogger.debug(f"    1809.{target} {addr} {key} {value[addr]}")

        return severity
    
    def severityEL1008(self, source, data, current, config: dict):
        severity = current.copy()
        value = data['value']['value']
        if value:
            for addr in map(int, list(config.keys())):
                key = "b"
                targets = config[f"{addr}"][key]["channel"]            
                limit = self.SeverityLimit.find(f"{source}.{addr}.{key}")
                if limit is not None:
                    critical = (value[addr] < limit["low"] or value[addr] > limit["high"])
                    if critical:
                        for target in targets:
                            severity[target] = severity[target] | SEVERITY_CRITICAL | SEVERITY_REASON_LOCK

                            SeverityLogger.debug(f"    1008.{target} {addr} {key} {value[addr]}")

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

                            SeverityLogger.debug(f"    1100.{target} {addr} {key} {value[addr][key]}")                               

        return severity    
    
    # severity test distributor

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
                case "EL3314":
                    severity = self.severityEL3314(source, data, severity, config._raw[alias][pos])
                case "EL3164":
                    severity = self.severityEL3164(source, data, severity, config._raw[alias][pos])
                case "EL1809":
                    severity = self.severityEL1809(source, data, severity, config._raw[alias][pos])
                case "EL1008":
                    severity = self.severityEL1008(source, data, severity, config._raw[alias][pos])
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
            if self.isSlot("bus", (0, pos)):         
                self._beckhoffCouplerController[pos] = BeckhoffCouplerController(pos, slave, self.ProcessLock)           
                self.SeverityController.register("EK1100.0")
                EcatLogger.debug(f"    ** init BeckhoffCouplerController @ {pos}")

        EcatLogger.debug(f"    -- done")

        return rc  

    # modbus; pressure and health
     
    def configEL6021(self, pos, slave):

        rc = super().configEL6021(pos, slave)

        if rc:

            if self.isSlot("bus", (1, pos)):   
                
                addr = [0x0B,0x0C]
                                
                self._kellerModbusController[pos] = KellerModbusController(pos, slave, self.ProcessLock, addr)
                self.SeverityController.register("EL6021.1")
                
                EcatLogger.debug(f"    ** init KellerModbusController @ {addr}")
            
            if self.isSlot("bus", (8, pos)):   

                addr = [0x13]
                
                self._sht01ModbusController[pos] = Sth01ModbusController(pos, slave, self.ProcessLock, addr)
                                
                EcatLogger.debug(f"    ** init Sth01ModbusController @ {addr}")

            if self.isSlot("bus", (9, pos)):   

                addr = [0x01]
                
                self._wt901cModbusController[pos] = Wt901cModbusController(pos, slave, self.ProcessLock, addr)
                                
                EcatLogger.debug(f"    ** init Wt901cModbusController @ {addr}")


        EcatLogger.debug(f"    -- done")

        return rc
    
    # position
    
    def configEL3124(self, pos, slave):

        rc = super().configEL3124(pos, slave)

        if rc:

            for slot in [2]:

                if self.isSlot("bus", (slot, pos)):
                    
                    # filter setting FIR 60Hz
                    slave.sdo_write(0x8000, 0x15, bytes(ctypes.c_uint16(0)))                    
                    # enable filter (all channels)
                    slave.sdo_write(0x8000, 0x06, bytes(ctypes.c_bool(1)))

                    self.SeverityController.register(f"EL3124.{slot}")

                    # presentation
                    for i, a in enumerate([0x8000, 0x8010, 0x8020, 0x8030]):
                        slave.sdo_write(a, 0x02, bytes(ctypes.c_uint8(0)))

        EcatLogger.debug(f"    -- done")

        return rc  
    
    # example: pressure; supply
    
    def configEL3164(self, pos, slave):

        rc = super().configEL3164(pos, slave)

        if rc:

            slot = 5

            if self.isSlot("bus", (slot, pos)):

                # filter setting 
                slave.sdo_write(0x8000, 0x15, bytes(ctypes.c_uint16(2)))
                # enable filter (all channels)
                slave.sdo_write(0x8000, 0x06, bytes(ctypes.c_bool(1)))
            
                # presentation unsigned 16bit 0..65535
                for i, a in enumerate([0x8000, 0x8010, 0x8020, 0x8030]):
                    slave.sdo_write(a, 0x02, bytes(ctypes.c_uint8(1)))

                self.SeverityController.register(f"EL3164.{slot}")

        EcatLogger.debug(f"    -- done")

        return rc  
    
    # analog out 0..10V
    
    def configEL4002(self, pos, slave):

        rc = super().configEL4002(pos, slave)

        if rc:

            slot = 10

            if self.isSlot("bus", (slot, pos)):
            
                # presentation unsigned 12bit 0..
                for i, a in enumerate([0x8000, 0x8010]):
                    slave.sdo_write(a, 0x02, bytes(ctypes.c_uint8(1)))

                self._beckhoffAnalogController[pos] = BeckhoffAnalogController(pos, slave, self.ProcessLock, 2)

                # self.SeverityController.register(f"EL4001.{pos}", self._beckhoffAnalogController[pos].severityFunc)

        EcatLogger.debug(f"    -- done")

        return rc  
    
    def configEL4104(self, pos, slave):

        rc = super().configEL4104(pos, slave)

        if rc:

            slot = 10

            if self.isSlot("bus", (slot, pos)):
            
                # presentation unsigned 16bit 0..
                for i, a in enumerate([0x8000, 0x8010, 0x8020, 0x8030]):
                    slave.sdo_write(a, 0x02, bytes(ctypes.c_uint8(1)))

                self._beckhoffAnalogController[pos] = BeckhoffAnalogController(pos, slave, self.ProcessLock, 4)

                # self.SeverityController.register(f"EL4001.{pos}", self._beckhoffAnalogController[pos].severityFunc)

        EcatLogger.debug(f"    -- done")

        return rc  
    
    # pressure by Beckhoff
    
    def configEM3702(self, pos, slave):

        rc = super().configEM3702(pos, slave)
        if rc:

            slot = 11

            if self.isSlot("bus", (slot, pos)):
                
                limit = { 'low': 4000, 'high': 7000 }

                for a in [0x8000, 0x8010]:

                    # set limit 1
                    slave.sdo_write(a, 0x13, bytes(ctypes.c_int16(limit['low'])))
                    # enable limit 1
                    slave.sdo_write(a, 0x07, bytes(ctypes.c_bool(1)))
                    # set limit 2
                    slave.sdo_write(a, 0x14, bytes(ctypes.c_int16(limit['high'])))
                    # enable limit 2
                    slave.sdo_write(a, 0x08, bytes(ctypes.c_bool(1)))

                    # filter setting IIR
                    slave.sdo_write(0x8000, 0x15, bytes(ctypes.c_uint16(2)))
                    # enable filter (all channels)
                    slave.sdo_write(0x8000, 0x06, bytes(ctypes.c_bool(0)))

                self._beckhoffPressureController[pos] = BeckhoffPressureController(pos, slave, self.ProcessLock)
                EcatLogger.debug(f"    ** init BeckhoffPressureController")

                self.SeverityController.register(f"EM3702.{slot}")

        EcatLogger.debug(f"    -- done")

        return rc  
    
    # binary out; valve, lighting, fan
    
    def configEL2008(self, pos, slave):

        rc = super().configEL2809(pos, slave)
        if rc:

            if self.isSlot("bus", (3, pos)):
                pass

            if self.isSlot("bus", (4, pos)):
                pass
                
        EcatLogger.debug(f"    -- done")

        return rc   
    
    # heating
    
    def configEL2502(self, pos, slave):

        rc = super().configEL2502(pos, slave)
        if rc:
            for slot in [6]:
                if self.isSlot("bus", (slot, pos)):                      
                    self._beckhoffHeatingController[pos] = BeckhoffHeatingController(pos, slave, self.ProcessLock, 2)
                    self.SeverityController.register(f"EL2502.{pos}", self._beckhoffHeatingController[pos].severityFunc)

        EcatLogger.debug(f"    -- done")

        return rc    
    
    # temperature
    
    def configEL3314(self, pos, slave):

        rc = super().configEL3314(pos, slave)
        if rc:            
            # Types; 0: K, 4: T
            for slot in [7]:
                if self.isSlot("bus", (slot, pos)):
                    t = [0, 0, 0, 0]
                    for i, a in enumerate([0x8000, 0x8010, 0x8020, 0x8030]):
                        slave.sdo_write(a, 0x19, bytes(ctypes.c_uint16(t[i])))

                    self.SeverityController.register(f"EL3314.{slot}")

        EcatLogger.debug(f"    -- done")
        
        return rc    
    
    #
    # config section (virtual)
    #
    
    def configSeverity(self):
        if self.SeverityLimit.enabled == 1:
            config = self.SeverityLimit.config
            # severity channel
            for target in range(config.control.channel):
                self.SeverityController.register(f"{config.control.item}.{target}", self.SeverityController.controlFunc)
            # severity limit data reload
            self.SeverityController.register(f"{config.control.item}.99")

    