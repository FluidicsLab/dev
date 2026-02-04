/*****************************************************************************/
/*
 *  Stream.cpp -- stream functions for sample application
 *
 *****************************************************************************
 * This sample demonstrates how to use the GigE Vision library to
 * discover and open a GigE Vision device. Reading and writing devices registers
 * and stream images is also demonstrated.
 * For reference of the uses library function, refer to its documentation.
 * The code is delivered "as is" without any warranty and can be freely used
 * for own applications.
 */
/*****************************************************************************/
#if defined( __GNUC__ )
#include <termios.h>
#include <fcntl.h>
#include <pthread.h>
#include <inttypes.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <sys/errno.h>
#else
#include "stdafx.h"
#include <Winsock2.h>
#include <windows.h>
#include <iphlpapi.h>
#include <conio.h>
#include <direct.h>
#endif

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <deque>
#include <vector>

#include "KowaGigEVisionLib.h"   // include KowaGigEVisionLib header file

#include "Stream.h"
#include "Utils.h"

// global variables
DEVICE_PARAMS DeviceParams;

#if defined( __GNUC__ )
pthread_t ThreadAcquisition;
#else
HANDLE ThreadAcquisition;
#endif

// acquisition thread
#if defined( __GNUC__ )
void* AcquisitionThreadProc(void* lpv)
#else
DWORD WINAPI AcquisitionThreadProc(LPVOID lpv)
#endif
{
  IMAGE_HEADER img_header;
  INT64 dw64;
  DWORD width, height, img_size;
  BYTE bpp;
  DWORD pixelFormat;
  WORD error;
  char l_str[150];
  static PDEVICE_PARAMS dparams;
  BYTE *ppixel[BUFFER_COUNT];
  DWORD acquisition_counter = 0;
  DWORD img_counter = 0;
#ifdef RING_BUFFER
  WORD index = 0;
  int i;
#endif

  ppixel[0] = NULL;

  // get thread parameter
  dparams = (PDEVICE_PARAMS)lpv;

  // get current image width from the device
  error = GEVGetFeatureInteger(dparams->Device, (char *)"Width", &dw64);
  if(error)
  {
    get_error(dparams->Device, error,l_str);
    printf("[ERROR] - GEVGetFeatureInteger(Width) error: %s\n",l_str);
    goto END;
  }
  width = (DWORD)dw64;

  // get current image height from the device
  error = GEVGetFeatureInteger(dparams->Device, (char *)"Height", &dw64);
  if(error)
  {
    get_error(dparams->Device, error,l_str);
    printf("[ERROR] - GEVGetFeatureInteger(Height) error: %s\n",l_str);
    goto END;
  }
  height = (DWORD)dw64;

  // get current image pixel format from the device
  error = GEVGetFeatureInteger(dparams->Device, (char *)"PixelFormat", &dw64);
  if(error)
  {
    get_error(dparams->Device, error,l_str);
    printf("[ERROR] - GEVGetFeatureInteger(PixelFormat) error: %s\n",l_str);
    goto END;
  }
  pixelFormat = (DWORD)dw64;
  bpp = (BYTE)PFNC_PIXEL_SIZE(pixelFormat);

  // printf out the image information is done by the KowaGigEVisionLib (error_callback_func function)

  // get current image size (payload size) from the device
  error = GEVGetFeatureInteger(dparams->Device, (char *)"PayloadSize", &dw64);
  if(error)
  {
    get_error(dparams->Device, error,l_str);
    printf("[ERROR] - GEVGetFeatureInteger(PayloadSize) error: %s\n",l_str);
    goto END;
  }
  img_size = (int)dw64;

#ifdef RING_BUFFER
  GEVSetBufferCount(dparams->Device,BUFFER_COUNT);

  // allocate memory for the user ring buffer, ringbuffer is handled by user application
  for(i = 0;i < BUFFER_COUNT;i++)
  {
    ppixel[i] = (BYTE *)malloc(img_size);
    GEVSetRingBuffer(dparams->Device, i, ppixel[i]);  //used by function GEVGetImageRingBuffer
  }
#else
  // allocate memory for the image, ringbuffer is handled directly in library
  ppixel[0] = (BYTE *)malloc(img_size);               //used by function GEVGetImageBuffer
#endif

  // get AcquisitionMode of the device
  error = GEVGetFeatureEnumeration(dparams->Device, (char *)"AcquisitionMode", l_str, sizeof(l_str));
  if (error)
  {
    printf("[ERROR] - AcquisitionMode node error or not exist.\n");
    acquisition_counter = 0;
  }
  else
  {
    if (strstr(l_str, "Continuous") != NULL)
      acquisition_counter = 0;
    else if (strstr(l_str, "SingleFrame") != NULL)
      acquisition_counter = 1;
    else if (strstr(l_str, "MultiFrame") != NULL)
    {
      error = GEVGetFeatureInteger(dparams->Device, (char *)"AcquisitionFrameCount", &dw64);
      if (error)
      {
        printf("[ERROR] - AcquisitionFrameCount node error or not exist.\n");
        goto END;
      }
      acquisition_counter = (DWORD)dw64;
    }
    else
      acquisition_counter = 0;
  }

  // start acquisition
  error = GEVAcquisitionStart(dparams->Device, acquisition_counter);
  if(error)
  {
    get_error(dparams->Device, error,l_str);
    printf("[ERROR] - GEVAcquisitionStart error: %s\n",l_str);
    goto END;
  }

  while ( !dparams->Kill )
  {
    // get image and header info
#ifdef RING_BUFFER
    error = GEVGetImageRingBuffer(dparams->Device,&img_header, &index);
#else
    error = GEVGetImageBuffer(dparams->Device,&img_header, ppixel[0]);
#endif
    if((error) && (error != GEV_STATUS_GRAB_ERROR))
    {
      get_error(dparams->Device, error,l_str);
      printf("[ERROR] - GEVGetImage: %s\n",l_str);
    }
    else
    {
      // printf out image information
#ifdef RING_BUFFER
#if defined( __GNUC__ )
      printf("[INFO] - Image: %"PRId64", Index: %d, Missing Packets: %d\n",img_header.FrameCounter, index,img_header.MissingPacket);
#else
      printf("[INFO] - Image: %lld, Index: %d, Missing Packets: %d\n", img_header.FrameCounter, index, img_header.MissingPacket);
#endif
#else
#if defined( __GNUC__ )
      printf("[INFO] - Image: %" PRId64 ", Missing Packets: %d\n", img_header.FrameCounter, img_header.MissingPacket);
#else
      printf("[INFO] - Image: %lld, Missing Packets: %d\n", img_header.FrameCounter, img_header.MissingPacket);
#endif

      if (img_header.PayloadType == PAYLOAD_TYPE_JPEG)
      {
        FILE* hfile;

        printf("PixelType: %08X\n", img_header.PixelType);
        printf("PayloadType: %04X\n", img_header.PayloadType);
        // jpeg file size
        printf("jpeg file size: %04X\n", img_header.ChunkDataPayloadLength);


        if (!dir_exists("images"))
          create_dir((char *)"images");

#if defined( __GNUC__ )
        sprintf(l_str, "images/image_%d.jpg", img_counter);
#else
        sprintf(l_str, "images\\image_%d.jpg", img_counter);
#endif
        if ((hfile = fopen(l_str, "w+b")) == NULL)
          goto END;

        if (fwrite((unsigned char*)ppixel[0], img_header.SizeY, 1, hfile) == 0)
          goto END;

        fclose(hfile);
      }
#endif

#ifdef RING_BUFFER
      // queued user buffer
      GEVQueueRingBuffer(dparams->Device, index);
#endif

      img_counter++;
    }

    if (acquisition_counter)
    {
      if (img_counter >= acquisition_counter)
        dparams->Kill = TRUE;
    }
  }

  // stop acquisition
  error = GEVAcquisitionStop(dparams->Device);
  if (error)
  {
    get_error(dparams->Device, error,l_str);
    printf("[ERROR] - GEVAcquisitionStop: %s\n",l_str);
    goto END;
  }

  // save last image as bitmap to disk
  printf("[INFO] - Save last image to disk...\n");
#ifdef RING_BUFFER
  error = save_bmp((char *)"image.bmp", width, height, bpp ,ppixel[index]);
#else
  error = save_bmp((char *)"image.bmp", width, height, bpp ,ppixel[0]);
#endif
  if(error)
    printf("[ERROR] - Error %d save image.bmp\n",error);
  else
    printf("[INFO] - Save image ok\n");

END:

#ifdef RING_BUFFER
  // free user ring buffer memory
  if(ppixel[0])
  {
    for(i = 0;i < BUFFER_COUNT;i++)
      free(ppixel[i]);
  }
  GEVReleaseRingBuffer(dparams->Device);
#else
  // free image memory
  if(ppixel[0])
    free(ppixel[0]);
#endif

  return(0);
}
