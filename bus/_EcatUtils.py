
import math, os, sys
import numpy as np
from PyQt5.QtGui import QIcon

from PyQt5.QtCore import QFile, QDir, QSettings, QObject, QMetaMethod
from PyQt5Singleton import Singleton


class EcatSettings(QSettings, metaclass=Singleton):
    
    def __init__(self, parent=None, **kwargs):
        super().__init__(EcatSettings.filename(), QSettings.IniFormat)

    @staticmethod
    def filename() -> str:
        return EcatUtils.application_directory_() + os.sep + "_EcatSettings.ini"

    @staticmethod
    def directory() -> str:
        return QDir(EcatSettings.filename()).currentPath()
    

class EcatUtils:

    @staticmethod
    def size_str_(nbytes):
        suffixes = ['B','KB','MB','GB','TB','PB']
        human = nbytes
        rank = 0
        if nbytes != 0:
            rank = int((math.log10(nbytes)) / 3)
            rank = min(rank, len(suffixes) - 1)
            human = nbytes / (1024.0 ** rank)
        f = ('%.2f' % human).rstrip('0').rstrip('.')
        return '%s %s' % (f, suffixes[rank])
    
    @staticmethod
    def load_style_(path):
        rc = ""
        stylesheet: QFile = QFile(path)
        if stylesheet.exists():
            stylesheet.open(QFile.ReadOnly)
            rc = str(stylesheet.readAll(), 'utf-8')
        return rc
    
    @staticmethod
    def application_directory_():
        try:
            rc = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
        except NameError:
            rc = os.getcwd()
        return rc
    
    @staticmethod
    def media_directory_():
        return os.path.join(EcatUtils.application_directory_(),"media")

    @staticmethod
    def application_icon_():
        return QIcon(os.path.join(EcatUtils.media_directory_(),EcatSettings().value("application/icon")))
    
    @staticmethod
    def signal_method(obj: QObject, name:str):        
        meta = obj.metaObject()
        for i in range (meta.methodCount()):
            method = meta.method(i)
            if not method.isValid():
                continue
            if method.methodType() == QMetaMethod.Signal and method.name() == name:
                return method
        return None
    
    @staticmethod
    def signal_connected(obj: QObject, name:str):
         return obj.isSignalConnected(EcatUtils.signal_method(obj, name))
    
    @staticmethod
    def signal_methods(obj: QObject):
        rc = []
        meta = obj.metaObject()
        for i in range (meta.methodCount()):
            method = meta.method(i)
            if not method.isValid():
                continue
            if method.methodType() == QMetaMethod.Signal:
                rc.append(str(method.name()))
        return rc
 
    @staticmethod
    def widget_debug(self, oParent, level=1):    
        print("".join(['-']*level),oParent)
        for oChild in oParent.children():
            EcatUtils.widget_debug(oChild, level+1)

    zoom_ = lambda a,b: "".join([c[0] if c[0]!="x" else c[1] for c in list(zip(list(a),list(b)))])
    compare_ = lambda a,b: np.sum([0 if c[0]==c[1] or c[0]=="x" else 1 for c in list(zip(list(a),list(b)))])

    exclude_ = lambda s, exclude: np.sum([1 for b in exclude if s.lower().find(b) >= 0]+[0])

    @staticmethod
    def exception_str_(value):
        if isinstance(value, Exception): 
            value = value.message if hasattr(value, "message") else value
        return str(value)
    
    @staticmethod
    def axb_(aa,bb):
        rc = []
        for a in aa: 
            for b in bb: rc.append((a,b))
        return rc
    
    @staticmethod
    def comp_(b):         
        
        n = len(b)
        ones = "" 
        twos = "" 
        
        for i in range(n): 
            ones += ('1' if b[i] == '0' else '0')  

        ones = list(ones.strip("")) 
        twos = list(ones) 
        for i in range(n - 1, -1, -1): 
        
            if (ones[i] == '1'): 
                twos[i] = '0'
            else:          
                twos[i] = '1'
                break

        i -= 1    
        if (i == -1): 
            twos.insert(0, '1')  

        return "".join(ones), "".join(twos)


class EcatDeviceUtils:

    def PID(Kp, Ki, Kd, steps=1000):
            
        # initialize
        e_prev = 0
        t_prev = -100
        
        I = 0
        II = []

        MV = 0
        P, I, D = 0, 0, 0
        
        e, dt = 0., 0.
                        
        while True:

            # yield MV, wait for new t, PV, SP
            t, PV, SP = yield MV
            
            # PID calculations
            e = PV - SP
            dt = t - t_prev
            
            P = Kp * e
            
            II.append(Ki * e * dt)
            I = np.sum(II)

            D = Kd*(e - e_prev) / dt if dt != 0. else 0.
            
            MV = P + I + D
            
            # update stored data for next iteration
            e_prev = e
            t_prev = t

            while len(II) > steps:
                II.pop(0) 

    @staticmethod
    def ITS90(t,R0):
        A,B,C = 3.9083*10**-3, -5.775*10**-7, -4.183*10**-12
        return R0 * (1.0 + A*t + B*t**2 + (C*(t-100)*t**3 if t<0 else 0.0))
    
    @staticmethod
    def IEEE754(data):
        N = "".join([format(x,"08b") for x in data])
        a = int(N[0])           # sign,     1 bit
        b = int(N[1:9],2)       # exponent, 8 bits
        c = int("1"+N[9:], 2)   # fraction, len(N)-9 bits
        sc = (len(N)-9 - (b-127))
        return (-1)**a * c / (1<<sc) if sc >=0 else None
    
    @staticmethod
    def CRC16(data: list[int]) -> str:
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
        return [rc[2:4],rc[0:2]]  