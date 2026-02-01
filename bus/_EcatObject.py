import uuid
import pysoem

from collections import namedtuple

import logging

logging.basicConfig(
    level=logging.ERROR,
    #format='%(levelname)-8s %(asctime)s %(threadName)-15s %(message)s'
    format='%(asctime)s %(message)s'
    #format='%(levelname)-8s %(asctime)s %(message)s'
    )

EcatLogger = logging.getLogger(__name__)
EcatLogger.setLevel(logging.DEBUG)
EcatLogger.name = "__EcatLogger__"

def loggingFilter(record: logging.Filter):
    if isinstance(record.msg, str):
        return True
    return True

EcatLogger.addFilter(loggingFilter)


EcatSlaveSet = namedtuple('EcatSlaveSet', 'name alias vendor_id product_code consumption power valid priority')

class EcatLayoutError(Exception):
    def __init__(self, message):
        super(EcatLayoutError, self).__init__(message)
        self.message = message


class EcatError(Exception):

    @staticmethod
    def error(obj, src='n.n'):
        if isinstance(obj, pysoem.pysoem.ConfigMapError):
            EcatLogger.debug(f"    {obj.__class__}")
            for e in obj.error_list:
                EcatError.error(e,src)
        elif isinstance(obj, pysoem.pysoem.MailboxError):
            EcatLogger.debug(f"    {src}:{obj.__class__} {obj.slave_pos} {obj.error_code} {obj.desc}")
        elif isinstance(obj, pysoem.pysoem.PacketError):
            EcatLogger.debug(f"    {src}:{obj.__class__} {obj.slave_pos} {obj.error_code} {obj.desc}")
        elif isinstance(obj, pysoem.pysoem.SdoError):
            EcatLogger.debug(f"    {src}:{obj.__class__} {obj.slave_pos} {hex(obj.abort_code)} {obj.desc}")
        elif isinstance(obj, pysoem.pysoem.WkcError):
            EcatLogger.debug(f"    {src}:{obj.__class__} {obj.wkc} {obj.message}")
        elif isinstance(obj, EcatLayoutError):
            EcatLogger.debug(f"    {src}:{obj.__class__} {obj.message}")
        else:
            EcatLogger.debug(f"    {src}:{obj.__class__} {obj.__doc__}")


class EcatObject(object):

    _parent = None

    _uid = None
    def _get_uid(self): 
        return self._uid
    Uid = property(fget=_get_uid)
    
    def __init__(self, parent: object=None) -> None:
        super().__init__()
        self._parent = parent
        self._uid = str(uuid.uuid4())

class EcatObjectTypes:

    items = {
        
        "EK1100":"Coupler",

        "EL1008":"Digital In, 8-Channel, 24V, 3ms",
        "EL1124":"Digital In, 4-Channel, 5V, 10µs",

        "EL2008":"Digital Out, 8-Channel, 24V, 0.5A",        
        "EL2124":"Digital Out, 4-Channel, 5V, CMOS",

        "EL2502":"PWM Out, 2-Channel",
        "EL2596":"LED Strobe Control, 1-Channel",
        
        "EL3124":"Analog In, 4-Channel, 4..20mA",
        "EL3164":"Analog In, 4-Channel, 0..10V",

        "EL3202":"Analog In, 2-Channel, Pt100 (RTD)",        
        "EL3314":"Analog In, 4-Channel, thermocouples",

        "EL4104":"Analog Out, 4-Channel, 0..10V",

        "EL6021":"RS422/RS485, 1-Channel",

        "EL6080":"128kB NOVRAM, 1-Channel",

        "EL6614":"Ethernet-Switchport, 4-Channel",

        "ED1F CoE Drive":"Servo Drive",

    }