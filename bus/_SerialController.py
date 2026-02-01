
import struct
import pysoem
import time
from threading import Lock, Event, Thread
import binascii

from _EcatObject import EcatLogger


class SerialController(object):

    _debug = False    
    
    _writer: Thread = None        
        
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

    _data = {}
    def _get_data(self): return self._data
    Data = property(fget=_get_data)    
    
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
            
    def run(self):
        return False
    

class GscSerialController(SerialController):

    _writer: Thread = None

    Axis = 1

    LfCr = [0x0d,0x0a]
    
    TxMap = {
        'status': 'Q:'
    }

    RxMap = {
    }

    def __init__(self, index, device, lock, debug=False) -> None:
        super().__init__(index, device, lock, debug)

    def input(self):
        raw = self.Device.input
        rlen = len(raw)
        rc = struct.unpack(f'{rlen}B',raw)  
        return rc
                    
    def write(self, data):
        self.DeviceLock.acquire()
        try:
            self.Device.output = data
        finally:
            self.DeviceLock.release()
        
    def status(self, input):        
        value = input
        status = list(map(int,list(f'{value[0]:08b}')))[::-1] + list(map(int,list(f'{value[1]:08b}')))[::-1]        
        statusInfo = {
            'TA': status[0],    # transmit accepted
            'RR': status[1],    # receive request
            'IA': status[2],    # init accepted
            'BF': status[3],    # buffer overrun
            'PE': status[4],    # parity error
            'FE': status[5],    # framing error
            'OE': status[6],    # overrun error
                                # input length
            'IL': int("".join(list(map(str,status[8:16]))[::-1]),2),
        }
        return status, statusInfo        

    @staticmethod
    def int2byte(value):
        value = [hex(h).replace("0x","").zfill(2) for h in value]
        return bytes(bytearray.fromhex("".join(value)))

    @staticmethod
    def char2hex(value):
        rc = binascii.hexlify(value.encode()).decode()
        return [int(rc[i:i+2],16) for i in range(0,len(rc),2)] + GscSerialController.LfCr

    @staticmethod
    def byte2char(value):
        return [chr(c) for c in value]

    def subscribe(self, data):

        self._lock.acquire()
        try:

            if 'A' in data.keys():

                key = 'A'
                value = int(data[key])
                d = ('-' if value < 0 else '+')
                cmd = key + ':' + f'{GscSerialController.Axis}' + d + 'P' + f'{abs(value):d}'
                
                self.RxMap.update({'move':cmd})
                self.RxMap.update({'drive':'G:'})
                
            elif 'R' in data.keys():

                key = 'R'
                value = int(data[key])
                cmd = 'A:' + f'{GscSerialController.Axis}' + '-P' + f'{abs(value):d}'

                self.RxMap.update({'move':cmd})
                self.RxMap.update({'drive':'G:'})

                self.RxMap.update({'zero':'R:'+f'{GscSerialController.Axis}'})

            elif 'Q' in data.keys():

                self.RxMap.update({'status':'Q:'})

        finally:
            self._lock.release()

    def publish(self, key, value):
        self._data[key] = value

    _initialized = False

    def init(self):

        rc = False
        try:            
            while not rc and not self._exit.is_set():                
                self.write(GscSerialController.int2byte([0x04,0x00]))                
                _, si = self.status(self.input())
                rc = si['IA'] == 1

            if rc:
                rc = False
                while not rc and not self._exit.is_set():                
                    self.write(GscSerialController.int2byte([0x00,0x00]))                
                    _, si = self.status(self.input())
                    rc = si['IA'] == 0                
        except:
            pass
        finally:
            return rc
               
    _toggle = 0

    def compute(self):

        #while not self._exit.is_set():
        if not self._exit.is_set():

            for key in GscSerialController.RxMap.keys():                    

                txm = GscSerialController.RxMap[key]                    

                delay = .15 #1/9600 * (num +2) * 1000

                xmd = GscSerialController.char2hex(txm)
                num = len(xmd)

                self._toggle ^= 1
                cw = int(f"0000000{self._toggle}", 2)        
                self.write(GscSerialController.int2byte([cw, num] + xmd))
                self._exit.wait(delay)

                # accept
                self.write(GscSerialController.int2byte([cw|int(self._toggle)<<1, num]))
                self._exit.wait(delay)

                ack,dat = [],[]
                sta = None
                                    
                inp = self.input()
                _, sta = self.status(inp)   

                cnt = sta['IL']
                
                dat = GscSerialController.byte2char(inp[2:2+cnt])

                EcatLogger.debug(f"{txm} {sta} {dat}")

                dat = "".join(dat).replace("\r\n","")

                ack = None
                val = None
                if 'status' == key:
                    try:
                        ack = dat[-5:].split(",")
                        val = int(dat[:-6].replace(" ",""))
                    except:
                        pass

                else:            
                    try: 
                        ack = dat[-3:].split(",") 
                    except: 
                        pass
                        
                self.publish(
                    key, {
                        'key': key,
                        'ack': ack,
                        'val': val,
                        'dat': dat,
                        'mod': time.time_ns()
                        })

            GscSerialController.RxMap = {}        
        
        
    def run(self):

        if not self.Enabled:
            return None
        
        if (self.Device.state & pysoem.OP_STATE) != self.Device.state:
            return None

        self._lock.acquire()
        try:            
        
            if not self._initialized:        
                self._initialized = self.init()
                #if self._initialized:
                    #self._writer = Thread(target=self.compute)
                    #self._writer.start()
            
            if self._initialized:
                self.compute()
                   
        finally:
            self._lock.release()

        return self.Data