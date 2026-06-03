import uuid
import pysoem

from collections import namedtuple

import logging, sys

EcatLogger = logging.getLogger(__name__)
EcatLogger.setLevel(logging.DEBUG)
EcatLogger.name = "__EcatLogger__"

class EcatLoggerFormatter(logging.Formatter):
    
    _format = "%(asctime)s - %(name)s - %(levelname)s %(message)s"
    
    grey        = "\x1b[38;20m"
    yellow      = "\x1b[33;20m"
    red         = "\x1b[31;20m"
    bold_red    = "\x1b[31;1m"

    _reset = "\x1b[0m"
    
    _formats = {
            logging.DEBUG    : f"\x1b[02m{_format}{_reset}",
            logging.INFO     : f"\x1b[39m{_format}{_reset}",
            logging.WARNING  : f"\x1b[33m{_format}{_reset}",
            logging.ERROR    : f"\x1b[31;1m{_format}{_reset}",
            logging.CRITICAL : f"\x1b[41m{_format}{_reset}",
    } if sys.stderr.isatty() else {}
    _formatters = {
        level : logging.Formatter(fmt)
        for level, fmt in _formats.items()
    }
    _default_formatter = logging.Formatter(_format)
    def format(self, record):
        formatter = self._formatters.get(record.levelno, self._default_formatter)
        return formatter.format(record)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(EcatLoggerFormatter())
EcatLogger.addHandler(ch)


EcatSlaveSet = namedtuple('EcatSlaveSet', 'name alias vendor_id product_code consumption power valid priority watchdog')

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
        
    }