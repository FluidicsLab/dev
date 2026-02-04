/*****************************************************************************/
/*
 *  Discovery.h -- discovery header for sample application
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
#ifndef __DISCOVERY_H
#define __DISCOVERY_H

// if you want to get devices over the discovery callback function, enable DISCOVER_CALLBACK define
// #define DISCOVER_CALLBACK 1

#ifdef DISCOVER_CALLBACK
BYTE WINAPI discovery_callback_func(int s_cnt,DEVICE_PARAM *dparam);
#endif

int Discovery(CONNECTION *con);

#endif
