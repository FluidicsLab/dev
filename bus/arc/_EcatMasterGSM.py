
import math
from _EcatMaster import EcatMaster, EcatLogger, ctypes, \
    KellerModbusController, BeckhoffMultimeterController, NanotecMotionController, \
    BeckhoffDisplayController, ifmIOLinkController

class EcatMasterGSM(EcatMaster):

    def __init__(self):
        pass

    def configEL6021(self, pos, slave):

        rc = super().configEL6021(pos, slave)

        if rc:

            if self.isSlot("bus", (2, pos)):

                addr = [0x01]
                self._kellerModbusController[pos] = KellerModbusController(pos, slave, self.ProcessLock, addr) 

                EcatLogger.debug(f"    ** init KellerModbusController @ {addr} @ {pos}")

        EcatLogger.debug(f"    -- done")
        return rc
    
    def configEL3681(self, pos, slave):

        rc = super().configEL3681(pos, slave)

        if rc:

            if self.isSlot("bus", (4, pos)):

                self._beckhoffMultimeterController[pos] = BeckhoffMultimeterController(pos, slave, self.ProcessLock)
                self._beckhoffMultimeterController[pos].PdoInput = [0x1A00,0x1A01]
                self._beckhoffMultimeterController[pos].PdoOuput = [0x1600]
                EcatLogger.debug(f"    ** init BeckhoffMultimeterController @ {pos}")

        EcatLogger.debug(f"    -- done")        
        return rc
    
    def configEL7041(self, pos, slave):

        rc = super().configEL7041(pos, slave)

        if rc:

            if self.isSlot("bus", (3, pos)):

                self._nanotecMotionController[pos] = NanotecMotionController(pos, slave, self.ProcessLock)

                # max. current mA
                slave.sdo_write(0x8010, 0x01, bytes(ctypes.c_int16(2800)))
                # red. current mA
                slave.sdo_write(0x8010, 0x02, bytes(ctypes.c_int16(500)))

                # nominal voltage mV, motor supply
                slave.sdo_write(0x8010, 0x03, bytes(ctypes.c_int16(48000)))
                # motor coil resistance 0.01 Ohm, one coil
                slave.sdo_write(0x8010, 0x04, bytes(ctypes.c_int16(110)))
                
                # motor full steps
                slave.sdo_write(0x8010, 0x06, bytes(ctypes.c_int16(1000)))

                # operation mode: 0 automatic, 1 velocity direct
                slave.sdo_write(0x8012, 0x01, bytes(ctypes.c_uint8(0)))

                # invert polarity
                slave.sdo_write(0x8012, 0x09, bytes(ctypes.c_bool(0)))
                
                # velocity min
                slave.sdo_write(0x8020, 0x01, bytes(ctypes.c_int16(200)))
                # velocity max
                slave.sdo_write(0x8020, 0x02, bytes(ctypes.c_int16(4000)))

                # calib. position
                slave.sdo_write(0x8020, 0x08, bytes(ctypes.c_uint32(0)))

                # configure PDO register
                self._nanotecMotionController[pos].PdoInput = [0x1a03, 0x1a06]
                self._nanotecMotionController[pos].PdoOutput = [0x1602, 0x1606]

                EcatLogger.debug(f"    ** init NanotecMotionController @ {pos}")

        EcatLogger.debug(f"    -- done")
        return rc
    

    def configEL6090(self, pos, slave):


        def callback(*args):

            controller = self._beckhoffDisplayController[pos]
        
            if not controller.CallbackEnabled:
                return

            arg = args[0]
            name = arg['name']
            
            if 'value' in list(arg['value'].keys()):
            
                val = arg['value']['value']

                if isinstance(val, dict):

                    keys = list(val.keys())

                    if len(keys) > 0:

                        if name == "EL6021":

                            code = controller.Code.copy()
                            code[1]["value"] = controller.CodeMap['NONE']
                            code[1]["digit"] = 0
                            controller.Code = code.copy()

                            val = val[keys[0]]

                            data = controller.Data.copy()
                            if isinstance(val['p'], float):
                                data[1] =  int((val['p'])*1000)
                            controller.Data = data.copy()

                        elif name == "EL7041":

                            code = controller.Code.copy()
                            code[0]["value"] = controller.CodeMap['NONE']
                            code[0]["digit"] = 0
                            controller.Code = code.copy()

                            val = val['position'] / 12800

                            val = round(val * (math.pow(160,2) * math.pi / 4.0) * (40 * math.pi / 20.0) / 1000., 0)
                            
                            data = controller.Data.copy()
                            if isinstance(val, float):
                                data[0] =  int(val)
                            controller.Data = data.copy()

        
        rc = super().configEL6090(pos, slave)

        if rc:

            if self.isSlot("bus", (5, pos)):

                self._beckhoffDisplayController[pos] = BeckhoffDisplayController(pos, slave, self.ProcessLock)
                self._beckhoffDisplayController[pos].Template = [" %u ml", " %.3i bar"]
                self._beckhoffDisplayController[pos].callback = callback
                self._beckhoffDisplayController[pos].CallbackEnabled = True
                
                for (item, ctrl) in [("EL6021.2","EL6090.5"),("EL7041.3","EL6090.5")]:
                    self.CallbackController.register(ctrl, item, self._beckhoffDisplayController[pos].callback)

                EcatLogger.debug(f"    ** init BeckhoffDisplayController @ {pos}")

        EcatLogger.debug(f"    -- done")
        return rc

    def configEL6224(self, pos, slave):

        rc = super().configEL6224(pos, slave)

        if rc:

            if self.isSlot("bus", (3, pos)):
        
                self._ifmIOLinkController[pos] = ifmIOLinkController(pos, slave, self.ProcessLock)
                self._ifmIOLinkController[pos].PdoInput = [0x1a00]

                EcatLogger.debug(f"    ** init ifmIOLinkController @ {pos}")
                        
        EcatLogger.debug(f"    -- done")
        return rc      
