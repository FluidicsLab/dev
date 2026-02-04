#ifndef KOWAGIGEVISIONLIB_STRUCTURES_H
#define KOWAGIGEVISIONLIB_STRUCTURES_H
#include "types.h"
#include "constant_values.h"


typedef struct _FeatureList FeatureList;
typedef FeatureList* FeatureListPtr;
struct _FeatureList {
    FeatureListPtr Next;
    DWORD Index;
    char* Name;
    //    char *DisplayName;
    //    char *ToolTip;
    BYTE Type;
    BYTE Level;
    //    BYTE Visibility;
};

typedef struct
{
    BYTE Type;
    INT64 Min;
    INT64 Max;
    DWORD OnValue;
    DWORD OffValue;
    WORD AccessMode;
    WORD Representation;
    DWORD Inc;
    DWORD CommandValue;
    DWORD Length;
    BYTE EnumerationCount;
    BYTE Visibility;
    double FloatMin;
    double FloatMax;
    double FloatInc;
    BYTE IsImplemented;
    BYTE IsAvailable;
    BYTE IsLocked;
    BYTE Sign;
    DWORD Address;
    BYTE DisplayNotation;
    BYTE DisplayPrecision;
    BYTE InvalidatorCount;
    INT64 PollingTime;
} FEATURE_PARAMETER;

typedef struct
{
    DWORD IP;
    BYTE manuf[32];
    BYTE model[32];
    BYTE version[32];
    DWORD AdapterIP;
    DWORD AdapterMask;
    BYTE Mac[6];
    DWORD subnet;
    DWORD gateway;
    char adapter_name[MAX_ADAPTER_NAME_LEN + 4];
    BYTE serial[16];
    BYTE userdef_name[16];
    BYTE status;
} DEVICE_PARAM;

typedef struct
{
    DWORD AdapterIP;
    DWORD AdapterMask;
    char AdapterName[MAX_ADAPTER_NAME_LEN + 4];
} ADAPTER_PARAM;

typedef struct
{
    BYTE Count;
    ADAPTER_PARAM param[CAMERA_COUNT_DISCOVERY];
} ENUMERATE_ADAPTER;

typedef struct
{
    BYTE Count;
    DEVICE_PARAM param[CAMERA_COUNT_DISCOVERY];
} DISCOVERY;

typedef struct
{
    DWORD IP_CANCam;
    WORD PortData;
    WORD PortCtrl;
    DWORD AdapterIP;
    DWORD AdapterMask;
    char adapter_name[MAX_ADAPTER_NAME_LEN + 4];
    WORD PortMessage;
} CONNECTION;

typedef struct
{
    BYTE receive_count;
    BYTE transmit_count;
    BYTE transmit_buffer_full;
    BYTE transmit_buffer_empty;
    BYTE reveice_buffer_full;
    BYTE reveice_data_available;
} CLINK_STATUS;

typedef struct
{
    DWORD cc_heartbeat_timeout;
    DWORD cc_timeout;
    BYTE cc_retry;
    DWORD sc_timeout;
    BYTE sc_packet_resend;
    DWORD sc_image_wait_timeout;
} CHANNEL_PARAMETER;

typedef struct
{
    INT64 FrameCounter;
    ULONGLONG TimeStamp;
    DWORD PixelType;
    DWORD SizeX;
    DWORD SizeY;
    DWORD OffsetX;
    DWORD OffsetY;
    WORD PaddingX;
    WORD PaddingY;
    INT  MissingPacket;
    WORD PayloadType;
    DWORD ChunkDataPayloadLength;
    DWORD ChunkLayoutId;
} IMAGE_HEADER, * pIMAGE_HEADER;

typedef struct
{
    WORD  EventID;
    WORD  StreamChannelIndex;
    ULONGLONG  BlockID;
    ULONGLONG  TimeStamp;
    BYTE* Data;
    WORD DataLength;
} MESSAGECHANNEL_PARAMETER;

typedef struct
{
    DWORD DeviceKey;
    DWORD GroupKey;
    DWORD GroupMask;
} ACTION_KEYS;

typedef BYTE(WINAPI* DISCOVERY_CALLBACK_FUNC)(int s_cnt, DEVICE_PARAM* dparam);
typedef BYTE(WINAPI* MESSAGECHANNEL_CALLBACK_FUNC)(KOWAGIGEVISION_CAMNR cam_nr, MESSAGECHANNEL_PARAMETER mcparam);
typedef BYTE(WINAPI* ERROR_CALLBACK_FUNC)(KOWAGIGEVISION_CAMNR cam_nr, char* error_str, BYTE detailed_log);
typedef BYTE(WINAPI* SECURE_TRANSFER_CALLBACK_FUNC)(KOWAGIGEVISION_CAMNR cam_nr);
typedef BYTE(WINAPI* READ_WRITE_MEM_CALLBACK_FUNC)(KOWAGIGEVISION_CAMNR cam_nr, int s_cnt);
typedef void(WINAPI* ACQUISITION_CALLBACK_FUNC)(KOWAGIGEVISION_CAMNR cam_nr, const IMAGE_HEADER* image_header, const void* data, size_t datalen);
// return
//     0: continue to wait acknowledge.
//     1: decontinue to waiting, and instantly return.
typedef BYTE(WINAPI* ACTION_ACKNOWLEDGE_CALLBACK_FUNC)(KOWAGIGEVISION_CAMNR cam_nr, DWORD fromip, WORD status, void* param);

#define GEV_INVALID_CAMNR ((KOWAGIGEVISION_CAMNR)0)

#endif//KOWAGIGEVISIONLIB_STRUCTURES_H
