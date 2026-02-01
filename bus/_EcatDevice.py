
import struct, ctypes

from _EcatObject import EcatObject,EcatLogger
from _EcatConstant import EcatConstant


class EcatDevice(EcatObject):

    _product = ""
    _vendor = 0

    _revision = 0  
    def _get_revision(self):
         return (self._revision >> 16) & 0xFFFF
    Revision = property(fget=_get_revision)
        
    _container = None
    def _set_container(self,value): 
        self._container = value
    def _get_container(self): 
        return self._container
    Container = property(fset=_set_container,fget=_get_container)

    _parent = None
    def _get_parent(self): return self._parent    
    Parent = property(fget=_get_parent)

    _index:int = 0
    def _get_index(self): return self._index
    Index = property(fget=_get_index)
    
    def _get_state(self):         
        return self.Container.state if self.Container is not None else EcatConstant.STATE_NONE    
    def _set_state(self,value): 
        if self.Container is not None:
            self.Container.state = value
            self.Container.write_state()
            i = 0
            while (i < 10):
                current = self.Container.state_check(value, timeout=50_000)
                if (current & value == value) or self.Container.state == EcatConstant.STATE_OP:
                    break
                if i % 10 == 0:
                    EcatLogger.debug(f'slave {self.Index}:{current}!{value} ({i:03d})')

                i += 1
            
    State = property(fget=_get_state,fset=_set_state)
        
    _name = ""
    def _get_name(self): 
        return self._name
    Name = property(fget=_get_name)

    
    def __init__(self,parent, id,name,vendor,rev, container=None, index=0) -> None:
        super().__init__()
        self._parent = parent
        self._product = id
        self._name = name
        self._vendor = vendor
        self._revision = rev
        self._container = container
        self._index = index

    def setup(self):
        pass

    def __str__(self):
        return f"{self.Index}|{self.Name}| (Index:{self._index}, Product:{self._product}, Vendor:{self._vendor}, Rev.:{self.Revision})"

    def reset(self):
        self.reconfig()

    def reconfig(self):
        return self.Container.reconfig()
    
    def recover(self):
        return self.Container.recover()
    
    def debug(self):
        pass
        
    def clear(self):
        self._product = ""
        self._name = ""
        self._vendor = ""
        self._revision = 0   
        self._container = None
        self._parent = None
        self._index = 0

    def Payload(self, *args):
        pass

    def Request(self):
        return None
    
    def Proceed(self, *args):
        rc = dict()
        try:
            pass
        except Exception as ex:
            EcatLogger.error(ex)
        finally:
            return rc