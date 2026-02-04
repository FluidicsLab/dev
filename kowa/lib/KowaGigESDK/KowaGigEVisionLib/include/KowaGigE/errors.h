#ifndef KOWAGIGEVISIONLIB_EXTENDTED_ERRORS_H
#define KOWAGIGEVISIONLIB_EXTENDTED_ERRORS_H

#include "gev_errors.h"
// Extended Status Code by this SDK.
#ifndef GEV_STATUS_SUCCESS
#define GEV_STATUS_SUCCESS                              (0x0000)
#endif//GEV_STATUS_SUCCESS


#define GEV_STATUS_CAMERA_NOT_INIT                      (0xC001)
#define GEV_STATUS_CAMERA_ALWAYS_INIT                   (0xC002)
#define GEV_STATUS_CANNOT_CREATE_SOCKET                 (0xC003)
#define GEV_STATUS_SEND_ERROR                           (0xC004)
#define GEV_STATUS_RECEIVE_ERROR                        (0xC005)
#define GEV_STATUS_CAMERA_NOT_FOUND                     (0xC006)
#define GEV_STATUS_CANNOT_ALLOC_MEMORY                  (0xC007)
#define GEV_STATUS_TIMEOUT                              (0xC008)
#define GEV_STATUS_SOCKET_ERROR                         (0xC009)
#define GEV_STATUS_INVALID_ACK                          (0xC00A)
#define GEV_STATUS_CANNOT_START_THREAD                  (0xC00B)
#define GEV_STATUS_CANNOT_SET_SOCKET_OPT                (0xC00C)
#define GEV_STATUS_CANNOT_OPEN_DRIVER                   (0xC00D)
#define GEV_STATUS_HEARTBEAT_READ_ERROR                 (0xC00E)
#define GEV_STATUS_EVALUATION_EXPIRED                   (0xC00F)
#define GEV_STATUS_GRAB_ERROR                           (0xC010)
#define GEV_STATUS_DRIVER_READ_ERROR                    (0xC011)
#define GEV_STATUS_XML_READ_ERROR                       (0xC012)
#define GEV_STATUS_XML_OPEN_ERROR                       (0xC013)
#define GEV_STATUS_XML_FEATURE_ERROR                    (0xC014)
#define GEV_STATUS_XML_COMMAND_ERROR                    (0xC015)
#define GEV_STATUS_GAIN_NOT_SUPPORTED                   (0xC016)
#define GEV_STATUS_EXPOSURE_NOT_SUPPORTED               (0xC017)
#define GEV_STATUS_CANNOT_GET_ADAPTER_INFO              (0xC018)
#define GEV_STATUS_ERROR_INVALID_HANDLE                 (0xC019)
#define GEV_STATUS_CLINK_SET_BAUD                       (0xC01A)
#define GEV_STATUS_CLINK_SEND_BUFFER_FULL               (0xC01B)
#define GEV_STATUS_CLINK_RECEIVE_BUFFER_NO_DATA         (0xC01C)
#define GEV_STATUS_FEATURE_NOT_AVAILABLE                (0xC01D)
#define GEV_STATUS_MATH_PARSER_ERROR                    (0xC01E)
#define GEV_STATUS_FEATURE_ITEM_NOT_AVAILABLE           (0xC01F)
#define GEV_STATUS_NOT_SUPPORTED                        (0xC020)
#define GEV_STATUS_GET_URL_ERROR                        (0xC021)
#define GEV_STATUS_READ_XML_MEM_ERROR                   (0xC022)
#define GEV_STATUS_XML_SIZE_ERROR                       (0xC023)
#define GEV_STATUS_XML_ZIP_ERROR                        (0xC024)
#define GEV_STATUS_XML_ROOT_ERROR                       (0xC025)
#define GEV_STATUS_XML_FILE_ERROR                       (0xC026)
#define GEV_STATUS_DIFFERENT_IMAGE_HEADER               (0xC027)
#define GEV_STATUS_XML_SCHEMA_ERROR                     (0xC028)
#define GEV_STATUS_XML_STYLESHEET_ERROR                 (0xC029)
#define GEV_STATUS_FEATURE_LIST_ERROR                   (0xC02A)
#define GEV_STATUS_ALREADY_OPEN                         (0xC02B)
#define GEV_STATUS_TEST_PACKET_DATA_ERROR               (0xC02C)
#define GEV_STATUS_FEATURE_NOT_FLOAT                    (0xC02D)
#define GEV_STATUS_FEATURE_NOT_INTEGER                  (0xC02E)
#define GEV_STATUS_XML_DLL_NOT_FOUND                    (0xC02F)
#define GEV_STATUS_XML_NOT_INIT                         (0xC030)
#define GEV_STATUS_NOT_SAME_SUBNET                      (0xC031)
#define GEV_STATUS_GET_MANIFEST_TABLE_ERROR             (0xC032)
#define GEV_STATUS_DEPRECATED                           (0xC033)
#define GEV_STATUS_BUFFERS_NOT_INIT                     (0xC034)
//#define GEV_STATUS_BUFFER_TOO_SMALL                     (0xC035)
#define GEV_STATUS_INVALID_ARGUMENT                    (0xC036) // same role as GEV_STATUS_INVALID_PARAMETER
//#define GEV_STATUS_ARGUMENT_IS_NULL                     (0xC037)
#define GEV_STATUS_FEATURE_WRONG_TYPE                   (0xC038)
#define GEV_STATUS_INVALID_OPERATION                    (0xC039)
#define GEV_STATUS_UNDECIDED_PORT                       (0xC03A)
#define GEV_STATUS_UNDECIDED_ADDRESS                    (0xC03B)


#define KOWAGIGEVISIONLIB_EXTENDTED_ERRORS_H
#endif//KOWAGIGEVISIONLIB_EXTENDTED_ERRORS_H
