/*****************************************************************************/
/*
 *  Device.cpp -- device functions for sample application
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

#include "Device.h"
#include "Utils.h"

bool DeviceInit = false;
bool StreamChannelInit = false;
bool FilterDriverInit = false;

int InitDevice(BYTE device, CONNECTION *con)
{
  WORD error;
  char l_str[50];

  // initialization of the GigE device
  // error_callback_func, this function receives information, warning and error strings from the KowaGigEVisionLib
  error = GEVInit(device, con, error_callback_func, 0,EXCLUSIVE_ACCESS);
  if(error)
  {
    get_error(device, error,l_str);
    printf("[ERROR] - GEVInit: %s\n",l_str);
    return(1);
  }
  DeviceInit = true;

  // enable this function to set the specific log outputs from the KowaGigEVisionLib (error_callback_func)
  // GEVSetDetailedLog(device, DETAILED_LOG_INFO | DETAILED_LOG_WARNING | DETAILED_LOG_ERROR);

#ifdef _DEBUG
    // if debug mode is enabled, set heartbeat to 10 seconds (needed for single-step execution)
    error = GEVSetHeartbeatRate(device, 10000);
    if(error)
    {
      get_error(device, error,l_str);
      printf("GEVSetHeartbeatRate error: %s\n",l_str);
      return(1);
    }
#endif

  // initialization xml parser
  error = GEVInitXml(device);
  if(error)
  {
    get_error(device, error,l_str);
    printf("[ERROR] - GEVInitXml error: %s\n",l_str);
    return(1);
  }

  // set message channel callback function
  error = GEVSetMessageChannelCallback(device, msg_callback_func);
  if(error == GEV_STATUS_NOT_SUPPORTED)
  {
    printf("[INFO] - Message channel not Supported\n");
  }

  // open stream channel
  error = GEVOpenStreamChannel(device, con->AdapterIP, con->PortData,0 );
  if(error)
  {
    get_error(device, error,l_str);
    printf("[ERROR] - GEVOpenStreamChannel error: %s\n",l_str);
    return(1);
  }
  StreamChannelInit = true;

  // disable packet resend
  error = GEVSetPacketResend(device, 0);
  if(error)
  {
    get_error(device, error,l_str);
    printf("[ERROR] - GEVSetPacketResend: %s\n",l_str);
  }

  // set stream channel packet delay to 500 (default 0)
  error = GEVSetFeatureInteger(device,(char *)"GevSCPD", 500);
  if(error)
  {
    get_error(device, error,l_str);
    printf("[ERROR] - GEVSetFeatureInteger(GevSCPD): %s\n",l_str);
  }

  // find maximal packet size
  FEATURE_PARAMETER f_param;

  // get stream channel packet size parameters from xml node GevSCPSPacketSize
  error = GEVGetFeatureParameter(device,(char *)"GevSCPSPacketSize",&f_param);
  if(error)
  {
    get_error(device, error,l_str);
    printf("[ERROR] - GevSCPSPacketSize: %s\n",l_str);
  }
  else
  {
    // check parameters for plausibility
    WORD ps_max, ps_min, ps_inc, packet_size;

    // calculate min, max and increment of packet size
    if(f_param.Min == -1)
      ps_min = 0;
    else
      ps_min = (WORD)f_param.Min;

    if(f_param.Max == -1)
      ps_max = 20000;
    else
      ps_max = (WORD)f_param.Max;

    ps_inc = (WORD)f_param.Inc;
    if(ps_inc == 1)
      ps_inc = 4;

    // test maximum achievable packet size
    error = GEVTestFindMaxPacketSize(device, &packet_size, ps_min, ps_max, ps_inc);
    if(error)
    {
      get_error(device, error,l_str);
      printf("[ERROR] - GEVTestFindMaxPacketSize: %s\n",l_str);
    }
    printf("[INFO] - Find maximal packet size: %d.\n", packet_size);
  }

#ifdef USE_FILTER_DRIVER
  // initialization �f the filter driver, must be installed
  error = GEVInitFilterDriver(device);
  if(error)
  {
    get_error(device, error,l_str);
    printf("[ERROR] - GEVInitFilterDriver: %s\n",l_str);
    return(1);
  }

  unsigned char version_major, version_minor;
  error = GEVGetFilterDriverVersion(device,&version_major, &version_minor);
  if(error)
  {
    get_error(device, error,l_str);
    printf("[ERROR] - GEVGetFilterDriverVersion: %s\n",l_str);
    return(1);
  }
  else
  {
    printf("[INFO] Filter driver version %d.%d.%d\n", version_major, version_minor >> 4, version_minor & 0x0f);
    FilterDriverInit = true;
  }
#endif

  return(0);
}

int CloseDevice(BYTE device)
{
  // close stream channel
  if(StreamChannelInit)
    GEVCloseStreamChannel(device);

#ifdef USE_FILTER_DRIVER
  // close filter driver
  if(FilterDriverInit)
    GEVCloseFilterDriver(device);
#endif

  // close GigE device
  if(DeviceInit )
    GEVClose(device);

  return(0);
}
