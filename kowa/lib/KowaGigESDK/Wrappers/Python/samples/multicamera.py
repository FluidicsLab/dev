#!/usr/bin/env python3

import os
import sys

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

def init_to_aquisition(dev):
    logger.info("device: %s", dev)
    camera = kge.initEx(dev, 0, 1)
    try:
        logger.info("selected camera no: %s", camera.camera_no)

        # setSchemaPath and initXml was implicitly called at init.
        camera.initFilterDriver()
        camera.openStreamChannel()

        camera.setPacketResend(1)

        camera.setFeatureInteger("GevSCPD", 50000)
        camera.setFeatureInteger("ExposureTime", 5000)

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
            raise Exception("Image is empty.")

        logger.info("Start acquisiton")
        camera.acquisitionStart(0)
        logger.info("Display image")
        logger.info("waiting for console input...")
        return camera
    except:
        camera.close()
        raise

def createbuffer(camera):
    bufsize = camera.getFeatureInteger("PayloadSize")
    return (ctypes.c_uint8*bufsize)()

def demo() -> typing.Optional[int]:
    dis = kge.discovery(1000)
    if len(dis) == 0:
        logger.error("No GigE Device found.")
        return 1

    logger.info("found camera count: %s.", len(dis))
    cameras = [init_to_aquisition(dev) for dev in dis]
    try:
        buffers = [createbuffer(camera) for camera in cameras]
        while True:
            for camera, buf in zip(cameras, buffers):
                try:
                    header = camera.getImageBuffer(buf)
                except kge.GEVGrabError as ex:
                    logger.error("%s", ex.missing_returned_value)
                else:
                    width = header.SizeX
                    height = header.SizeY
                    dsize=(width*360//height, 360) # (w,h) to 360p
                    grabbed_img = np.ctypeslib.as_array(buf).reshape(height,width)
                    display_img = cv2.resize(grabbed_img, dsize=dsize,
                                             interpolation=cv2.INTER_AREA)
                    cv2.imshow(repr(camera), display_img)

            key = cv2.waitKey(1)
            if key != -1:
                logger.info("pressed key: %d", key)
            if key in range(32, 128):
                cv2.destroyAllWindows()
                return None
    finally:
        for c in cameras:
            c.close()


if __name__ == "__main__":
    setting_logger()
    exit(demo())
