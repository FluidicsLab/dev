import numpy as np
import pysoem
import ctypes
import struct
import datetime 

from threading import Lock,Event

from _EcatObject import EcatLogger

ULONG_MAX = 4294967295

class DisplayController(object):

    _debug = False    
    _lock = Lock()
    _exit = Event()

    def _get_enabled(self):
        return not self._exit.is_set()
    Enabled = property(fget=_get_enabled)

    _index = 0

    _device = None
    def _get_device(self): return self._device
    Device = property(fget=_get_device)

    def _get_id(self):
        return f"{self._device.name}.{self._index}"
    Id = property(fget=_get_id)

    _deviceLock: Lock = None
    def _get_deviceLock(self): return self._deviceLock
    DeviceLock: Lock = property(fget=_get_deviceLock)

    _data = None
    def _get_data(self): return self._data
    Data = property(fget=_get_data)    

    _display = None
    def _get_display(self): 
        return self._display
    Display = property(fget=_get_display)    

    def __init__(self, index, device, lock, debug=False) -> None:   
        super().__init__()   
        self._index = index  
        self._device = device
        self._deviceLock = lock
        self._debug = debug
        
    def release(self):
        self._exit.set()

    def input(self):
        return None

    def output(self, data):        
        pass

    def write(self, data):   
        pass

    def init(self):
        return False
    
    def compute(self):
        pass
            
    def run(self):
        return False
    
    
class BeckhoffDisplayController(DisplayController):

    CTRL = ["EL6090.5"]

    '''
    2 lines;
    one value for every line, 
    one special character for every line
    '''

    ButtonMap = {
        "UP":       0x03,
        "DOWN":     0x04,
        "LEFT":     0x05,
        "RIGHT":    0x06,
        "ENTER":    0x07
    }

    CodeMap = {
        "NONE":         [ 0, 0, 0, 0, 0, 0, 0, 0],

        "DEGREE":       [ 7, 5, 7, 0, 0, 0, 0, 0],  # °
        "MU":           [ 0,17,17,19,29,10,10, 0],  # µ
        "PLUSMINUS":    [ 0, 4,14, 4, 0,14, 0, 0],  # +/-

        "MOVING":       [ 0, 4,14, 4, 0,14, 0, 0],

        "LEFT":         [ 0, 4,12,31,12, 4, 0, 0],       
        "RIGHT":        [ 0, 4, 6,31, 6, 4, 0, 0],         
        "UP":           [ 4,15,31, 4, 4, 4, 4, 0],        
        "DOWN":         [ 4, 4, 4, 4,31,15, 4, 0],        
        "ENTER":        [ 1, 1, 5,14,31,13, 4, 0],       
    }

    _diagnostic = { 
        "time": 0,
        "error": { "source": None, "class": None, "doc": None, "time": 0 }
    }

    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)

    def _get_data(self): 
        if self._data is None:
            self._data = [0, 0]
        return self._data
    def _set_data(self, value):
        if len(value) == 2 and all(isinstance(v,int) for v in value):
            self._data = value
    Data = property(fget=_get_data, fset=_set_data)    

    _template = None
    def _get_template(self):
        if self._template is None:
            self._template = [" %.2i", " %.2i"]
        return self._template
    def _set_template(self, value):
        if len(value) == 2 and all(isinstance(v,str) for v in value):
            self._template = value.copy()
    Template = property(fget=_get_template, fset=_set_template)    
    
    _code = None
    def _get_code(self): 
        if self._code is None:
            self._code = [
                { "value": [0,0,0,0,0,0,0,0], "digit": -1 },
                { "value": [0,0,0,0,0,0,0,0], "digit": -1 }
                ]
        return self._code
    def _set_code(self, value):
        self._code = value
    Code = property(fget=_get_code, fset=_set_code)    

    _operatingTime = 0
    def _get_operatingTime(self):
        return self._operatingTime
    OperatingTime = property(fget=_get_operatingTime)
    
    _button = [False] * 5
    def _get_button(self):
        return self._button
    Button = property(fget=_get_button)

    _initialized = False          
    def init(self):

        rc = False
        try:
            rc = self.update()
            if (len(self.Data) == 2):
                self.write(struct.pack(f'2h', *(self.Data)))            
            rc = rc and True

            # backlight on 0xff, off 0xfe
            a, o = 0x8000, 0x11
            self.Device.sdo_write(a, o, bytes(ctypes.c_uint8(0xff)))

            self._diagnostic['time'] = datetime.datetime.now()

        except Exception as ex:
            self._diagnostic["error"] = { "source": "BeckhofDisplayController.init", "class": str(ex.__class__), "doc": str(ex.__doc__), "time": datetime.datetime.now() }
            EcatLogger.debug(f"{self._diagnostic}")
            
        finally:
            return rc
        
    def update(self):

        rc = False
        try:

            # apply code to special register
            a = 0x8008
            for i,o in enumerate([0x1C,0x1D]):
                if self.Code[i]["digit"] != -1:
                    self.Device.sdo_write(a, o, bytes(bytearray(self.Code[i]["value"])))

            a = 0x8008
            for i,o in enumerate([0x11,0x12]):
                s = bytearray(str.encode(self.Template[i]))
                if self.Code[i]["digit"] != -1:
                    # load code from register
                    s[self.Code[i]["digit"]] = i +1
                s = bytes(s)
                self.Device.sdo_write(a, o, s)

            rc = True
            
        except Exception as ex:
            self._diagnostic["error"] = { "source": "BeckhofDisplayController.update", "class": str(ex.__class__), "doc": str(ex.__doc__), "time": datetime.datetime.now() }
            EcatLogger.debug(f"{self._diagnostic}")
            
        finally:
            return rc
        
    _archive = None        
    def archive(self):
        self._archive = {
            "data": self.Data.copy(),
            "code": self.Code.copy(),
            "button": self.Button.copy()
        }
        
    def compute(self):
                    
        if not self._exit.is_set():
            
            try:

                self.archive()

                changed = False
                
                keys = list(self.ButtonMap.keys())
                values = list(self.ButtonMap.values())
                button = [0] * len(values)
                a = 0x6000
                for i,o in enumerate(values):
                    button[i] = ctypes.c_bool.from_buffer_copy(self.Device.sdo_read(a,o)).value

                code = self.Code.copy()

                if any(button):

                    keys = list(self.ButtonMap.keys())
                    i = np.argwhere(button)[0][0]
                    
                    code[1]["value"] = self.CodeMap[keys[i]]
                    code[1]["digit"] = 0
                            
                else:

                    code[1]["value"] = self.CodeMap['NONE']
                    code[1]["digit"] = -1

                self._button = button.copy()                
                self.Code = code.copy()        
                
                self.update()

                a, o = 0xf600, 0x11               
                self._operatingTime = ctypes.c_uint32.from_buffer_copy(self.Device.sdo_read(a,o)).value

                if (len(self.Data) == 2):
                    self.write(struct.pack(f'2h', *(self.Data)))
                                
            except Exception as ex:
                self._diagnostic["error"] = { "source": "BeckhofDisplayController.compute", "class": str(ex.__class__), "doc": str(ex.__doc__), "time": self._diagnostic["time"] - datetime.datetime.now() }
                EcatLogger.debug(f"{self._diagnostic}")

    def run(self):
        
        if not self.Enabled:
            return None

        if (self.Device.state & pysoem.OP_STATE) != self.Device.state:
            return None

        self._lock.acquire()
        try:            
            if not self._initialized:
                self._initialized = self.init()
            
            if self._initialized:
                self.compute()

        except Exception as ex:
            self._diagnostic["error"] = { "source": "BeckhofDisplayController.run", "class": str(ex.__class__), "doc": str(ex.__doc__), "time": self._diagnostic["time"] - datetime.datetime.now() }
            EcatLogger.debug(f"{self._diagnostic}")

        finally:
            self._lock.release()

        return {
            "data": self.Data,
            "button": self.Button,
            "moving": self.Moving,
            "operatingTime": self.OperatingTime
        }    
    
    def write(self, data):
        self.DeviceLock.acquire()
        try:
            self.Device.output = data        
        except Exception as ex:
            self._diagnostic["error"] = { "source": "BeckhofDisplayController.write", "class": str(ex.__class__), "doc": str(ex.__doc__), "time": self._diagnostic["time"] - datetime.datetime.now() }
            EcatLogger.debug(f"{self._diagnostic}")
        finally:
            self.DeviceLock.release()

    def output(self, data):

        if not self.Enabled:
            return False

        self._lock.acquire()
        try:
            changed = False

            if "data" in data.keys():
                self.Data = data["data"]
            
            if "template" in data.keys():
                changed = not all(t == self.Template[i] for i,t in enumerate(data["template"]))
                self.Template = data["template"]        

            if "code" in data.keys():
                changed = changed or not all(c["value"] == self.Code[i]["value"] for i,c in enumerate(data["code"])) \
                                  or not all(c["digit"] == self.Code[i]["digit"] for i,c in enumerate(data["code"]))
                self.Code = data["code"].copy()
            
            if (changed):
                self.update()

        except Exception as ex:
            self._diagnostic["error"] = { "source": "BeckhofDisplayController.output", "class": str(ex.__class__), "doc": str(ex.__doc__), "time": self._diagnostic["time"] - datetime.datetime.now() }
            EcatLogger.debug(f"{self._diagnostic}")
        finally:
            self._lock.release()
        
        return True      
    
    _moving = False
    def _get_moving(self):
        return self._moving
    Moving = property(fget=_get_moving)

    def callback(self, *args):

        arg = args[0]        
        name = arg["name"]

        if 'value' in list(arg['value'].keys()):
            pass

            '''
            if name == "EL7041":

                code = self.Code.copy()
                code[0]["value"] = self.CodeMap['DEGREE']
                code[0]["digit"] = 0
                self.Code = code.copy()

                val = arg['value']['value']

                pos = val['position']

                steps = 12800 # 360°
                ratio = 50

                sign = -1 if pos >ratio * steps else +1
                pos = ULONG_MAX - pos if sign <0 else pos

                data = self.Data.copy()
                data[0] = sign * int(100 * 360 * pos / ratio / steps)
                
                self.Data = data.copy()

            if name == "EL3164":

                val = [int(v/10.0) for v in arg['value']['value']]

                self._moving = sum(val) == 3
                if self._moving:

                    code = self.Code.copy()
                    code[0]["value"] = self.CodeMap['MOVING']
                    code[0]["digit"] = 0
                    self.Code = code.copy()

            if name == "EL6021":

                val = arg['value']['value']

                if isinstance(val, dict):

                    if '0x11.RPY' in list(val.keys()):

                        axis = 0

                        val = val['0x11.RPY']['value']

                        data = self.Data.copy()
                        data[1] =  int((val[axis])*100)
                        self.Data = data.copy()
            '''


