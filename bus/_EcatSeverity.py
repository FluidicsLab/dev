
import json
import numpy as np
from multiprocessing import shared_memory
from functools import reduce
from threading import Lock

from _EcatObject import EcatLogger

import logging, sys

SeverityLogger = logging.getLogger(__name__)
SeverityLogger.setLevel(logging.DEBUG)
SeverityLogger.name = "__SeverityLogger__"

class SeverityLoggerFormatter(logging.Formatter):
    _baseformat = "%(asctime)s - %(name)s - %(levelname)s %(message)s"
    _colorreset = "\x1b[0m"
    _formats = {
            logging.DEBUG    : f"\x1b[02m{_baseformat}{_colorreset}",
            logging.INFO     : f"\x1b[39m{_baseformat}{_colorreset}",
            logging.WARNING  : f"\x1b[33m{_baseformat}{_colorreset}",
            logging.ERROR    : f"\x1b[31;1m{_baseformat}{_colorreset}",
            logging.CRITICAL : f"\x1b[41m{_baseformat}{_colorreset}",
    } if sys.stderr.isatty() else {}
    _formatters = {
        level : logging.Formatter(fmt)
        for level, fmt in _formats.items()
    }
    _default_formatter = logging.Formatter(_baseformat)
    def format(self, record):
        formatter = self._formatters.get(record.levelno, self._default_formatter)
        return formatter.format(record)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(SeverityLoggerFormatter())
SeverityLogger.addHandler(ch)

# high 4 bits
SEVERITY_INFORMATION =          int('10000000', 2) #8
SEVERITY_WARNING =              int('01000000', 2) #4
SEVERITY_ERROR =                int('00100000', 2) #2
SEVERITY_CRITICAL =             int('00010000', 2) #1
SEVERITY_VERBOSE =              int('00000000', 2) #0

# low 4 bits
SEVERITY_REASON_TEMPERATURE =   int('00001100', 2) #12
SEVERITY_REASON_LOCK =          int('00001010', 2) #10
SEVERITY_REASON_PRESSURE =      int('00001000', 2) #8
SEVERITY_REASON_TIME =          int('00000110', 2) #6
SEVERITY_REASON_DISTANCE =      int('00000100', 2) #4
SEVERITY_REASON_SYSTEM =        int('00000010', 2) #2

SEVERITY_IGNORE =               int('00000001', 2) #1

class EcatSeverityController:

    @staticmethod
    def create_(name, size):
        rc = 0
        try:
            shm = shared_memory.SharedMemory(name=name, create=True, size=size)
            rc = 1
        except FileExistsError:
            shm = shared_memory.SharedMemory(name=name, create=False, size=size)
            rc = 2
        except Exception:
            shm = None
            rc = 3
        return shm, rc

    @staticmethod
    def release_(ctrl):
        ctrl.close()
        ctrl.unlink() 

    _id = None

    _severity = None

    _len = 0
    _initial = []
    _size = 0

    _parent = None
    
    _items = {}

    def __init__(self, parent, config):
        self._parent = parent
        self._id = self.__class__.__name__
        self._config = config
        self._len = self._config.config.control.channel
        self._size = self._len * 8
        self._initial = self._config.config.control.initial
        
    def register(self, source, callback=None):        
        if source not in self._items.keys():         
            self._items[source] = callback
        if source.split('.')[0] != 'SEVERITY':
            EcatLogger.debug(f"register severity for {source}")    

    def unregister(self, source):
        if source not in self._items.keys():
            return
        if self._items[source] is not None:
            del self._items[source]

    def unregisterAll(self):
        self._items = {}

    def startup(self):

        EcatLogger.debug("start severity controller")
        EcatLogger.debug(f"version {self._config.version} enabled {self._config.enabled} ")
        
        self._severity, _ = EcatSeverityController.create_(f"{self._id}", self._size)

        EcatLogger.debug("- done")

    def release(self):

        EcatLogger.debug("release severity controller")
        self.unregisterAll()
        EcatSeverityController.release_(self._severity)
        EcatLogger.debug("done")        

    def push(self, name, pos, data, config):  
        
        source = f"{name.upper()}.{pos}"
        if source not in self._items.keys():
            return
        
        current = np.ndarray((self._len,), dtype=np.int64, buffer=self._severity.buf)
        severity = self._parent.severityFunc(source, data, current)

        current = severity.copy()

        # subscription
        if self._items[source] is not None:

            if "SEVERITY" == name:
                self._items[source](data, config)
            else:
                for item in list(config.subscription._raw.keys()):

                    for target in list(config.subscription._raw[item].keys()):
                        if name == item and str(pos) == target:  
                            channel = config.subscription._raw[item][target]["channel"]                     
                            value = [SEVERITY_VERBOSE] * len(channel) 
                            for i, s in enumerate(config.subscription._raw[item][target]["severity"]):
                                if s is not None:
                                    value[i] = current[s]
                            self._items[source](value)           
 
    @property
    def Severity(self):
        current = np.ndarray((self._len,), dtype=np.int64, buffer=self._severity.buf)
        return current.copy()
    
    @staticmethod
    def isValid(values: list):
        return np.any([(value & SEVERITY_CRITICAL != SEVERITY_CRITICAL) or 
                       (value & SEVERITY_IGNORE == SEVERITY_IGNORE) for value in values])

    def controlFunc(self, data, config):

        if "value" in list(data.keys()):                        
            
            index = data["index"]
            # shared memory request
            current = np.ndarray((self._len,), dtype=np.int64, buffer=self._severity.buf)                
            
            # shared memory update
            if 1 == data["value"][config.control.reset]:
                current[index] = SEVERITY_VERBOSE

            if 1 == data["value"][config.control.ignore]:
                current[index] |= SEVERITY_IGNORE  
                    
              
class EcatSeverityLimitData:

    def __set__(self, parent, keys):
        for key in keys:
            if isinstance(parent[key], dict):
                parent[key] = EcatSeverityLimitData(**parent[key])
                setattr(self, key, parent[key])
            elif isinstance(parent[key], list):
                parent[key] = [item for item in parent[key]]
                setattr(self, key, parent[key])
            else:
                setattr(self, key, parent[key])        

    _parent = None
    _raw = {}

    def __init__(self, **kwargs):     
        self._raw = kwargs.copy()
        self.__set__(kwargs, list(kwargs.keys()))

    def __str__(self):
        return json.dumps(self.__dict__)
    
    def find(self, path):
        try:
            return reduce(lambda acc,i: acc[i], path.split('.'), self._raw)
        except:
            return None
        
    def reset(self):
        if self._parent is not None:
            self._parent.reset()

    def release(self):
        self._parent = None
    

class EcatSeverityLimit(object):

    _platform = ""
    _filename = "_EcatSeverity.json"
    _lock = Lock()
    
    _data: EcatSeverityLimitData = None
    def _get_data(self):
        self._lock.acquire()
        try:
            if self._data is None:                        
                with open(self._filename, 'r', encoding="utf-8") as f:
                    self._data = EcatSeverityLimitData(**json.load(f))
                self._data._parent = self
        finally:
            self._lock.release()
            return self._data
    Data: EcatSeverityLimitData = property(fget=_get_data)

    def __init__(self, *args, **kwargs):
        super(EcatSeverityLimit, self).__init__()
        if len(args) > 0:
            self._platform = args[0]
            self._filename = f"_EcatSeverity{self._platform}.json"

    def reset(self):
        self._lock.acquire()
        try:
            self._data = None
        finally:
            self._lock.release()

    def release(self):
        self._lock.acquire()
        try:
            if self._data is not None:
                self._data.release()
        finally:
            self._lock.release()
        