/* types.h -- Types header
 *
 * Version: 1.0.0 Date: 15.12.2021
 */
#ifndef KOWAGIGEVISIONLIB_TYPES_H
#define KOWAGIGEVISIONLIB_TYPES_H
#include "defines.h"
#include <stdint.h>
#include <errno.h>

#if 0
typedef int gev_bool;
typedef uint16_t gev_error_t;
//enum get_error {
//};
//typedef enum get_error gev_error_t;

#endif // for next version


// Legacy types. (deprecated)
// compatible to Win32API
#ifndef GEV_ENVIRON_WINDOWS
// Note: compatible to Win32API
#define WINAPI GEV_API
#include <sys/types.h>
typedef uint8_t BYTE;
typedef uint16_t WORD;
typedef uint32_t DWORD;
typedef uint64_t UINT64;
typedef int64_t INT64;

typedef uint64_t ULONGLONG;
typedef int32_t INT;

#ifdef __APPLE__
typedef signed char BOOL;
#else
typedef int BOOL;
#endif

typedef u_int32_t os_delay_t;
typedef u_int32_t os_time_t;
#define OS_TIME_UNDEF 0
#define OsTimeDefined(t) (t)
#define OS_TIME_DEWRAP ((u_int64_t)(1ULL << 32))
typedef u_int32_t os_frequency_t;
#define OS_TIME_ONE_SECOND 1000
#ifndef __cplusplus
#define false FALSE
#define true TRUE
#ifndef TRUE
#define TRUE 1
#endif
#ifndef FALSE
#define FALSE 0
#endif
#endif


#else //GEV_ENVIRON_WINDOWS
#include <windows.h>
// Note: compatible to Linux kernel
typedef BYTE u_int8_t;
typedef WORD u_int16_t;
typedef DWORD u_int32_t;
typedef INT64 int64_t;
typedef UINT64 u_int64_t;
typedef INT int32_t;
#define KOWAGIGE_STRUCTURES_PACKING_NEEDED

typedef DWORD os_delay_t;
typedef LARGE_INTEGER os_time_t;
#define OS_TIME_UNDEF (os_time_t) {0}
#define OsTimeDefined(t) ((t).QuadPart)
typedef u_int64_t os_frequency_t;
#ifndef __cplusplus
// true/false
#include <stdbool.h>
#endif
#endif//GEV_ENVIRON_WINDOWS else

//! internal camera identifier, from 0 to CAMERA_COUNT-1, ready for array indexing.
typedef u_int8_t gev_camno_t;
//! camera identifier, ranging from 1 to CAMERA_COUNT (included)
typedef u_int8_t KOWAGIGEVISION_CAMNR;

typedef WORD os_error_t;
#define OS_SEND_FAILURE errno
#define OS_ALLOC_FAILURE ENOMEM // GEV_STATUS_CANNOT_ALLOC_MEMORY
#define OS_OK 0 // GEV_STATUS_SUCCESS
typedef struct tagCANCAMPARAM gev_kernel_context_t;

typedef struct _IMAGE_BUFFER IMAGE_BUFFER;

#endif//KOWAGIGEVISIONLIB_TYPES_H
