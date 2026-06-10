
import math
import struct,time
import numpy as np
import ctypes
from threading import Lock, Event, Thread
import re
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

    def status(self, value):        
        stat = list(map(int,list(f'{value[0]:08b}')))[::-1] + list(map(int,list(f'{value[1]:08b}')))[::-1]
        statInfo = {
            'TA': stat[0], # transmit accepted
            'RR': stat[1], # receive request
            'IA': stat[2], # init accepted
            'BF': stat[3], # buffer full
            'PE': stat[4], # parity error
            'FE': stat[5], # frame error 
            'OE': stat[6], # overrun error
                           # input length
            'IL': int("".join(list(map(str,stat[8:16]))[::-1]),2),
        }
        return stat, statInfo
    
    def control(self, value):
        ctrl = list(map(int,list(f'{value[0]:08b}')))[::-1] + list(map(int,list(f'{value[1]:08b}')))[::-1]
        ctrlInfo = {
            'TR': ctrl[0], # transmit request
            'RA': ctrl[1], # receive accepted
            'IR': ctrl[2], # init request
            'SC': ctrl[3], # send cont.
                        # output length
            'OL': int("".join(list(map(str,ctrl[8:16]))[::-1]),2),
        }
        return ctrl, ctrlInfo
    
    def initConfig(self):

        """                
        :param self: 
        """
        try:

            for (a,o,v) in [                
                (0x8000,0x11,6),    # baud rate 9600
                
                (0x8000,0x15,3),    # data frame 8N1
                
                (0x8000,0x06,1),    # half duplex
                (0x8000,0x05,0),    # rate optimization
                
                (0x8000,0x04,0),    # fifo continuous
                (0x8000,0x07,0),    # point to point                
            ]:  
                try:
                    c = self.Device.sdo_read(a,o)        
                    s = len(c)                                                                                                                
                    self.Device.sdo_write(a,o,struct.pack(f'{s}B',v))
                except Exception as ex:
                    EcatLogger.error(f'{a}{o} {ex}')

            # explicit baudrate
            self.Device.sdo_write(0x8000, 0x1B, bytes(ctypes.c_uint32(9600)))

        except pysoem.SdoError as se:
            self._initialized = False
            EcatLogger.error(f"SdoError {se}")  
        except pysoem.PacketError as pe:
            self._initialized = False
            EcatLogger.error(f"PacketError {pe}")  
        except pysoem.MailboxError as me:
            self._initialized = False
            EcatLogger.error(f"MailboxError {me}")  
        except pysoem.WkcError as we:
            self._initialized = False
            EcatLogger.error(f"WkcError {we}")  
        except Exception as ex:
            self._initialized = False
            EcatLogger.error(f"Exception {ex}")      

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
    

class EsiModbusController(ModbusController):

    _key = "P1TOB1"

    class RxMapEx:
        register = 0x1C12
        address = [0x1606]    

    class TxMapEx:
        register = 0x1C13
        address = [0x1A06]
    
    _reader: Thread = None
        
    _addr = [(0x00, "0")]
    def _get_addr(self): 
        return self._addr
    Addr:list[(int,int)] = property(fget=_get_addr)

    def __init__(self, index, device, lock, addr=[0x00], debug=False) -> None:
        super().__init__(index, device, lock, debug)
        self._addr = addr

    def _enablePdoAssignment(self, enable=False):
        try:
            if not enable:
                # DISABLE pdo mapping assignment
                self.Device.sdo_write(EsiModbusController.TxMapEx.register, 0, bytes(ctypes.c_uint8(0)))
                self.Device.sdo_write(EsiModbusController.RxMapEx.register, 0, bytes(ctypes.c_uint8(0))) 
            else:
                # ENABLE pdo mapping assignment
                self.Device.sdo_write(EsiModbusController.TxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(EsiModbusController.TxMapEx.address))))
                self.Device.sdo_write(EsiModbusController.RxMapEx.register, 0, 
                                    bytes(ctypes.c_uint8(len(EsiModbusController.RxMapEx.address)))) 
        except Exception as ex:
            EcatLogger.error(f"{ex}")

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

    def initConfig(self):

        """                
        :param self: 
        """

        try:

            self._enablePdoAssignment(False)
        
            addr = EsiModbusController.TxMapEx.register            
            for i,value in enumerate(EsiModbusController.TxMapEx.address):
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))

            # outputs; write; master-slave  
            addr = EsiModbusController.RxMapEx.register            
            for i,value in enumerate(EsiModbusController.RxMapEx.address): 
                self.Device.sdo_write(addr, i +1, bytes(ctypes.c_uint16(value)))  

            self._enablePdoAssignment(True)
                        
            self.Device.sdo_write(0x8000, 0x02, bytes(ctypes.c_bool(0))) # xon/xoff tx            
            self.Device.sdo_write(0x8000, 0x03, bytes(ctypes.c_bool(0))) # xon/xoff rx
            self.Device.sdo_write(0x8000, 0x04, bytes(ctypes.c_bool(0))) # fifo contin.
            self.Device.sdo_write(0x8000, 0x05, bytes(ctypes.c_bool(0))) # rate optim.
            self.Device.sdo_write(0x8000, 0x07, bytes(ctypes.c_bool(0))) # ptp

            self.Device.sdo_write(0x8000, 0x06, bytes(ctypes.c_bool(1))) # half duplex
            self.Device.sdo_write(0x8000, 0x11, bytes(ctypes.c_uint8(9))) # baud rate 9 ~ 57600, 6 ~ 9600
            self.Device.sdo_write(0x8000, 0x15, bytes(ctypes.c_uint8(3))) # data frame 3 ~ 8N1
            self.Device.sdo_write(0x8000, 0x1A, bytes(ctypes.c_uint16(864))) # rx buf. full

        except pysoem.SdoError as se:
            self._initialized = False
            EcatLogger.error(f"SdoError {se}")  
        except pysoem.PacketError as pe:
            self._initialized = False
            EcatLogger.error(f"PacketError {pe}")  
        except pysoem.MailboxError as me:
            self._initialized = False
            EcatLogger.error(f"MailboxError {me}")  
        except pysoem.WkcError as we:
            self._initialized = False
            EcatLogger.error(f"WkcError {we}")  
        except Exception as ex:
            self._initialized = False
            EcatLogger.error(f"Exception {ex}") 

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

    def data_(self, xmd):        
        xmd = ("#"+":".join(xmd)+"\r\n").encode("ASCII")
        return len(xmd), list(xmd)
    
    _toggle = 0
        
    def compute(self):

        EcatLogger.debug(f"start computing {self.__class__.__name__}")
        
        delay = 0.02

        noData = {}
        for a, no in self.Addr:
            noData[no] = { "p": None, "T": None, "addr": a }

        while not self._exit.is_set():

            for a, no in self.Addr:

                for n, cmd in [
                    (25, [no, "RP", "Bar"]),
                    (24, [no, "RT", "C"])
                ]:

                    num, xmd = self.data_(cmd)
                   
                    #                 
                    cw = int(self._toggle)
                    data = [cw, num] + xmd
                    self.write(data)

                    data = self.input()
                    sw, si = self.status(data)
                    rmd = ""
                   
                    try:

                        if si["IL"] == n:

                            rmd = ''.join(map(chr,data[2:si["IL"]]))
                            rmd = re.sub(f"\\$|{cmd[2]}:|\r\n", "", rmd)
                            rno, cmd, val = re.split(":", rmd)
                            val = float(val)
                            if cmd == "RP":
                                noData[rno]["p"] = val
                            elif cmd == "RT":
                                noData[rno]["T"] = val
                    
                    except Exception as ex:
                        EcatLogger.error(f"{ex}")
                    
                    data = [cw|int(self._toggle)<<1, num]
                    self.write(data)                

                    self._toggle ^= 1                
                                    
                    self._exit.wait(delay)

                valid = noData[no]["p"] is not None and noData[no]["T"] is not None

                if valid:                    
                    t = time.time_ns()                    
                    self.publish(a, {            
                        'key': self._key,
                        'addr': a,
                        'p': noData[no]["p"],
                        'T': noData[no]["T"],
                        't': t,
                        "no": no
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
    