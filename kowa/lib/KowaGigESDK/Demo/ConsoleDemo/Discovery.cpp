/*****************************************************************************/
/*
 *  Discovery.cpp -- discovery functions for sample application
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

#include "Discovery.h"
#include "Utils.h"

#ifdef DISCOVER_CALLBACK

std::vector<DEVICE_PARAM *> DiscoveryList;
BYTE discovery_device = 1;

BYTE WINAPI discovery_callback_func(int s_cnt, DEVICE_PARAM *dparam)
{
  struct sockaddr_in addr;

  if(dparam)
  {
    DEVICE_PARAM *lDevParam = new DEVICE_PARAM;
    memcpy(lDevParam, dparam, sizeof(DEVICE_PARAM));

    // Devices returned from the callback didn't have their status checked.
    // This can you do with the GEVCheckDeviceStatus function
    if(lDevParam->status == DISCOVERY_STATUS_NOT_CHECKED)
      GEVCheckDeviceStatus(lDevParam->AdapterIP, lDevParam->AdapterMask, lDevParam->IP, &lDevParam->status, 200, 0);

    DiscoveryList.push_back(lDevParam);

    printf("\n\n");
    printf("[INFO] - Device: %d\n", discovery_device++);

    printf("[INFO] - %s\n", lDevParam->manuf);
    printf("[INFO] - %s\n", lDevParam->model);
    printf("[INFO] - %s\n", lDevParam->version);

    addr.sin_addr.s_addr = lDevParam->IP;
    printf("[INFO] - IP: %s\n", inet_ntoa(addr.sin_addr));

    addr.sin_addr.s_addr = lDevParam->AdapterIP;
    printf("[INFO] - Adapter-IP: %s\n", inet_ntoa(addr.sin_addr));

    addr.sin_addr.s_addr = lDevParam->AdapterMask;
    printf("[INFO] - Adapter-Mask: %s\n", inet_ntoa(addr.sin_addr));

    printf("[INFO] - Adapter-Name: %s\n", lDevParam->adapter_name);

    printf("[INFO] - Status: %d\n", lDevParam->status);
  }

  printf("[INFO] - Process %d %%\n", s_cnt);

  return(0);
}
#endif

int Discovery(CONNECTION *con)
{
  WORD error;
#ifndef DISCOVER_CALLBACK
  DISCOVERY *dis = NULL;
  struct sockaddr_in addr;
#endif
  int i;
  BYTE device = 1;

#ifdef DISCOVER_CALLBACK
  discovery_device = 1;

  // discovery devices, use auto port
  error = GEVDiscovery(NULL, discovery_callback_func, 200, 0, 0);
  if(error)
  {
    printf("[ERROR] - GEVDiscovery error: %04X\n",error);
    return(1);
  }

  // if no device is found, exit the application
  if(DiscoveryList.size() == 0)
  {
    printf("[INFO] - No GigE device found.\n");
    return(1);
  }

  printf("[INFO] - Device count: %zd\n", DiscoveryList.size());
#else

  dis = (DISCOVERY *)malloc(sizeof(DISCOVERY));
  if (dis == NULL)
    return(1);

  // discovery devices, auto port
  error = GEVDiscovery(dis, NULL, 200, 0, 0);
  if(error)
  {
    printf("[ERROR] - GEVDiscovery error: %04X\n",error);
    return(1);
  }

  // if no device is found, exit the application
  if(dis->Count == 0)
  {
    printf("[INFO] - No GigE device found.\n");
    return(1);
  }

  printf("[INFO] - Count: %d\n", dis->Count);

  // print out the information of found devices
  for(i = 0;i < dis->Count;i++)
  {
    printf("\n\n");
    printf("[INFO] - Device: %d\n", i + 1);

    printf("[INFO] - %s\n", dis->param[i].manuf);
    printf("[INFO] - %s\n", dis->param[i].model);
    printf("[INFO] - %s\n", dis->param[i].version);

    addr.sin_addr.s_addr = dis->param[i].IP;
    printf("[INFO] - IP: %s\n", inet_ntoa(addr.sin_addr));

    addr.sin_addr.s_addr = dis->param[i].AdapterIP;
    printf("[INFO] - Adapter-IP: %s\n", inet_ntoa(addr.sin_addr));

    addr.sin_addr.s_addr = dis->param[i].AdapterMask;
    printf("[INFO] - Adapter-Mask: %s\n", inet_ntoa(addr.sin_addr));

    printf("[INFO] - Adapter-Name: %s\n", dis->param[i].adapter_name);

    printf("[INFO] - Status: %d\n", dis->param[i].status);
  }
#endif

  // if we found more than one device, select the device you want to use
#ifdef DISCOVER_CALLBACK
  if(DiscoveryList.size() > 1)
#else
  if(dis->Count > 1)
#endif
  {
    printf("Select Device: ");
    if(scanf("%d", &i))
      device = i;
    printf("device: %d\n", device);
#if defined( __GNUC__ )
    i = getch();
#else
    fflush(stdin);
#endif
  }

#ifdef DISCOVER_CALLBACK

  DEVICE_PARAM *lDevParam = DiscoveryList.at((device - 1));

  // set CONNECTION parameter for GEVInit function
  con->AdapterIP = lDevParam->AdapterIP;              // network adapter ip address
  con->AdapterMask = lDevParam->AdapterMask;          // network  adapter mask
  con->IP_CANCam = lDevParam->IP;                     // device ip address
  con->PortCtrl = 49149;                              // control port, set 0 to port than automatic port is use
  con->PortData = 49150;                              // stream port, set 0 to port than automatic port is use
  con->PortMessage = 49151;                           // message port, set 0 to port than automatic port is use
  strcpy(con->adapter_name, lDevParam->adapter_name); // name of network adapter

  DiscoveryList.clear();
#else
  // set CONNECTION parameter for GEVInit function
  con->AdapterIP = dis->param[device - 1].AdapterIP;             // network adapter ip address
  con->AdapterMask = dis->param[device - 1].AdapterMask;         // network  adapter mask
  con->IP_CANCam = dis->param[device - 1].IP;                    // device ip address
  con->PortCtrl = 49149;                                         // control port, set 0 to port than automatic port is use
  con->PortData = 49150;                                         // stream port, set 0 to port than automatic port is use
  con->PortMessage = 49151;                                      // message port, set 0 to port than automatic port is use
  strcpy(con->adapter_name,dis->param[device - 1].adapter_name); // name of network adapter

  if(dis)
    free(dis);
#endif

  return(0);
}
