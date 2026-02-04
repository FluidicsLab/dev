#ifndef KOWAGIGEVISIONLIB_FUNCTIONS_H
#define KOWAGIGEVISIONLIB_FUNCTIONS_H
#include "defines.h"
#include "types.h"
#include "constant_values.h"
#include "structures.h"

#ifdef __cplusplus
extern "C" {
#endif

    // *************** General functions *********************
    GEV_EXPORT WORD WINAPI GEVDiscovery(DISCOVERY* dis, DISCOVERY_CALLBACK_FUNC c_func, DWORD d_timeout, BOOL ignore_subnet, WORD port);
    GEV_EXPORT WORD WINAPI GEVEnumerateAdapters(ENUMERATE_ADAPTER* adapter);
    GEV_EXPORT WORD WINAPI GEVDiscoveryAdapter(DISCOVERY* dis, ADAPTER_PARAM* adapter, DISCOVERY_CALLBACK_FUNC c_func, DWORD d_timeout, BOOL ignore_subnet, WORD port);
    GEV_EXPORT WORD WINAPI GEVInit(KOWAGIGEVISION_CAMNR cam_nr, CONNECTION* con, ERROR_CALLBACK_FUNC error_func, BYTE save_xml, BYTE open_mode);
    GEV_EXPORT WORD WINAPI GEVInitEx(KOWAGIGEVISION_CAMNR* cam_nr, CONNECTION* con, ERROR_CALLBACK_FUNC error_func, BYTE save_xml, BYTE open_mode);
    GEV_EXPORT WORD WINAPI GEVClose(KOWAGIGEVISION_CAMNR cam_nr);

    GEV_EXPORT WORD WINAPI GEVOpenStreamChannel(KOWAGIGEVISION_CAMNR cam_nr, DWORD adapterip, WORD port, DWORD multicast);
    GEV_EXPORT WORD WINAPI GEVCloseStreamChannel(KOWAGIGEVISION_CAMNR cam_nr);

    GEV_EXPORT WORD WINAPI GEVInitFilterDriver(KOWAGIGEVISION_CAMNR cam_nr);
    GEV_EXPORT WORD WINAPI GEVCloseFilterDriver(KOWAGIGEVISION_CAMNR cam_nr);

    GEV_EXPORT WORD WINAPI GEVWriteRegister(KOWAGIGEVISION_CAMNR cam_nr, DWORD cmd, BYTE cnt, const DWORD pptr[]);
    GEV_EXPORT WORD WINAPI GEVReadRegister(KOWAGIGEVISION_CAMNR cam_nr, DWORD cmd, BYTE cnt, DWORD pptr[]);

    GEV_EXPORT WORD WINAPI GEVWriteMemory(KOWAGIGEVISION_CAMNR cam_nr, DWORD maddr, DWORD len, const void* pptr);
    GEV_EXPORT WORD WINAPI GEVReadMemory(KOWAGIGEVISION_CAMNR cam_nr, DWORD maddr, DWORD len, void* pptr);

    GEV_EXPORT WORD WINAPI GEVSetReadWriteMemoryCallback(KOWAGIGEVISION_CAMNR cam_nr, READ_WRITE_MEM_CALLBACK_FUNC c_func);

#ifdef WIN32
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI GEVGetPixelPtr(KOWAGIGEVISION_CAMNR cam_nr, DWORD offset, UINT64* ptradr);
#else
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI GEVGetPixelPtr(KOWAGIGEVISION_CAMNR cam_nr, DWORD offset, unsigned long* ptradr);
#endif

    GEV_DEPRECATED GEV_EXPORT WORD WINAPI GEVSetMemorySize(KOWAGIGEVISION_CAMNR cam_nr, DWORD mem_size);
    GEV_EXPORT WORD WINAPI GEVGetMemorySize(KOWAGIGEVISION_CAMNR cam_nr, DWORD* mem_size);

    GEV_EXPORT WORD WINAPI GEVSetMessageChannelCallback(KOWAGIGEVISION_CAMNR cam_nr, MESSAGECHANNEL_CALLBACK_FUNC c_func);

    GEV_EXPORT WORD WINAPI GEVSetReadWriteParameter(KOWAGIGEVISION_CAMNR cam_nr, DWORD ack_timeout, BYTE retry_count);
    GEV_EXPORT WORD WINAPI GEVGetReadWriteParameter(KOWAGIGEVISION_CAMNR cam_nr, DWORD* ack_timeout, BYTE* retry_count);

    GEV_EXPORT WORD WINAPI GEVSetNetConfig(KOWAGIGEVISION_CAMNR cam_nr, BYTE dhcp, DWORD ip, DWORD subnet, DWORD gateway);
    GEV_EXPORT WORD WINAPI GEVGetNetConfig(KOWAGIGEVISION_CAMNR cam_nr, BYTE* dhcp, DWORD* ip, DWORD* subnet, DWORD* gateway);

    GEV_EXPORT WORD WINAPI GEVForceIp(DWORD new_ip, DWORD subnet, DWORD gateway, BYTE* mac, DWORD adapter_ip);
    GEV_EXPORT WORD WINAPI GEVForceIpDiscovery(DWORD new_ip, DWORD subnet, DWORD gateway, BYTE* mac, DWORD adapter_ip, DWORD fcaddr);

    GEV_EXPORT WORD WINAPI GEVGetFilterDriverVersion(KOWAGIGEVISION_CAMNR cam_nr, BYTE* version_major, BYTE* version_minor);

    GEV_EXPORT WORD WINAPI GEVSetChannelParameter(KOWAGIGEVISION_CAMNR cam_nr, CHANNEL_PARAMETER cparam);
    GEV_EXPORT WORD WINAPI GEVGetChannelParameter(KOWAGIGEVISION_CAMNR cam_nr, CHANNEL_PARAMETER* cparam);

    GEV_EXPORT WORD WINAPI GEVSetHeartbeatRate(KOWAGIGEVISION_CAMNR cam_nr, DWORD heartbeat_rate);
    GEV_EXPORT WORD WINAPI GEVGetHeartbeatRate(KOWAGIGEVISION_CAMNR cam_nr, DWORD* heartbeat_rate);

    GEV_EXPORT WORD WINAPI GEVTestPacket(KOWAGIGEVISION_CAMNR cam_nr, DWORD* packet_size);
    GEV_EXPORT WORD WINAPI GEVGetConnectionStatus(KOWAGIGEVISION_CAMNR cam_nr, BYTE* status, BYTE* eval);

    GEV_EXPORT WORD WINAPI GEVGetTimeOneTick(KOWAGIGEVISION_CAMNR cam_nr, double* ttimes);

    GEV_EXPORT WORD WINAPI GEVGetDetailedLog(KOWAGIGEVISION_CAMNR cam_nr, BYTE* flags);
    GEV_EXPORT WORD WINAPI GEVSetDetailedLog(KOWAGIGEVISION_CAMNR cam_nr, BYTE flags);

    GEV_DEPRECATED GEV_EXPORT WORD WINAPI GEVSetActionCommand(KOWAGIGEVISION_CAMNR cam_nr, DWORD device_key, DWORD group_key, DWORD group_mask, DWORD action_time);
    GEV_EXPORT WORD WINAPI GEVIssueActionCommandBroadcast(const BYTE cam_nr[], size_t count, const ACTION_KEYS* keys, UINT64 actiontime, DWORD timeoutms, ACTION_ACKNOWLEDGE_CALLBACK_FUNC callback, void* param);
    GEV_EXPORT WORD WINAPI GEVIssueActionCommandAdapter(const DWORD adapterip[], size_t count, const ACTION_KEYS* keys, UINT64 actiontime, DWORD timeoutms, ACTION_ACKNOWLEDGE_CALLBACK_FUNC callback, void* param);
    GEV_EXPORT WORD WINAPI GEVIssueActionCommandBroadcastDirected(const BYTE cam_nr[], size_t count, const ACTION_KEYS* keys, UINT64 actiontime, DWORD timeoutms, ACTION_ACKNOWLEDGE_CALLBACK_FUNC callback, void* param);
    GEV_EXPORT WORD WINAPI GEVIssueActionCommandAdapterDirected(const DWORD adapterip[], size_t count, const ACTION_KEYS* keys, UINT64 actiontime, DWORD timeoutms, ACTION_ACKNOWLEDGE_CALLBACK_FUNC callback, void* param);
    GEV_EXPORT WORD WINAPI GEVIssueActionCommandUnicast(BYTE cam_nr, const ACTION_KEYS* keys, UINT64 actiontime);


    GEV_EXPORT WORD WINAPI GEVSetTraversingFirewallsInterval(KOWAGIGEVISION_CAMNR cam_nr, DWORD interval);

#ifdef WIN32
    GEV_EXPORT WORD WINAPI GEVEnableFirewallException(const char* app_name_with_path, const char* rule_name, BYTE* status);
#endif

    GEV_EXPORT WORD WINAPI GEVCheckDeviceStatus(DWORD ip_adapter, DWORD mask_adapter, DWORD ip_device, BYTE* device_status, DWORD ack_timeout, WORD port);

    // ***************** Utility functions ******************
    GEV_EXPORT void WINAPI GEVGetErrorString(WORD error_code, char errorstring[128]);

    // ***************** xml functions ******************
    GEV_EXPORT WORD WINAPI GEVGetFeatureList(KOWAGIGEVISION_CAMNR cam_nr, FeatureListPtr* featureListPtr, BYTE* maxLevel);

    GEV_EXPORT WORD WINAPI GEVGetFeatureParameter(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, FEATURE_PARAMETER* f_param);

    GEV_EXPORT WORD WINAPI GEVGetFeatureInteger(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, INT64* int_value);
    GEV_EXPORT WORD WINAPI GEVSetFeatureInteger(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, INT64 int_value);

    GEV_EXPORT WORD WINAPI GEVGetFeatureString(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, char* str_value);
    GEV_EXPORT WORD WINAPI GEVSetFeatureString(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, const char* str_value);

    GEV_EXPORT WORD WINAPI GEVGetFeatureBoolean(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, DWORD* bool_value);
    GEV_EXPORT WORD WINAPI GEVSetFeatureBoolean(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, DWORD bool_value);

    GEV_DEPRECATED GEV_EXPORT WORD WINAPI GEVGetFeatureCommand(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, DWORD* cmd_value);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI GEVSetFeatureCommand(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, DWORD cmd_value);
    GEV_EXPORT WORD WINAPI GEVExecuteFeatureCommand(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name);

    GEV_EXPORT WORD WINAPI GEVSetFeatureEnumeration(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, const char* enum_name, int str_len);
    GEV_EXPORT WORD WINAPI GEVGetFeatureEnumeration(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, char* enum_name, int str_len);
    GEV_EXPORT WORD WINAPI GEVGetFeatureEnumerationName(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, BYTE enum_index, char* enum_name, int str_len);

    GEV_EXPORT WORD WINAPI GEVGetFeatureFloat(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, double* float_value);
    GEV_EXPORT WORD WINAPI GEVSetFeatureFloat(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, double float_value);

    GEV_EXPORT WORD WINAPI GEVGetFeatureDisplayName(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, char* display_name, int display_name_length);
    GEV_EXPORT WORD WINAPI GEVGetFeatureTooltip(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, char* tooltip_name, int tooltip_name_length);

    GEV_EXPORT WORD WINAPI GEVSetXmlFile(KOWAGIGEVISION_CAMNR cam_nr, const char* filepath);
    GEV_EXPORT WORD WINAPI GEVInitXml(KOWAGIGEVISION_CAMNR cam_nr);

    GEV_EXPORT WORD WINAPI GEVGetFeatureRegister(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, DWORD len, BYTE* pbuffer);
    GEV_EXPORT WORD WINAPI GEVSetFeatureRegister(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, DWORD len, BYTE* pbuffer);

    GEV_EXPORT WORD WINAPI GEVGetFeatureUnit(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, char* unit_name, int unit_name_length);

    GEV_EXPORT WORD WINAPI GEVGetFeatureEnableStatus(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, BYTE* enable);

    GEV_EXPORT WORD WINAPI GEVGetXmlSize(KOWAGIGEVISION_CAMNR cam_nr, DWORD* size);
    GEV_EXPORT WORD WINAPI GEVGetXmlFile(KOWAGIGEVISION_CAMNR cam_nr, BYTE** xmlfile);

    GEV_EXPORT WORD WINAPI GEVGetFeatureInvalidator(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, BYTE index, char* invalidator_name, int str_len);

    GEV_EXPORT WORD WINAPI GEVGetFeaturePort(KOWAGIGEVISION_CAMNR cam_nr, const char* feature_name, char* port_name, int port_name_length);

    GEV_EXPORT WORD WINAPI GEVSetSchemaPath(KOWAGIGEVISION_CAMNR cam_nr, const char* schema_path);
    GEV_EXPORT WORD WINAPI GEVSetSchemaFromZip(KOWAGIGEVISION_CAMNR cam_nr, const void* schema_zip, size_t len);

    // only for embedded linux
    GEV_EXPORT WORD WINAPI GEVSetXmlCacheDirectoryName(KOWAGIGEVISION_CAMNR cam_nr, const char* dname);

    // ***************** Camera functions ******************

    GEV_EXPORT WORD WINAPI GEVAcquisitionStart(KOWAGIGEVISION_CAMNR cam_nr, DWORD number_images_to_acquire);
    GEV_EXPORT WORD WINAPI GEVAcquisitionStartEx(KOWAGIGEVISION_CAMNR cam_nr, DWORD number_images_to_acquire, DWORD image_size,
        DWORD image_width, DWORD image_height, DWORD pixel_format);

    GEV_EXPORT WORD WINAPI GEVAcquisitionStop(KOWAGIGEVISION_CAMNR cam_nr);
    GEV_EXPORT WORD WINAPI GEVSetAcquisitionCallback(KOWAGIGEVISION_CAMNR cam_nr, ACQUISITION_CALLBACK_FUNC callback);

    GEV_DEPRECATED GEV_EXPORT WORD WINAPI GEVGetImage(KOWAGIGEVISION_CAMNR cam_nr, IMAGE_HEADER* image_header);
    GEV_EXPORT WORD WINAPI GEVGetImageBuffer(KOWAGIGEVISION_CAMNR cam_nr, IMAGE_HEADER* image_header, BYTE* image_buffer);

    GEV_EXPORT WORD WINAPI GEVGetImageRingBuffer(KOWAGIGEVISION_CAMNR cam_nr, IMAGE_HEADER* image_header, WORD* image_buffer_index);
    GEV_EXPORT WORD WINAPI GEVQueueRingBuffer(KOWAGIGEVISION_CAMNR cam_nr, WORD image_buffer_index);
    GEV_EXPORT WORD WINAPI GEVSetRingBuffer(KOWAGIGEVISION_CAMNR cam_nr, WORD index, void* buffer);
    GEV_EXPORT WORD WINAPI GEVReleaseRingBuffer(KOWAGIGEVISION_CAMNR cam_nr);

    GEV_EXPORT WORD WINAPI GEVAddRingBufferElement(KOWAGIGEVISION_CAMNR cam_nr, DWORD size, void* buffer);
    GEV_EXPORT WORD WINAPI GEVRemoveRingBufferElement(KOWAGIGEVISION_CAMNR cam_nr, void* buffer);

    GEV_EXPORT WORD WINAPI GEVSetPacketResend(KOWAGIGEVISION_CAMNR cam_nr, BYTE enable);
    GEV_EXPORT WORD WINAPI GEVGetPacketResend(KOWAGIGEVISION_CAMNR cam_nr, BYTE* enable);
    GEV_EXPORT WORD WINAPI GEVPacketResend(KOWAGIGEVISION_CAMNR cam_nr, WORD stream_channel, INT64 block_id, DWORD first_packet_id, DWORD last_packet_id);

    GEV_EXPORT WORD WINAPI GEVGetImageFPS(KOWAGIGEVISION_CAMNR cam_nr, double* fps);

    GEV_EXPORT WORD WINAPI GEVSetBufferCount(KOWAGIGEVISION_CAMNR cam_nr, WORD count);
    GEV_EXPORT WORD WINAPI GEVGetBufferCount(KOWAGIGEVISION_CAMNR cam_nr, WORD* count);
    GEV_EXPORT WORD WINAPI GEVGetFreeBufferCount(KOWAGIGEVISION_CAMNR cam_nr, WORD* count);

    GEV_EXPORT WORD WINAPI GEVSetSecureTransfer(KOWAGIGEVISION_CAMNR cam_nr, BYTE enable, SECURE_TRANSFER_CALLBACK_FUNC c_func);
    GEV_EXPORT WORD WINAPI GEVGetSecureTransfer(KOWAGIGEVISION_CAMNR cam_nr, BYTE* enable);

    GEV_EXPORT WORD WINAPI GEVGetPacketsOutOfOrder(KOWAGIGEVISION_CAMNR cam_nr, BYTE* packets_out_of_order);
    GEV_EXPORT WORD WINAPI GEVSetPacketsOutOfOrder(KOWAGIGEVISION_CAMNR cam_nr, BYTE packets_out_of_order);

    // ***************** CANCam Camera functions ******************
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamGetPixelFormat(KOWAGIGEVISION_CAMNR cam_nr, DWORD* pixfmt);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamGetMaxVideoWindow(KOWAGIGEVISION_CAMNR cam_nr, WORD* max_width, WORD* max_height);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamGetVideoWindow(KOWAGIGEVISION_CAMNR cam_nr, WORD* x_start, WORD* y_start, WORD* x_len, WORD* y_len);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamSetVideoWindow(KOWAGIGEVISION_CAMNR cam_nr, WORD x_start, WORD y_start, WORD x_len, WORD y_len);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamGetGain(KOWAGIGEVISION_CAMNR cam_nr, BYTE* gain);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamSetGain(KOWAGIGEVISION_CAMNR cam_nr, BYTE gain);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamGetGainMinMax(KOWAGIGEVISION_CAMNR cam_nr, BYTE* gain_min, BYTE* gain_max);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamSetGainAuto(KOWAGIGEVISION_CAMNR cam_nr, BYTE on_off);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamGetExposureTime(KOWAGIGEVISION_CAMNR cam_nr, DWORD* exposure_time);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamSetExposureTime(KOWAGIGEVISION_CAMNR cam_nr, DWORD exposure_time);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamGetExposureTimeMinMax(KOWAGIGEVISION_CAMNR cam_nr, DWORD* exposure_min, DWORD* exposure_max);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamSetExposureTimeAuto(KOWAGIGEVISION_CAMNR cam_nr, BYTE on_off);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamSetLut(KOWAGIGEVISION_CAMNR cam_nr, WORD index, BYTE value);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI CANCamGetLut(KOWAGIGEVISION_CAMNR cam_nr, WORD index, BYTE* value);

    // ***************** Camera Link functions ******************
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI InitClinkSerial(KOWAGIGEVISION_CAMNR cam_nr, DWORD baud);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI GetClinkStatus(KOWAGIGEVISION_CAMNR cam_nr, CLINK_STATUS* status);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI SendClink(KOWAGIGEVISION_CAMNR cam_nr, WORD count, BYTE* send_buffer);
    GEV_DEPRECATED GEV_EXPORT WORD WINAPI ReceiveClink(KOWAGIGEVISION_CAMNR cam_nr, WORD count_buffer, BYTE* recv_buffer, WORD* recv_count);

    // ***************** Test functions ******************
    GEV_EXPORT WORD WINAPI GEVTestPacketResend(KOWAGIGEVISION_CAMNR cam_nr, BYTE on_off, WORD packet_number, WORD count);
    GEV_EXPORT WORD WINAPI GEVTestFindMaxPacketSize(KOWAGIGEVISION_CAMNR cam_nr, WORD* packet_size, WORD ps_min, WORD ps_max, WORD ps_inc);
    GEV_EXPORT void WINAPI GEVGetDllVersion(DWORD* major, DWORD* minor, DWORD* micro);
    GEV_EXPORT void WINAPI GEVGetDllAbiVersion(DWORD* major, DWORD* minor, DWORD* micro);

#ifdef __cplusplus
}
#endif

#endif//KOWAGIGEVISIONLIB_FUNCTIONS_H
