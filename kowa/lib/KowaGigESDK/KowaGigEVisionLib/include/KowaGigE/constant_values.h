#ifndef KOWAGIGEVISIONLIB_CONSTANT_VALUES_H
#define KOWAGIGEVISIONLIB_CONSTANT_VALUES_H

// event message channel
#define EVENT_TRIGGER               0x0002
#define EVENT_START_EXPOSURE        0x0003
#define EVENT_STOP_EXPOSURE         0x0004
#define EVENT_START_TRANSFER        0x0005
#define EVENT_STOP_TRANSFER         0x0006
#define EVENT_PRIMARY_APP_SWITCH    0x0007
#define EVENT_LINK_SPEED_CHANGE     0x0008
#define EVENT_ACTION_LATE           0x0009
#define EVENT_RESERVED_BEGIN        0x000A
#define EVENT_RESERVED_END          0x8000
#define EVENT_ERROR_BEGIN           0x8001
#define EVENT_ERROR_END             0x8FFF
#define EVENT_DEVICE_SPECIFIC       0x9000

#define FEATURE_NAME_COUNT 100

#define TYPE_CATEGORY     0
#define TYPE_FEATURE      1
#define TYPE_INTEGER      2
#define TYPE_FLOAT        3
#define TYPE_STRING       4
#define TYPE_ENUMERATION  5
#define TYPE_COMMAND      6
#define TYPE_BOOLEAN      7
#define TYPE_REGISTER     8
#define TYPE_PORT         9

#define ACCESS_MODE_RO    0x524F
#define ACCESS_MODE_RW    0x5257
#define ACCESS_MODE_WO    0x574F

#define VISIBILITY_INVISIBLE 0
#define VISIBILITY_BEGINNER  1
#define VISIBILITY_EXPERT    2
#define VISIBILITY_GURU      3

#define SIGN_UNSIGNED   0
#define SIGN_SIGNED     1

#define REPRESENTATION_LINEAR       0 // Slider with linear behaviour
#define REPRESENTATION_LOGARITHMIC  1 // Slider with logarithmic behaviour
#define REPRESENTATION_BOOLEAN      2 // Checkbox
#define REPRESENTATION_PURE_NUMBER  3 // Decimal number in an edit control
#define REPRESENTATION_HEX_NUMBER   4 // Hex number in an edit control
#define REPRESENTATION_UNDEFINDED   5 // Undefinded Representation
#define REPRESENTATION_IPV4ADDRESS  6 // IP address(IP version 4)
#define REPRESENTATION_MACADDRESS   7 // MAC address

#define DISPLAY_NOTATION_AUTOMATIC  0
#define DISPLAY_NOTATION_FIXED      1
#define DISPLAY_NOTATION_SCIENTIFIC 2

#define HEX_NUMBER    1

#define DISCOVERY_STATUS_OK                   0
#define DISCOVERY_STATUS_ALREADY_OPEN         1
#define DISCOVERY_STATUS_NOT_SAME_SUBNET      2
#define DISCOVERY_STATUS_CONTROL_OPEN         3
#define DISCOVERY_STATUS_COMMUNICATION_ERROR  4
#define DISCOVERY_STATUS_NOT_CHECKED          5

#define CONNECTION_STATUS_OK                 0
#define CONNECTION_STATUS_TIMEOUT            1
#define CONNECTION_STATUS_ACCESS_DENIED      2

#define OPEN_ACCESS       0
#define EXCLUSIVE_ACCESS  1
#define CONTROL_ACCESS    2

#define MAX_ADAPTER_NAME_LEN   256 // arb. from Win32API

#define PAYLOAD_TYPE_IMAGE                  0x0001
#define PAYLOAD_TYPE_IMAGE_EXTENDED_CHUNK   0x4001
#define PAYLOAD_TYPE_CHUNK                  0x0004
#define PAYLOAD_TYPE_GENDC                  0x000B
#define PAYLOAD_TYPE_JPEG                   0x0006
#define PAYLOAD_TYPE_JPEG_EX                0x4006
#define PAYLOAD_TYPE_JPEG_2000              0x0007
#define PAYLOAD_TYPE_JPEG_2000_EX           0x4007

#ifdef WIN32
#define FIREWALL_IS_DISABLED      1
#define FIREWALL_IS_ENABLED       2
#define FIREWALL_IS_ADDED         4
#endif

#endif//KOWAGIGEVISIONLIB_CONSTANT_VALUES_H
