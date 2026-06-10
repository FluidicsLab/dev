
import serial
import serial.tools.list_ports
import math, time, struct
from types import SimpleNamespace
from threading import Thread,Event,Lock
import re, os
import numpy as np

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

IXDB_MEASURMENT = "am8111"
IXDB_BUCKET = "am8111"
IXDB_ORG = "fxl"
IXDB_TOKEN = "G40DBfhpqDtHQqYk7VOj_rTOOpD6So8xoWoiVXJ3XLpURNU5MpO5uWkX5sOg7G_YeiAf8jqT8n7nSiFgK2mq1A=="
IXDB_URL = "http://localhost:8086"

SERIAL_BAUDRATE = 57600
SERIAL_TIMEOUT = 0.1        # lower - data values only, 
                            # higher - information and analog settings

SENSOR_NO = 1

def ixdb_connect_():    
    client = influxdb_client.InfluxDBClient(
        url=IXDB_URL,
        token=IXDB_TOKEN,
        org=IXDB_ORG
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)
    return client, write_api

def ixdb_disconnect_(client):
    client.close()

def ixdb_write_(write_api, data):
    
    point = influxdb_client.Point(IXDB_MEASURMENT)\
        .tag("addr", data["no"])\
        .tag("tag", "develop")\
        .tag("mode", "digital")\
        .tag("vendor", "esi")\
        .field("temperature", data["T"])\
        .field("pressure", data["p"])
    write_api.write(bucket=IXDB_BUCKET, org=IXDB_ORG, record=point)


def ports_():
    data = dict()
    for port,desc,hwid in serial.tools.list_ports.comports():
                data[port] = SimpleNamespace(**dict(
                    port=port,
                    desc=desc,
                    hwid=hwid
                ))
    return data

def config_():
    return SimpleNamespace(**dict(
        Baudrate = SERIAL_BAUDRATE,
        Bytesize = serial.EIGHTBITS,
        Parity = serial.PARITY_NONE,
        Stopbits = serial.STOPBITS_ONE,
        Timeout = SERIAL_TIMEOUT,
        Xonxoff = False,
        Rtscts = False,
        WriteTimeout = None,
        Dsrdtr = False,
        InterByteTimeout = None,
        Exclusive = None
    ))


def open_(prt, cfg):
    ss = serial.Serial(
        prt.port, 
        cfg.Baudrate, 
        cfg.Bytesize, 
        cfg.Parity, 
        cfg.Stopbits, 
        cfg.Timeout, 
        cfg.Xonxoff, 
        cfg.Rtscts, 
        cfg.WriteTimeout, 
        cfg.Dsrdtr, 
        cfg.InterByteTimeout, 
        cfg.Exclusive)    
    return ss

def close_(ss):
    if ss is not None and ss.is_open:
        ss.close()     

def call_(ss, xmd):    
    xmd = ("#"+":".join(xmd)+"\r\n").encode("ASCII")    
    ss.write(bytearray(xmd))
    ss.flush()
    rmd = []    
    res = ss.read()
    while(res):        
        rmd.append(res.hex())        
        res = ss.read()    
    return bytes.fromhex(''.join(rmd)).decode('ASCII')

def broadcast_(ss):
    rc = []
    try:    
        xmd = ["0", "ID"]            # broadcast ID ~ 0
        rmd = call_(ss, xmd)
        no = re.sub("\$|:ID|\r\n", "", rmd)
        rc.append(no)
    except Exception as ex:     
        print(ex)    
    return rc

def info_(ss, no):
    xmd = [no, "TI"]
    rmd = call_(ss, xmd)
    rmd = re.sub(f"\\$|{no}:TI:", "", rmd)
    rc = []
    for r in rmd.split("\r\n"):
        if len(r) > 0:
            rc.append(r)
    return rc

def analog_(ss, no, setup=None):

    # PL pressure low
    # PH pressure high
    # VL voltage low
    # VH voltage high
    # OM operating mode; LM linear, VC voltage cap, PC pressure cap

    # write
    if setup is not None:
        for key in list(setup.keys()):
            xmd = [no, "AS", key, setup[key]]
            _ = call_(ss, xmd)
    # read 
    xmd = [no, "AS"]
    rmd = call_(ss, xmd)
    rmd = re.sub(f"\\$|{no}:AS:", "", rmd)
    rc = []
    for r in rmd.split("\r\n"):
        if len(r) > 0:
            rc.append(r)
    return rc

def value_(ss, no):
    rc = []    
    for i,xmd in enumerate([
        [no, "RP", "Bar"], 
        [no, "RT", "C"]
        ]):
        rmd = call_(ss, xmd)
        if len(rmd) != 0:
            rc.append(float(re.sub(f"\\$|{xmd[0]}:{xmd[1]}:{xmd[2]}:|\r\n", "", rmd)))
    return rc

def offset_(ss, no):
    rc = []    
    for xmd in [[no, "PO", "Bar"], [no, "TO", "C"]]:
        rmd = call_(ss, xmd)
        rc.append(re.sub(f"\\$|{xmd[0]}:{xmd[1]}:{xmd[2]}:|\r\n", "", rmd))
    return rc

_loopEvent = Event()
_loopThread = None    

def loop_(ss, nos):

    client, write_api = ixdb_connect_()

    for no in nos:        
        print(info_(ss, no))
        print(analog_(ss, no, { "PL": "0.0", "PH": "700.0" }))

    while not _loopEvent.is_set():

        for no in nos:

            t = time.time_ns()        
            val = value_(ss, no)

            print(no, val, (time.time_ns()-t)/1e9)

            if len(val) == 2:
                ixdb_write_(write_api, { "no": no, "p": val[0], "T": val[1] })
        
        _loopEvent.wait(0.10)

    ixdb_disconnect_(client)

_runningEvent = Event()    
def running_():

    try:
        while not _runningEvent.is_set():
            _runningEvent.wait(0.01)

    except KeyboardInterrupt:
        _runningEvent.set()

def main_():

    ports = ports_()
    for k in list(ports.keys()):
        print(ports[k])
    
    prt = ports['COM8']    
    cfg = config_()

    try:
        
        ss = open_(prt, cfg)
        nos = broadcast_(ss)
        
        _loopThread = Thread(target=loop_, args=[ss, nos])
        _loopThread.start() 

        running_()

        _loopEvent.set()
        _loopThread.join()
        
    except Exception as ex:     
        print(ex)

    finally:
        if ss is not None and ss.is_open:
            close_(ss)

if __name__ == '__main__':
    os.system("cls")
    main_() 
