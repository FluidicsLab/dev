import json
from functools import reduce
from threading import Lock


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