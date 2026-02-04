/*****************************************************************************/
/*
 *  Device.h -- device header for sample application
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
#ifndef __DEVICE_H
#define __DEVICE_H

// if you want to use filter driver, enable USE_FILTER_DRIVER define
#define USE_FILTER_DRIVER  1

int InitDevice(BYTE device,CONNECTION *con);
int CloseDevice(BYTE device);

#endif
