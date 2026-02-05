import os
import sys

from lxml import etree

import datetime
import ctypes
import typing
from logging import getLogger

import numpy as np
import cv2
import kge

import logging

PIXEL_FORMAT = {
    "Mono8":            0x01080001,
    "Mono10":           0x01100003,
    "Mono10Packed":     0x010C0004,
    "Mono12":           0x01100005,
    "Mono12Packed":     0x010C0006,
    "BayerRG8":         0x01080009,
    "BayerRG10":        0x0110000D,
    "BayerRG10Packed":  0x010C0027,
    "BayerRG12":        0x01100011,
    "BayerRG12Packed":  0x010C002B    
}

BINNING_TYPE = ["OFF","BINNING2X2","BINNING3X3","BINNING4X4","BINNING2X1","BINNING3X1","BINNING4X1"]
BINNING_DIVIDER = ["DIVIDE_1","DIVIDE_2","DIVIDE_3","DIVIDE_4","DIVIDE_9","DIVIDE_16"]

ACQUISITION_MODE = ["SINGLE_FRAME","MULTI_FRAME","CONTINOUS"]

KowaLogger = getLogger("__KowaLogger__")
KowaLogger.setLevel(logging.DEBUG)

class KowaLoggerFormatter(logging.Formatter):
    """ logging Customed formatter. """
    _baseformat = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
ch.setFormatter(KowaLoggerFormatter())
KowaLogger.addHandler(ch)

TIMEOUT_DISCOVERY = 1_000   
CAMERA_INDEX = 0 

class KowaConfig:

    _items = {}

    def __str__(self):
        for key in self._items.keys():
            for mode in self._items[key].keys():
                KowaLogger.debug(f"{key}({mode}) {self._items[key][mode]}")
        return ""

    def update(self, key, mode, name, attr):        
        if key not in self._items.keys():
            self._items[key] = {}  
        if mode not in self._items[key].keys():
            self._items[key][mode] = []
        self._items[key][mode].append(( name, attr ))

    def parse(self, filename):

        tree = etree.parse(filename)
        if tree is not None:
            
            root = tree.getroot()

            for cat in root.xpath("./Group/Category[1]"):
                
                key = cat.get('Name')

                ifeat = cat.xpath(f"../Integer")
                ffeat = cat.xpath(f"../Float")
                efeat = cat.xpath(f"../Enumeration")
                sfeat = cat.xpath(f"../StringReg")
                bfeat = cat.xpath(f"../Boolean")

                if len(ifeat) > 0:
                    for feat in ifeat:
                        name = feat.get('Name')
                        attr = {}
                        self.update(key, 'integer', name, attr)
                if len(ffeat) > 0:
                    for feat in ffeat:
                        name = feat.get('Name')
                        attr = None
                        self.update(key, 'float', name, attr)
                if len(efeat) > 0:
                    for feat in efeat:
                        name = feat.get('Name')
                        attr = { 'keys': feat.xpath('EnumEntry/@Name'), 'values': feat.xpath('EnumEntry/Value/text()') }
                        self.update(key, 'enumeration', name, attr)
                if len(sfeat) > 0:        
                    for feat in sfeat:
                        name = feat.get('Name')
                        attr = None
                        self.update(key, 'string', name, attr)
                if len(bfeat) > 0:
                    for feat in bfeat:
                        name = feat.get('Name')
                        attr = None
                        self.update(key, 'boolean', name, attr)

    def debug(self, camera, modes):

        for key in self._items.keys():
            for mode in self._items[key].keys():

                try:

                    if mode == "integer" and mode in modes:
                        for feat in self._items[key][mode]:
                            name = feat[0]
                            KowaLogger.debug(f"{key:25s} {name:32s} {camera.getFeatureInteger(name)}")

                    if mode == "float" and mode in modes:
                        for feat in self._items[key][mode]:
                            name = feat[0]
                            KowaLogger.debug(f"{key:25s} {name:32s} {camera.getFeatureFloat(name)}")

                    if mode == "boolean" and mode in modes:
                        for feat in self._items[key][mode]:
                            name = feat[0]
                            KowaLogger.debug(f"{key:25s} {name:32s} {camera.getFeatureBoolean(name)}")

                    if mode == "string" and mode in modes:
                        for feat in self._items[key][mode]:
                            name = feat[0]
                            KowaLogger.debug(f"{key:25s} {name:32s} {camera.getFeatureString(name)}")

                    if mode == "enumeration" and mode in modes:
                        for feat in self._items[key][mode]:
                            name = feat[0]
                            KowaLogger.debug(f"{key:25s} {name:32s} {camera.getFeatureEnumeration(name)}")

                except Exception as ex:

                    KowaLogger.error(f"{key:25s} {name:32s} ")



class KowaDevice(object):

    _config: KowaConfig = None
    def _get_config(self):
        if self._config is None:
            self._config = KowaConfig()
        return self._config
    Config = property(fget=_get_config)

    def __init__(self):
        pass
    
    def _get_camera(self):
        return self._camera
    Camera = property(fget=_get_camera)

    _camera = None
    def startup(self):
        
        discovery = kge.discovery(timeout_ms=TIMEOUT_DISCOVERY)

        if discovery.Count == 1:

            try:

                self._camera = kge.initEx(connection=discovery[CAMERA_INDEX], 
                                        save_xml=1, 
                                        open_mode=kge.Access.exclusive)
                self._camera.initFilterDriver()
                self._camera.openStreamChannel()

                self._camera.setDetailedLog(32)

                self.debug(self._camera)

            except Exception as ex:
                KowaLogger.error(ex)

    def shutdown(self):
        if self._camera is not None and not self._camera.closed:
            self._camera.closeStreamChannel()
            self._camera.closeFilterDriver()
            self._camera.close()
        self._camera = None

    def debug(self, camera):
        
        KowaLogger.debug("--------------------------")

        KowaLogger.debug(f"dll abi version           {kge.getDllAbiVersion()}")
        KowaLogger.debug(f"dll version               {kge.getDllVersion()}")
        
        KowaLogger.debug(f"max packet size           {camera.testFindMaxPacketSize()}")

        KowaLogger.debug(f"connection status         {camera.getConnectionStatus()}")       # status 0=ok, 1=timeout, 2=access denied; eval 0=ok, 1=expired, 2=evaluation
        KowaLogger.debug(f"filter driver             {camera.getFilterDriverVersion()}")        
        KowaLogger.debug(f"heart beat rate           {camera.getHeartbeatRate()}")          # timeout ms for connection checking  
        KowaLogger.debug(f"ring buffer count         {camera.getBufferCount()}")
        KowaLogger.debug(f"fps                       {camera.getImageFPS()}")

        

        config_filename = "config/kowa.xml"
        #with open(config_filename, "wb") as f:
        #    f.write(camera.getXmlFile())

        self.Config.parse(config_filename)
        KowaLogger.debug("--------------------------integer")
        self.Config.debug(camera, ['integer'])
        KowaLogger.debug("--------------------------float")
        self.Config.debug(camera, ['float'])
        KowaLogger.debug("--------------------------boolean")
        self.Config.debug(camera, ['boolean'])
        KowaLogger.debug("--------------------------string")
        self.Config.debug(camera, ['string'])
        KowaLogger.debug("--------------------------enumeration")
        self.Config.debug(camera, ['enumeration'])
        
    def run() -> typing.Optional[int]:

        pass

        """

        dis = kge.discovery(1000)
        for i,d in enumerate(dis):
            logger.info("Device: %d", i)
            logger.info(d)

        if dis.Count == 0:
            logger.error("No GigE Device found.")
            return 1
        if dis.Count > 1:
            logger.info("Too GigE Device found(%s).", len(dis))
            logger.info("selected primary(0) device.")

        with kge.initEx(dis[0], 0, 1) as camera:
            logger.info("selected camera no: %s", camera.camera_no)

            # setSchemaPath and initXml was implicitly called at init.
            with camera.initFilterDriver():
                with camera.openStreamChannel():

                    camera.setPacketResend(1)

                    camera.setFeatureInteger("GevSCPD", 500)
                    camera.setFeatureInteger("ExposureTime", 2000)

                    # test maximum achievable packet size
                    max_packet_size = camera.testFindMaxPacketSize()
                    logger.info("max_packet_size: %d", max_packet_size)

                    width = camera.getFeatureInteger("Width")
                    height = camera.getFeatureInteger("Height")
                    pixel_format = camera.getFeatureInteger("PixelFormat")
                    img_size = camera.getFeatureInteger("PayloadSize")
                    logger.info("width: %d", width)
                    logger.info("height: %d", height)
                    logger.info("pixelFormat: %#010x", pixel_format)
                    logger.info("pixelformat(bpp): %#04x", (pixel_format>>16)&0xff)
                    logger.info("payloadsize: %d", img_size)

                    if height == 0 or width == 0 or img_size == 0:
                        logger.error("Image is empty.")
                        return 2

                    image_buffer = (ctypes.c_uint8*img_size)()
                    df = 2880
                    dsize=(width*df//height, df) # (w,h) to df pixel

                    logger.info("Start acquisiton")
                    with camera.acquisitionStart(0):

                        logger.info("Display image ...")
                        print("Display image ...")
                        cv2.namedWindow("frame", cv2.WINDOW_NORMAL)

                        keys_quit = tuple(map(ord, "\x1bq"))
                        keys_saveimg = tuple(map(ord, " s"))
                        keys_print = tuple(range(0, 256))

                        print("usage:")
                        for k,v in {
                            "ESC"   : "Quit",
                            "q"     : "Quit",
                            "SPACE" : "save captured image",
                            "s"     : "save captured image",
                        }.items():
                            print(f"    {k:8}: {v}")

                        frameno=-1
                        while True:
                            frameno+=1
                            try:
                                img_header = camera.getImageBuffer(image_buffer)
                            except kge.GEVGrabError as ex:
                                logger.error("%s", ex.missing_returned_value)
                            else:
                                grabbed_img = np.ctypeslib.as_array(image_buffer).reshape(height,width)
                                color_img = cv2.cvtColor(grabbed_img, cv2.COLOR_BayerBG2BGR)
                                display_img = cv2.resize(color_img, dsize=dsize,
                                                        interpolation=cv2.INTER_AREA)
                                cv2.imshow("frame", display_img)
                                key = cv2.waitKey(1)
                                if key != -1:
                                    logger.info("pressed key: %d", key)
                                if key in keys_print:
                                    print(f"pressed key: {key}")
                                if key in keys_saveimg:
                                    basedir="kge_captured"
                                    os.makedirs(basedir, exist_ok=True)
                                    now=datetime.datetime.now()
                                    write_path=os.path.join(basedir,
                                                            f"{now:%Y%m%d_%H%M%S_%f}_{frameno:08}.png")
                                    cv2.imwrite(write_path, grabbed_img)
                                    print(f"saved image: '{write_path}'")
                                if key in keys_quit:
                                    cv2.destroyAllWindows()
                                    return None

        """

if __name__ == "__main__":
    
    os.system('cls')

    device = KowaDevice()
    device.startup()

    #input("<ENTER>")

    device.shutdown()
