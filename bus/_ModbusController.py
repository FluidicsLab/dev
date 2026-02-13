
import math
import struct,time
import numpy as np
import ctypes
from threading import Lock, Event, Thread

import pysoem

from _EcatUtils import EcatDeviceUtils

from _EcatObject import EcatLogger


class ModbusController(object):

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

    _deviceLock: Lock = None
    def _get_deviceLock(self): return self._deviceLock
    DeviceLock: Lock = property(fget=_get_deviceLock)

    _data = None
    def _get_data(self): 
        if self._data is None:
            self._data = dict()
        return self._data
    Data = property(fget=_get_data)    
        
    @staticmethod
    def crc_(data: list[int]):
        data = bytearray(data)
        crc = 0xFFFF
        for b in data:
            crc ^= b
            for _ in range(0,8):
                bcarry = crc & 0x0001
                crc >>= 1
                if bcarry: 
                    crc ^= 0xa001
        rc = hex(crc).replace('0x','').zfill(4)
        crc = [rc[2:4],rc[0:2]]  
        return [int(crc[0],16),int(crc[1],16)]    

    def __init__(self, index, device, lock, debug=False) -> None:   
        super().__init__()    
        self._index = index 
        self._device = device
        self._deviceLock = lock
        self._debug = debug

    def status(self, input):
        value = input
        status = list(map(int,list(f'{value[0]:08b}')))[::-1] + list(map(int,list(f'{value[1]:08b}')))[::-1]
        statusInfo = {
            'TA': status[0], # transmit accepted
            'RR': status[1], # receive request
            'IA': status[2], # init accepted
            'BF': status[3], # buffer full
            'PE': status[4], # parity error
            'FE': status[5], # frame error 
            'OE': status[6], # overrun error
                             # input length
            'IL': int("".join(list(map(str,status[8:16]))[::-1]),2),
        }
        return status, statusInfo

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
            
    def run(self):
        return False
    

class Wt901cModbusController(ModbusController):

    _reader: Thread = None
    
    TxRanges = {
        'RPY': 180.0,
        'TMP': 1./100.0
    }

    TxMap = {   
        # roll, pitch, yaw, temperature
        'RPY': [0x03, 0x00,0x3d, 0x00,0x04],
        # pressure, height
        'SUP': [0x03, 0x00,0x45, 0x00,0x04]
    }  

    _addr = [0x00]
    def _get_addr(self): 
        return self._addr
    Addr:list[int] = property(fget=_get_addr)

    def __init__(self, index, device, lock, addr=[0x00], debug=False) -> None:
        super().__init__(index, device, lock, debug)
        self._addr = addr

    def input(self):
        raw = self.Device.input
        rlen = len(raw)
        rc = struct.unpack(f'{rlen}B',raw)  
        return rc
                    
    def write(self, data):
        self.DeviceLock.acquire()
        try:
            self.Device.output = bytes(bytearray(data))
        finally:
            self.DeviceLock.release()
       
    def subscribe(self, data):
        pass

    def publish(self, key, value):        
        self.Data[key] = value

    _initialized = False          
    def init(self):

        rc = False
        try:

            while not rc and not self._exit.is_set():
                self.write([int(f"00000100", 2), 0x00])           
                _, si = self.status(self.input())
                rc = si['IA'] == 1

            rc = False
            while not rc and not self._exit.is_set():
                self.write([int(f"00000000", 2), 0x00])           
                _, si = self.status(self.input())
                rc = si['IA'] == 0

        except Exception as ex:
            EcatLogger.debug(f"{ex}")

        finally:
            return rc
                
    _toggle = 1

    def compute(self):

        EcatLogger.debug(f"start computing {self.__class__.__name__}")

        while not self._exit.is_set():

            for addr in self.Addr:

                for key in self.TxMap.keys():

                    try:

                        xmd = self.TxMap[key]

                        xmd = [addr] + xmd 
                        
                        crc = ModbusController.crc_(xmd)     
                        xmd = xmd + crc + [0x00]
                        num = len(xmd)
                                                
                        cw = int(f"0000000{self._toggle}", 2)
                        self.write([cw, num] + xmd)      
                        # 

                        data = ["0x" + hex(b).replace("0x","").zfill(2) for b in bytearray(self.Device.input)]
                        sw = bin(int(data[0],16)).replace("0b","").zfill(8)

                        off = 5
                        id, func, cnt = data[2:off]
                        cnt = int(cnt,16)

                        if int(id,16) in self.Addr and cnt >0 and 0 != int(sw,2):
                             
                            if key in ['SUP']:

                                if 8 == cnt:

                                    al,ah = [int(data[5],16)<<8|int(data[6],16), int(data[7],16)<<8|int(data[8],16)]
                                    a = ah<<16|al

                                    bl,bh = [int(data[9],16)<<8|int(data[10],16), int(data[11],16)<<8|int(data[12],16)]
                                    b = bh<<16|bl

                                    self.publish(f"{id}.{key}", {
                                            "addr": id,
                                            "key": key,
                                            "sw": sw,
                                            "modified": time.time_ns(),
                                            "t": time.time_ns(),
                                            "value": [a, b]
                                        })
                                    
                            elif key == 'RPY':

                                if 8 == cnt:

                                    x = int(data[5],16)<<8|int(data[6],16)
                                    y = int(data[7],16)<<8|int(data[8],16)
                                    z = int(data[9],16)<<8|int(data[10],16)

                                    value = [ctypes.c_int16(v).value for v in [x,y,z]]

                                    a,b = Wt901cModbusController.TxRanges[key],32768                                         
                                    
                                    value = [a*v/b for v in value]
                                                                        
                                    self.publish(f"{id}.{key}", {
                                            "addr": id,
                                            "key": key,
                                            "sw": sw,
                                            "modified": time.time_ns(),
                                            "t": time.time_ns(),
                                            "value": value
                                        })
                                    
                                    key = "TMP"                                    
                                    value = [(int(data[11],16)<<8|int(data[12],16)) * Wt901cModbusController.TxRanges[key]]
                                   
                                    self.publish(f"{id}.{key}", {
                                            "addr": id,
                                            "key": key,
                                            "sw": sw,
                                            "modified": time.time_ns(),
                                            "t": time.time_ns(),
                                            "value": value
                                        })
                            

                        # accept 
                        self.write([cw|int(self._toggle)<<1, num])
                        self._toggle ^= 1

                        self._exit.wait(.25)
                                                                                                
                    except Exception as ex:
                        EcatLogger.debug(ex)

        EcatLogger.debug(f"stop computing {self.__class__.__name__}")
                        
        
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
                    self._reader = Thread(target=self.compute)
                    self._reader.start()

        finally:
            self._lock.release()

        return self.Data  
    

class Sth01ModbusController(ModbusController):
    
    _reader: Thread = None

    TxMap = {    
        'THD': [0x04, 0x00,0x00, 0x00,0x03]
    }  

    _addr = [0x00]
    def _get_addr(self): 
        return self._addr
    Addr:list[int] = property(fget=_get_addr)

    def __init__(self, index, device, lock, addr=[0x00], debug=False) -> None:
        super().__init__(index, device, lock, debug)
        self._addr = addr
    
    def input(self):
        raw = self.Device.input
        rlen = len(raw)
        rc = struct.unpack(f'{rlen}B',raw)  
        return rc
                    
    def write(self, data):
        self.DeviceLock.acquire()
        try:
            self.Device.output = bytes(bytearray(data))
        finally:
            self.DeviceLock.release()
        
    def subscribe(self, data):
        pass

    def publish(self, key, value):        
        self.DeviceLock.acquire()
        try:
            self.Data[key] = value
        finally:
            self.DeviceLock.release()

    _initialized = False          
    def init(self):

        rc = False
        try:

            while not rc and not self._exit.is_set():
                self.write([int(f"00000100", 2), 0x00])           
                _, si = self.status(self.input())
                rc = si['IA'] == 1

            rc = False
            while not rc and not self._exit.is_set():
                self.write([int(f"00000000", 2), 0x00])           
                _, si = self.status(self.input())
                rc = si['IA'] == 0

        except Exception as ex:
            EcatLogger.debug(f"{ex}")

        finally:
            return rc
    
    _toggle = 1

    def compute(self):

        EcatLogger.debug(f"start computing {self.__class__.__name__}")
                    
        while not self._exit.is_set():

            for addr in self.Addr:

                for key in self.TxMap.keys():

                    try:

                        xmd = self.TxMap[key]

                        xmd = [addr] + xmd 
                        crc = ModbusController.crc_(xmd)     
                        xmd = xmd + crc
                        num = len(xmd)
                        
                        cw = int(f"0000000{self._toggle}", 2)
                        self.write([cw, num] + xmd)              

                        data = ["0x" + hex(b).replace("0x","").zfill(2) for b in bytearray(self.Device.input)]
                        sw = bin(int(data[0],16)).replace("0b","").zfill(8)

                        if 'THD' == key:

                            if int(data[1],16) >0:

                                addr, _, cnt = data[2:5]
                                cnt = int(cnt,16)
                                if cnt >0:

                                    payload = {
                                        "addr": addr,
                                        "sw": sw,
                                        "modified": time.time_ns(),
                                        
                                        "T": int(data[5],16)<<8|int(data[6],16), # hb<<8|lb
                                        "H": int(data[7],16)<<8|int(data[8],16),
                                        "D": int(data[9],16)<<8|int(data[10],16),

                                        "t": time.time_ns()
                                    }
                                    
                                    self.publish(addr, payload)


                        # accept 
                        self.write([cw|int(self._toggle)<<1, num])
                        
                        self._toggle ^= 1

                        delay = 0.07125
                        
                        self._exit.wait(delay)
                                               
                    except Exception as ex:
                        EcatLogger.debug(ex)

        EcatLogger.debug(f"stop computing {self.__class__.__name__}")
        
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
                    self._reader = Thread(target=self.compute)
                    self._reader.start()

        finally:
            self._lock.release()

        return self.Data    
    

class KellerModbusController(ModbusController):

    _reader: Thread = None
    
    # register read
    # addr, [0x03, StAdd_H, StAdd_L, Reg_H, Reg_L], CRC16_L, CRC16_H
    TxMap = {
        'P1TOB1':   [0x03, 0x01,0x00, 0x00,0x04]
    }    

    _addr = [0x00]
    def _get_addr(self): 
        return self._addr
    Addr:list[int] = property(fget=_get_addr)

    def __init__(self, index, device, lock, addr=[0x00], debug=False) -> None:
        super().__init__(index, device, lock, debug)
        self._addr = addr

    def input(self):
        raw = self.Device.input
        rlen = len(raw)
        rc = struct.unpack(f'{rlen}B',raw)  
        return rc
                    
    def write(self, data):
        self.DeviceLock.acquire()
        try:
            self.Device.output = bytes(bytearray(data))
        finally:
            self.DeviceLock.release()
    
    def subscribe(self, data):
        pass

    def publish(self, key, value):        
        self.DeviceLock.acquire()
        try:
            self.Data[key] = value
        finally:
            self.DeviceLock.release()        

    @staticmethod
    def int2byte(value, crc=[]):
        value = [hex(h).replace("0x","").zfill(2) for h in value]
        value = value + crc
        return bytes(bytearray.fromhex("".join(value)))

    @staticmethod
    def ieee754(key, data):        
        try:         
            addr,_,_ = data[2:5]
            data = data[5:]                
            if key == 'P1TOB1':   
                p,T = data[:4],data[4:8]
                p,T = EcatDeviceUtils.IEEE754(p), EcatDeviceUtils.IEEE754(T)
            elif key == 'P1':
                p,T = data[:4],None
                p = EcatDeviceUtils.IEEE754(p)
            return addr,p,T
        except:
            pass
        return None,None,None  

    _initialized = False  
    
    def init(self):

        rc = False
        try:
            
            while not rc and not self._exit.is_set():
                self.write([int(f"00000100", 2), 0x00])
                _, si = self.status(self.input())
                rc = si['IA'] == 1

            rc = False
            while not rc and not self._exit.is_set():          
                self.write([int(f"00000000", 2), 0x00])
                _, si = self.status(self.input())
                rc = si['IA'] == 0

        except Exception as ex:
            EcatLogger.debug(f"{ex}")

        finally:
            return rc
        
    _toggle = 0

    def compute(self):

        EcatLogger.debug(f"start computing {self.__class__.__name__}")
                    
        while not self._exit.is_set():

            dec = len(self.Addr)
            
            key = list(self.TxMap.keys())[0]

            for addr in self.Addr:
                
                try:
                    xmd = self.TxMap[key]
                    
                    xmd = [addr] + xmd                
                    crc = EcatDeviceUtils.CRC16(xmd)
                    xmd += [int(crc[0],16),int(crc[1],16)]
                    
                    num = len(xmd)
                            
                    cw = int(self._toggle)
                    
                    self.write([cw, num] + xmd)

                    data = [int(hex(b),16) for b in bytearray(self.Device.input)]
                    sw = bin(data[0]).replace("0b","").zfill(8)

                    a, p, T = KellerModbusController.ieee754(key, data)

                    valid = a is not None and a > 0 and T is not None and round(T, 2) >= 10.0 and a in self.Addr
                    
                    if valid:

                        t = time.time_ns()

                        self.publish(a, {            
                            'key': key,
                            'addr': a,
                            'p': p,
                            'T': T,
                            't': t,
                            'e': 1,
                            'sw': sw 
                        })

                    # accept 
                    cc = [cw|int(self._toggle)<<1, num]

                    self.write(cc)
                    
                    self._toggle ^= 1
                        
                    # baud rate * ((letter time) * (letters + crc) + pause time) * count of members
                    # pause time : 1.5ms, letter time: 3.5ms
                    
                    delay = 0.07125

                    self._exit.wait(delay)
                        
                except Exception as ex:
                    EcatLogger.debug(ex)

            for addr in self.Addr:

                if addr not in self.Data.keys():
                    
                    t = time.time_ns()
                    
                    self.publish(addr, {            
                        'key': key,
                        'addr': addr,
                        'p': None,
                        'T': None,
                        't': t,
                        'e': 0,
                        'sw': 0
                    })

        EcatLogger.debug(f"stop computing {self.__class__.__name__}")

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
                    self._reader = Thread(target=self.compute)
                    self._reader.start()
            
        finally:
            self._lock.release()

        return self.Data
    