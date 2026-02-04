#pragma once

#ifndef KOWA_EXTERNAL_CONTROL_LIB_H
#define KOWA_EXTERNAL_CONTROL_LIB_H

//#include "KowaGigEVisionLib.h"
#include <stdint.h>

#ifdef  KOWAEXTERNALCONTROLLIB_EXPORTS
#if   defined(_WIN32)
#define KOWAEXTERNALCONTROLLIB_API __declspec(dllexport)
#elif defined(__GNUC__)
#define KOWAEXTERNALCONTROLLIB_API __attribute__((visibility))
#endif//envirion
#else
#if   defined(_WIN32)
#define KOWAEXTERNALCONTROLLIB_API __declspec(dllimport)
#elif defined(__GNUC__)
#define KOWAEXTERNALCONTROLLIB_API
#endif//envirion
#endif//KOWAEXTERNALCONTROLLIB_EXPORTS

#ifdef __cplusplus
extern "C"
{
#endif

    enum phase_type {
        pt_full_step = 0,
        pt_half_step = 1,
    };

    enum origin_state_type {
      ost_not_implemented = 0,
      ost_complete = 1,
      ost_operating = 2,
      ost_error = 3,
    };

#pragma pack(push, 1)
    struct RemoteFocusInfo {
      BYTE flags;
      BYTE is_busy;
      short step_count;
      BYTE origin_state;
      BYTE slit_location;
    };
#pragma pack(pop)

    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusGetFWVersion(BYTE camera_number, DWORD* fw_ver);

    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusAddStepCount(BYTE camera_number, DWORD step_count);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusSubStepCount(BYTE camera_number, DWORD step_count);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusGetStepCount(BYTE camera_number, short* step_count);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusSetOrigin(BYTE camera_number);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusGetOriginState(BYTE camera_number, enum origin_state_type* origin_state);

    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusForceStop(BYTE camera_number);

// pps: pulse per second.
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusSetPPS(BYTE camera_number, DWORD pps);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusGetPPS(BYTE camera_number, DWORD* pps);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusSetMotorPhase(BYTE camera_number, enum phase_type motor_phase);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusGetMotorPhase(BYTE camera_number, enum phase_type* motor_phase);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusSetCanMotorSleep(BYTE camera_number, DWORD motor_state);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusGetCanMotorSleep(BYTE camera_number, DWORD* motor_state);

    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusGetInfo(BYTE camera_number, struct RemoteFocusInfo* info);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusIsMotorBusy(BYTE camera_number, DWORD* busy);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusGetSlitLocation(BYTE camera_number, DWORD* slit_location);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI RemoteFocusGetFlags(BYTE camera_number, DWORD* flags);


    KOWAEXTERNALCONTROLLIB_API WORD WINAPI PwmSetParameter(BYTE camera_number, DWORD mode, DWORD delay, DWORD width, DWORD duty);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI PwmGetParameter(BYTE camera_number, DWORD* mode, DWORD* delay, DWORD* width, DWORD* duty);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI PwmSetManualCtrl(BYTE camera_number, DWORD enable);
    KOWAEXTERNALCONTROLLIB_API WORD WINAPI PwmGetManualCtrl(BYTE camera_number, DWORD* enable);

#ifdef __cplusplus
}
#endif

typedef size_t COM_HANDLE;
#endif//KOWA_EXTERNAL_CONTROL_LIB_H
