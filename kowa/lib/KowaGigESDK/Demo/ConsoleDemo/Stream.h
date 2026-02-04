/*****************************************************************************/
/*
 *  Stream.h -- stream header for sample application
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
#ifndef __STREAM_H
#define __STREAM_H

// if you want to use user buffer handling, enable RING_BUFFER define
//#define RING_BUFFER  1
#define BUFFER_COUNT 4

// Acquisition thread parameter
typedef struct
{
  BOOL Kill;
  BYTE Device;

}DEVICE_PARAMS, *PDEVICE_PARAMS;


// global variables
extern DEVICE_PARAMS DeviceParams;

#if defined( __GNUC__ )
extern pthread_t ThreadAcquisition;
#else
extern HANDLE ThreadAcquisition;
#endif

#if defined( __GNUC__ )
void* AcquisitionThreadProc(void* lpv);
#else
DWORD WINAPI AcquisitionThreadProc(LPVOID lpv);
#endif


#endif
