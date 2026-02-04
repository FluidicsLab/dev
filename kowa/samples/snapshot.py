#!/usr/bin/env python3

import os
import sys

import datetime
import ctypes
import typing
from logging import getLogger

import numpy as np
import cv2
import kge

logger = getLogger(__name__)

def setting_logger():
    import logging
    logger.setLevel(logging.DEBUG)

    class CustomFormatter(logging.Formatter):
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
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)

def demo() -> typing.Optional[int]:
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

if __name__ == "__main__":
    setting_logger()
    exit(demo())
