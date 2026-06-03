import json
from functools import reduce
from threading import Lock
import numpy as np
from _EcatObject import EcatLogger


class PumpProfileController:

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
                
    def register(self, source, callback=None):        
        if source not in self._items.keys():         
            self._items[source] = callback
        EcatLogger.debug(f"register severity for {source}")    

    def unregister(self, source):
        if source not in self._items.keys():
            return
        if self._items[source] is not None:
            del self._items[source]

    def unregisterAll(self):
        self._items = {}

    def startup(self):

        EcatLogger.debug("start pump profile controller")
                
        EcatLogger.debug("done")

    def release(self):

        EcatLogger.debug("release pump profile controller")
        self.unregisterAll()
        
        EcatLogger.debug("done")        

    def push(self, name, pos, data, config):  
        
        source = f"{name.upper()}.{pos}"
        if source not in self._items.keys():
            return

        # subscription
        if self._items[source] is not None:
            self._items[source](data, config)
                    
    def controlFunc(self, data, config):

        if "value" in list(data.keys()):            
            pass


class PumpProfileData:

    def __set__(self, parent, keys):
        for key in keys:
            if isinstance(parent[key], dict):
                parent[key] = PumpProfileData(**parent[key])
                setattr(self, key, parent[key])
            elif isinstance(parent[key], list):
                parent[key] = [item for item in parent[key]]
                setattr(self, key, parent[key])
            else:
                setattr(self, key, parent[key])        

    class ComplexJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, list):
                return obj.tolist()
            return json.JSONEncoder.default(self, obj) 

    _parent = None
    _raw = {}

    def __init__(self, **kwargs):     
        self._raw = kwargs.copy()
        self.__set__(kwargs, list(kwargs.keys()))

    def __str__(self):
        return json.dumps(self.__dict__, cls=self.ComplexJSONEncoder)
    
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


class PumpProfile(object):

    _profile = ""
    _path = ""
    _filename = "default.json"
    _lock = Lock()
    
    _data: PumpProfileData = None
    def _get_data(self):
        self._lock.acquire()
        try:
            if self._data is None:                        
                with open(self._filename, 'r', encoding="utf-8") as f:
                    self._data = PumpProfileData(**json.load(f))
                self._data._parent = self
        finally:
            self._lock.release()
            return self._data
    Data: PumpProfileData = property(fget=_get_data)

    def __init__(self, *args, **kwargs):
        super(PumpProfile, self).__init__()
        if len(args) > 0:
            self._path = args[0]
            self._profile = args[1]
            self._filename = os.path.join(self._path, f"{self._profile}.json")

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


if __name__ == "__main__":

    import os
    os.system("cls")

    pp = PumpProfile("profile", "purge")

    print(pp.Data._raw)