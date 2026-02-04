/*****************************************************************************/
/*
 *    ConsoleDemo.cpp -- sample application to use discover, open, configure
 *    					and stream from a GigE Vision device
 *
 *****************************************************************************
 * This sample demonstrates how to use the KowaGigEVisionlibrary to
 * discover and open a GigE Vision device. Reading and writing devices registers
 * and stream images is also demonstrated.
 * For reference of the uses Kowa library function, refer to its documentation.
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
#include <sys/types.h>
#include <sys/stat.h>
#else
#pragma comment(lib, "WSock32.lib")
#define _WINSOCK_DEPRECATED_NO_WARNINGS
#include <Winsock2.h>
#include <windows.h>
#include <iphlpapi.h>
#include <conio.h>
#include <direct.h>
#include "stdafx.h"
#endif


#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

#include "KowaGigEVisionLib.h"   // include KowaGigEVisionLib header file

#include "Utils.h"
#include "Discovery.h"
#include "Device.h"
#include "Stream.h"


// main program
int main(int argc, char* argv[])
{
  CONNECTION con;
  BYTE device = 1;
#if !defined( __GNUC__ )
  DWORD dw;
#endif

  // discovery devices
  if (Discovery(&con) == 1)
    return(0);

  // init GigE device
  if (InitDevice(device,&con) == 1)
    goto END;

  printf("[INFO] - Start acquisition continuous mode with any key.\n");
  printf("[INFO] - Cancel acquisition with any key.\n");
#if defined( __GNUC__ )
  getch();
#else
  _getch();
#endif

  // start acquisition thread
  DeviceParams.Kill = FALSE;
  DeviceParams.Device = device;

#if defined( __GNUC__ )
  pthread_create(&ThreadAcquisition,0,AcquisitionThreadProc,(void*)&DeviceParams);
#else
  ThreadAcquisition = CreateThread(NULL,0,AcquisitionThreadProc, &DeviceParams,0, &dw);
  if(ThreadAcquisition == NULL)
    goto END;
#endif

  // run acquisition as long as no key was pressed
  while(!_kbhit())
      Sleep(0);

#if defined( __GNUC__ )
  getch();
#else
  _getch();
#endif

  // stops acquisition thread
  DeviceParams.Kill = TRUE;

#if defined( __GNUC__ )
  // wait end thread
  pthread_join(ThreadAcquisition,0);
  ThreadAcquisition = 0;
#else
  // wait end thread
  if(WaitForSingleObject(ThreadAcquisition, 2000) != WAIT_OBJECT_0)
    printf("timeout close thread 1\n");
  CloseHandle( ThreadAcquisition );
#endif

END:

  printf("[INFO] - Exit application with any key.\n");

#if defined( __GNUC__ )
  getch();
#else
  _getch();
#endif

  // close device
  CloseDevice(device);
  return 0;
}
