using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Runtime.InteropServices;

namespace GigeCameraCtrlSample
{
    internal class KowaGigEVisionLib
    {
        // Pixel Format
        public const uint GVSP_PIX_MONO1P = 0x01010037;
        public const uint GVSP_PIX_MONO2P = 0x01020038;
        public const uint GVSP_PIX_MONO4P = 0x01040039;
        public const uint GVSP_PIX_MONO8 = 0x01080001;
        public const uint GVSP_PIX_MONO8_SIGNED = 0x01080002;
        public const uint GVSP_PIX_MONO8S = 0x01080002;       // new name 2.0
        public const uint GVSP_PIX_MONO10 = 0x01100003;
        public const uint GVSP_PIX_MONO10_PACKED = 0x010C0004;
        public const uint GVSP_PIX_MONO12 = 0x01100005;
        public const uint GVSP_PIX_MONO12_PACKED = 0x010C0006;
        public const uint GVSP_PIX_MONO14 = 0x01100025;
        public const uint GVSP_PIX_MONO16 = 0x01100007;
        public const uint GVSP_PIX_BAYGR8 = 0x01080008;
        public const uint GVSP_PIX_BAYRG8 = 0x01080009;
        public const uint GVSP_PIX_BAYGB8 = 0x0108000A;
        public const uint GVSP_PIX_BAYBG8 = 0x0108000B;
        public const uint GVSP_PIX_BAYGR10 = 0x0110000C;
        public const uint GVSP_PIX_BAYRG10 = 0x0110000D;
        public const uint GVSP_PIX_BAYGB10 = 0x0110000E;
        public const uint GVSP_PIX_BAYBG10 = 0x0110000F;
        public const uint GVSP_PIX_BAYGR12 = 0x01100010;
        public const uint GVSP_PIX_BAYRG12 = 0x01100011;
        public const uint GVSP_PIX_BAYGB12 = 0x01100012;
        public const uint GVSP_PIX_BAYBG12 = 0x01100013;

        public const uint GVSP_PIX_BAYGR10_PACKED = 0x010C0026;
        public const uint GVSP_PIX_BAYRG10_PACKED = 0x010C0027;
        public const uint GVSP_PIX_BAYGB10_PACKED = 0x010C0028;
        public const uint GVSP_PIX_BAYBG10_PACKED = 0x010C0029;
        public const uint GVSP_PIX_BAYGR12_PACKED = 0x010C002A;
        public const uint GVSP_PIX_BAYRG12_PACKED = 0x010C002B;
        public const uint GVSP_PIX_BAYGB12_PACKED = 0x010C002C;
        public const uint GVSP_PIX_BAYBG12_PACKED = 0x010C002D;
        public const uint GVSP_PIX_BAYGR16_PACKED = 0x0110002E;
        public const uint GVSP_PIX_BAYRG16_PACKED = 0x0110002F;
        public const uint GVSP_PIX_BAYGB16_PACKED = 0x01100030;
        public const uint GVSP_PIX_BAYBG16_PACKED = 0x01100031;
        public const uint GVSP_PIX_RGB8_PACKED = 0x02180014;
        public const uint GVSP_PIX_RGB8 = 0x02180014;       // new name 2.0
        public const uint GVSP_PIX_BGR8_PACKED = 0x02180015;
        public const uint GVSP_PIX_BGR8 = 0x02180015;       // new name 2.0
        public const uint GVSP_PIX_RGBA8_PACKED = 0x02200016;
        public const uint GVSP_PIX_RGBA8 = 0x02200016;       // new name 2.0
        public const uint GVSP_PIX_BGRA8_PACKED = 0x02200017;
        public const uint GVSP_PIX_BGRA8 = 0x02200017;       // new name 2.0
        public const uint GVSP_PIX_RGB10_PACKED = 0x02300018;
        public const uint GVSP_PIX_RGB10 = 0x02300018;       // new name 2.0
        public const uint GVSP_PIX_BGR10_PACKED = 0x02300019;
        public const uint GVSP_PIX_BGR10 = 0x02300019;       // new name 2.0
        public const uint GVSP_PIX_RGB12_PACKED = 0x0230001A;
        public const uint GVSP_PIX_RGB12 = 0x0230001A;       // new name 2.0
        public const uint GVSP_PIX_BGR12_PACKED = 0x0230001B;
        public const uint GVSP_PIX_BGR12 = 0x0230001B;       // new name 2.0
        public const uint GVSP_PIX_RGB16_PACKED = 0x02300033;
        public const uint GVSP_PIX_RGB16 = 0x02300033;       // new name 2.0
        public const uint GVSP_PIX_RGB10V1_PACKED = 0x0220001C;
        public const uint GVSP_PIX_RGB10V2_PACKED = 0x0220001D;
        public const uint GVSP_PIX_RGB10P32 = 0x0220001D;       // new name 2.0
        public const uint GVSP_PIX_RGB12V1_PACKED = 0x02240034;
        public const uint GVSP_PIX_RGB565_PACKED = 0x02100035;
        public const uint GVSP_PIX_RGB565P = 0x02100035;       // new name 2.0
        public const uint GVSP_PIX_BGR565_PACKED = 0x02100036;
        public const uint GVSP_PIX_BGR565P = 0x02100036;       // new name 2.0
        public const uint GVSP_PIX_YUV411_PACKED = 0x020C001E;
        public const uint GVSP_PIX_YUV411_8_UYYVYY = 0x020C001E;
        public const uint GVSP_PIX_YUV422_PACKED = 0x0210001F;
        public const uint GVSP_PIX_YUV422_8_UYVY = 0x0210001F;
        public const uint GVSP_PIX_YUV422_YUYV_PACKED = 0x02100032;
        public const uint GVSP_PIX_YUV422_YUV422_8 = 0x02100032;
        public const uint GVSP_PIX_YUV444_PACKED = 0x02180020;
        public const uint GVSP_PIX_YUV8_UYV = 0x02180020;

        public const uint GVSP_PIX_YCBCR_8_CBYCR = 0x0218003A;
        public const uint GVSP_PIX_YCBCR422_8 = 0x0210003B;
        public const uint GVSP_PIX_YCBCR422_8_CBYCRY = 0x02100043;
        public const uint GVSP_PIX_YCBCR411_8_CBYYCRYY = 0x020C003C;

        public const uint GVSP_PIX_YCbCr601_8_CbYCr = 0x0218003D;
        public const uint GVSP_PIX_YCbCr601_422_8 = 0x0218003E;
        public const uint GVSP_PIX_YCbCr601_422_8_CbYCrY = 0x02100044;
        public const uint GVSP_PIX_YCbCr601_422_8_CbYYCrYY = 0x020C003F;

        public const uint GVSP_PIX_YCbCr709 = 0x02180040;
        public const uint GVSP_PIX_YCbCr709_422 = 0x02100041;
        public const uint GVSP_PIX_YCbCr709_422_8_CbYCrY = 0x02100045;
        public const uint GVSP_PIX_YCbCr709_422_8_CbYYCrYY = 0x020C0042;

        public const uint GVSP_PIX_RGB8_PLANAR = 0x02180021;
        public const uint GVSP_PIX_RGB10_PLANAR = 0x02300022;
        public const uint GVSP_PIX_RGB12_PLANAR = 0x02300023;
        public const uint GVSP_PIX_RGB16_PLANAR = 0x02300024;

        public const int GVSP_PIX_EFFECTIVE_PIXEL_SIZE_MASK = 0x00FF0000;
        public const int GVSP_PIX_EFFECTIVE_PIXEL_SIZE_SHIFT = 16;

        // Standard Status Codes
        public const ushort GEV_STATUS_SUCCESS = 0x0000;
        public const ushort GEV_STATUS_NOT_IMPLEMENTED = 0x8001;
        public const ushort GEV_STATUS_INVALID_PARAMETER = 0x8002;
        public const ushort GEV_STATUS_INVALID_ADDRESS = 0x8003;
        public const ushort GEV_STATUS_WRITE_PROTECT = 0x8004;
        public const ushort GEV_STATUS_BAD_ALIGNMENT = 0x8005;
        public const ushort GEV_STATUS_ACCESS_DENIED = 0x8006;
        public const ushort GEV_STATUS_BUSY = 0x8007;
        public const ushort GEV_STATUS_LOCAL_PROBLEM = 0x8008;
        public const ushort GEV_STATUS_MSG_MISMATCH = 0x8009;
        public const ushort GEV_STATUS_INVALID_PROTOCOL = 0x800A;
        public const ushort GEV_STATUS_NO_MSG = 0x800B;
        public const ushort GEV_STATUS_PACKET_UNAVAILABLE = 0x800C;
        public const ushort GEV_STATUS_DATA_OVERRUN = 0x800D;
        public const ushort GEV_STATUS_INVALID_HEADER = 0x800E;
        public const ushort GEV_STATUS_WRONG_CONFIG = 0x800F;
        public const ushort GEV_STATUS_PACKET_NOT_YET_AVAILABLE = 0x8010;
        public const ushort GEV_STATUS_PACKET_AND_PREV_REMOVED_FROM_MEMORY = 0x8011;
        public const ushort GEV_STATUS_PACKET_REMOVED_FROM_MEMORY = 0x8012;
        public const ushort GEV_STATUS_NO_REF_TIME1 = 0x8013;
        public const ushort GEV_STATUS_PACKET_TEMPORARILY_UNAVAILABLE = 0x8014;
        public const ushort GEV_STATUS_OVERFLOW = 0x8015;
        public const ushort GEV_STATUS_ACTION_LATE = 0x8016;
        public const ushort GEV_STATUS_ERROR = 0x8FFF;

        // Device-Specific Status Code
        public const ushort GEV_STATUS_CAMERA_NOT_INIT = 0xC001;
        public const ushort GEV_STATUS_CAMERA_ALWAYS_INIT = 0xC002;
        public const ushort GEV_STATUS_CANNOT_CREATE_SOCKET = 0xC003;
        public const ushort GEV_STATUS_SEND_ERROR = 0xC004;
        public const ushort GEV_STATUS_RECEIVE_ERROR = 0xC005;
        public const ushort GEV_STATUS_CAMERA_NOT_FOUND = 0xC006;
        public const ushort GEV_STATUS_CANNOT_ALLOC_MEMORY = 0xC007;
        public const ushort GEV_STATUS_TIMEOUT = 0xC008;
        public const ushort GEV_STATUS_SOCKET_ERROR = 0xC009;
        public const ushort GEV_STATUS_INVALID_ACK = 0xC00A;
        public const ushort GEV_STATUS_CANNOT_START_THREAD = 0xC00B;
        public const ushort GEV_STATUS_CANNOT_SET_SOCKET_OPT = 0xC00C;
        public const ushort GEV_STATUS_CANNOT_OPEN_DRIVER = 0xC00D;
        public const ushort GEV_STATUS_HEARTBEAT_READ_ERROR = 0xC00E;
        public const ushort GEV_STATUS_EVALUATION_EXPIRED = 0xC00F;
        public const ushort GEV_STATUS_GRAB_ERROR = 0xC010;
        public const ushort GEV_STATUS_DRIVER_READ_ERROR = 0xC011;
        public const ushort GEV_STATUS_XML_READ_ERROR = 0xC012;
        public const ushort GEV_STATUS_XML_OPEN_ERROR = 0xC013;
        public const ushort GEV_STATUS_XML_FEATURE_ERROR = 0xC014;
        public const ushort GEV_STATUS_XML_COMMAND_ERROR = 0xC015;
        public const ushort GEV_STATUS_GAIN_NOT_SUPPORTED = 0xC016;
        public const ushort GEV_STATUS_EXPOSURE_NOT_SUPPORTED = 0xC017;
        public const ushort GEV_STATUS_CANNOT_GET_ADAPTER_INFO = 0xC018;
        public const ushort GEV_STATUS_ERROR_INVALID_HANDLE = 0xC019;
        public const ushort GEV_STATUS_CLINK_SET_BAUD = 0xC01A;
        public const ushort GEV_STATUS_CLINK_SEND_BUFFER_FULL = 0xC01B;
        public const ushort GEV_STATUS_CLINK_REVEICE_BUFFER_NO_DATA = 0xC01C;
        public const ushort GEV_STATUS_FEATURE_NOT_AVAILABLE = 0xC01D;
        public const ushort GEV_STATUS_MATH_PARSER_ERROR = 0xC01E;
        public const ushort GEV_STATUS_FEATURE_ITEM_NOT_AVAILABLE = 0xC01F;
        public const ushort GEV_STATUS_NOT_SUPPORTED = 0xC020;
        public const ushort GEV_STATUS_GET_URL_ERROR = 0xC021;
        public const ushort GEV_STATUS_READ_XML_MEM_ERROR = 0xC022;
        public const ushort GEV_STATUS_XML_SIZE_ERROR = 0xC023;
        public const ushort GEV_STATUS_XML_ZIP_ERROR = 0xC024;
        public const ushort GEV_STATUS_XML_ROOT_ERROR = 0xC025;
        public const ushort GEV_STATUS_XML_FILE_ERROR = 0xC026;
        public const ushort GEV_STATUS_DIFFERENT_IMAGE_HEADER = 0xC027;
        public const ushort GEV_STATUS_XML_SCHEMA_ERROR = 0xC028;
        public const ushort GEV_STATUS_XML_STYLESHEET_ERROR = 0xC029;
        public const ushort GEV_STATUS_FEATURE_LIST_ERROR = 0xC02A;
        public const ushort GEV_STATUS_ALREADY_OPEN = 0xC02B;
        public const ushort GEV_STATUS_TEST_PACKET_DATA_ERROR = 0xC02C;
        public const ushort GEV_STATUS_FEATURE_NOT_FLOAT = 0xC02D;
        public const ushort GEV_STATUS_FEATURE_NOT_INTEGER = 0xC02E;
        public const ushort GEV_STATUS_XML_DLL_NOT_FOUND = 0xC02F;
        public const ushort GEV_STATUS_XML_NOT_INIT = 0xC030;
        public const ushort GEV_STATUS_NOT_SAME_SUBNET = 0xC031;
        public const ushort GEV_STATUS_GET_MANIFEST_TABLE_ERROR = 0xC032;

        // event message channel
        public const ushort EVENT_TRIGGER = 0x0002;
        public const ushort EVENT_START_EXPOSUE = 0x0003;
        public const ushort EVENT_STOP_EXPOSUE = 0x0004;
        public const ushort EVENT_START_TRANSFER = 0x0005;
        public const ushort EVENT_STOP_TRANSFER = 0x0006;
        public const ushort EVENT_PRIMARY_APP_SWITCH = 0x0007;
        public const ushort EVENT_LINK_SPEED_CHANGE = 0x0008;
        public const ushort EVENT_ACTION_LATE = 0x0009;
        public const ushort EVENT_ERROR_BEGIN = 0x8001;
        public const ushort EVENT_ERROR_END = 0x8FFF;
        public const ushort EVENT_DEVICE_SPECIFIC = 0x9000;

        public const ushort DEFAULT_PDATA = 2000;
        public const ushort DEFAULT_PCTRL = 2001;

        public const ushort FEATURE_NAME_COUNT = 100;

        public const ushort TYPE_CATEGORY = 0;
        public const ushort TYPE_FEATURE = 1;
        public const ushort TYPE_INTEGER = 2;
        public const ushort TYPE_FLOAT = 3;
        public const ushort TYPE_STRING = 4;
        public const ushort TYPE_ENUMERATION = 5;
        public const ushort TYPE_COMMAND = 6;
        public const ushort TYPE_BOOLEAN = 7;
        public const ushort TYPE_REGISTER = 8;
        public const ushort TYPE_PORT = 9;

        public const ushort ACCESS_MODE_RO = 0x524F;
        public const ushort ACCESS_MODE_RW = 0x5257;
        public const ushort ACCESS_MODE_WO = 0x574F;

        public const ushort VISIBILITY_INVISIBLE = 0;
        public const ushort VISIBILITY_BEGINNER = 1;
        public const ushort VISIBILITY_EXPERT = 2;
        public const ushort VISIBILITY_GURU = 3;

        public const byte OPEN_ACCESS = 0;
        public const byte EXCLUSIVE_ACCESS = 1;
        public const byte CONTROL_ACCESS = 2;

        public const byte SIGN_UNSIGNED = 0;
        public const byte SIGN_SIGNED = 1;

        public const ushort REPRESENTATION_LINEAR = 0;  // Slider with linear behaviour
        public const ushort REPRESENTATION_LOGARITHMIC = 1;  // Slider with logarithmic behaviour
        public const ushort REPRESENTATION_BOOLEAN = 2;  // Checkbox
        public const ushort REPRESENTATION_PURE_NUMBER = 3;  // Decimal number in an edit control
        public const ushort REPRESENTATION_HEX_NUMBER = 4;  // Hex number in an edit control
        public const ushort REPRESENTATION_UNDEFINDED = 5;  // Undefinded Representation
        public const ushort REPRESENTATION_IPV4ADDRESS = 6;  // IP address(IP version 4)
        public const ushort REPRESENTATION_MACADDRESS = 7;  // MAC address

        public const byte DISPLAY_NOTATION_AUTOMATIC = 0;
        public const byte DISPLAY_NOTATION_FIXED = 1;
        public const byte DISPLAY_NOTATION_SCIENTIFIC = 2;

        public const byte DISCOVERY_STATUS_OK = 0;
        public const byte DISCOVERY_STATUS_ALLREADY_OPEN = 1;
        public const byte DISCOVERY_STATUS_NOT_SAME_SUBNET = 2;
        public const byte DISCOVERY_STATUS_CONTROL_OPEN = 3;

        public const byte CONNECTION_STATUS_OK = 0;
        public const byte CONNECTION_STATUS_TIMEOUT = 1;
        public const byte CONNECTION_STATUS_ACCESS_DENIED = 2;

        public const byte DETAILED_LOG_OFF = 0;
        public const byte DETAILED_LOG_INFO = 1;
        public const byte DETAILED_LOG_WARNING = 2;
        public const byte DETAILED_LOG_ERROR = 4;
        public const byte DETAILED_LOG_REGISTER = 8;

        public const ushort PAYLOAD_TYPE_IMAGE = 0x0001;
        public const ushort PAYLOAD_TYPE_IMAGE_EXTENDED_CHUNK = 0x4001;
        public const ushort PAYLOAD_TYPE_CHUNK = 0x0004;
        public const ushort PAYLOAD_TYPE_GENDC = 0x000B;

        public struct _FeatureList
        {
            public IntPtr Next;
            public uint Index;
            public IntPtr Name;
            public byte Type;
            public byte Level;
        }

        public struct FEATURE_PARAMETER
        {
            public byte Type;
            public long Min;
            public long Max;
            public uint OnValue;
            public uint OffValue;
            public ushort AccessMode;
            public ushort Representation;
            public uint Inc;
            public uint CommandValue;
            public uint Length;
            public byte EnumerationCount;
            public byte Visibility;
            public double FloatMin;
            public double FloatMax;
            public double FloatInc;
            public byte IsImplemented;
            public byte IsAvailable;
            public byte IsLocked;
            public byte Sign;
            public uint Address;
            public byte DisplayNotation;
            public byte DisplayPrecision;
            public byte InvalidatorCount;
            public Int64 PollingTime;
        }

        public struct DEVICE_PARAM
        {
            public uint IP;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 32)] public byte[] manuf;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 32)] public byte[] model;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 32)] public byte[] version;
            public uint AdapterIP;
            public uint AdapterMask;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 6)] public byte[] Mac;
            public uint subnet;
            public uint gateway;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 260)]
            public char[] adapter_name;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)] public byte[] serial;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)] public byte[] userdef_name;
            public byte status;
        }

        public struct ADAPTER_PARAM
        {
            public uint AdapterIP;
            public uint AdapterMask;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 260)]
            public char[] AdapterName;
        }

        public struct ENUMERATE_ADAPTER
        {
            public byte Count;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)]
            public ADAPTER_PARAM[] param;
        }

        public struct DISCOVERY
        {
            public byte Count;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 20)]
            public DEVICE_PARAM[] param;
        }

        public struct CONNECTION
        {
            public uint IP_CANCam;
            public ushort PortData;
            public ushort PortCtrl;
            public uint AdapterIP;
            public uint AdapterMask;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 260)]
            public char[] adapter_name;
        }

        public struct CLINK_STATUS
        {
            public byte receive_count;
            public byte transmit_count;
            public byte transmit_buffer_full;
            public byte transmit_buffer_empty;
            public byte reveice_buffer_full;
            public byte reveice_data_available;
        }

        public struct CHANNEL_PARAMETER
        {
            public uint cc_heartbeat_rate;
            public uint cc_timeout;
            public byte cc_retry;
            public uint sc_timeout;
            public byte sc_packet_resend;
            public uint sc_image_wait_timeout;
        }

        public struct IMAGE_HEADER
        {
            public Int64 FrameCounter;
            public UInt64 TimeStamp;
            public uint PixelType;
            public uint SizeX;
            public uint SizeY;
            public uint OffsetX;
            public uint OffsetY;
            public ushort PaddingX;
            public ushort PaddingY;
            public int MissingPacket;
            public ushort PayloadType;
            public uint ChunkDataPayloadLength;
            public uint ChunkLayoutId;
        }

        public struct MESSAGECHANNEL_PARAMETER
        {
            public ushort EventID;
            public ushort StreamChannelIndex;
            public UInt64 BlockID;
            public UInt64 TimeStamp;
            public byte[] Data;
            public ushort DataLength;
        }

        public struct ACTION_KEYS
        {
            public uint DeviceKey;
            public uint GroupKey;
            public uint GroupMask;
        }

        public delegate void CallbackDiscovery(int s_cnt);
        public delegate void CallbackMessagechannel(byte cam_nr, MESSAGECHANNEL_PARAMETER mcparam);
        public delegate void CallbackError(byte cam_nr, IntPtr error_str);
        public delegate byte CallbackSecureTransfer(byte cam_nr);
        public delegate byte CallbackReadWriteMem(byte cam_nr, int s_cnt);

        /// <returns>
        ///  0: continue to wait acknowledge.
        ///  1: decontinue to waiting, and instantly return.
        /// </returns>
        public delegate byte CallbackActionAcknowledge(byte cam_nr, uint fromip, ushort status, IntPtr param);

        // General functions
        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVDiscovery")]
        public static extern ushort GEVDiscovery(out DISCOVERY disc, MulticastDelegate callback, uint timeout, bool ignore_subnet);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVEnumerateAdapters")]
        public static extern ushort GEVEnumerateAdapters(out ENUMERATE_ADAPTER adapter);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVDiscoveryAdapter")]
        public static extern ushort GEVDiscoveryAdapter(out DISCOVERY disc, ref ADAPTER_PARAM adapter, MulticastDelegate callback, uint timeout, bool ignore_subnet);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVInit")]
        public static extern ushort GEVInit(byte cam_nr, ref CONNECTION con, MulticastDelegate callback, byte save_xml, byte open_mode);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVClose")]
        public static extern ushort GEVClose(byte cam_nr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVOpenStreamChannel")]
        public static extern ushort GEVOpenStreamChannel(byte cam_nr, uint ip, ushort port, uint multicast);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVCloseStreamChannel")]
        public static extern ushort GEVCloseStreamChannel(byte cam_nr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVInitFilterDriver")]
        public static extern ushort GEVInitFilterDriver(byte cam_nr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVCloseFilterDriver")]
        public static extern ushort GEVCloseFilterDriver(byte cam_nr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVWriteRegister")]
        public static extern ushort GEVWriteRegister(byte cam_nr, uint cmd, byte cnt, [MarshalAs(UnmanagedType.LPArray)] uint[] pptr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVReadRegister")]
        public static extern ushort GEVReadRegister(byte cam_nr, uint cmd, byte cnt, [MarshalAs(UnmanagedType.LPArray)] uint[] pptr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVWriteMemory")]
        public static extern ushort GEVWriteMemory(byte cam_nr, uint maddr, uint cnt, [MarshalAs(UnmanagedType.LPArray)] byte[] pptr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVReadMemory")]
        public static extern ushort GEVReadMemory(byte cam_nr, uint maddr, uint cnt, [MarshalAs(UnmanagedType.LPArray)] byte[] pptr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetReadWriteMemoryCallback")]
        public static extern ushort GEVSetReadWriteMemoryCallback(byte cam_nr, MulticastDelegate callback);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetPixelPtr")]
        public static extern ushort GEVGetPixelPtr(byte cam_nr, uint offset, out ulong ptradr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetMemorySize")]
        public static extern ushort GEVSetMemorySize(byte cam_nr, uint mem_size);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetMemorySize")]
        public static extern ushort GEVGetMemorySize(byte cam_nr, out uint mem_size);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetMessageChannelCallback")]
        public static extern ushort GEVSetMessageChannelCallback(byte cam_nr, MulticastDelegate callback);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetReadWriteParameter")]
        public static extern ushort GEVSetReadWriteParameter(byte cam_nr, uint ack_timeout, byte retry_count);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetReadWriteParameter")]
        public static extern ushort GEVGetReadWriteParameter(byte cam_nr, out uint ack_timeout, out byte retry_count);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetNetConfig")]
        public static extern ushort GEVSetNetConfig(byte cam_nr, byte dhcp, uint ip, uint subnet, uint gateway);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetNetConfig")]
        public static extern ushort GEVGetNetConfig(byte cam_nr, out byte dhcp, out uint ip, out uint subnet, out uint gateway);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVForceIp")]
        public static extern ushort GEVForceIp(uint new_ip, uint subnet, uint gateway, [MarshalAs(UnmanagedType.LPArray)] byte[] mac);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFilterDriverVersion")]
        public static extern ushort GEVGetFilterDriverVersion(byte cam_nr, out byte version_major, out byte version_minor);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetChannelParameter")]
        public static extern ushort GEVSetChannelParameter(byte cam_nr, CHANNEL_PARAMETER cparam);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetChannelParameter")]
        public static extern ushort GEVGetChannelParameter(byte cam_nr, out CHANNEL_PARAMETER cparam);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetHeartbeatRate")]
        public static extern ushort GEVSetHeartbeatRate(byte cam_nr, uint heartbeat_rate);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetHeartbeatRate")]
        public static extern ushort GEVGetHeartbeatRate(byte cam_nr, out uint heartbeat_rate);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVTestPacket")]
        public static extern ushort GEVTestPacket(byte cam_nr, out uint packet_size);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetConnectionStatus")]
        public static extern ushort GEVGetConnectionStatus(byte cam_nr, out byte status, out byte eval);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetTimeOneTick")]
        public static extern ushort GEVGetTimeOneTick(byte cam_nr, out double ttimes);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetDetailedLog")]
        public static extern ushort GEVGetDetailedLog(byte cam_nr, out byte on_off);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetDetailedLog")]
        public static extern ushort GEVSetDetailedLog(byte cam_nr, byte on_off);


        [Obsolete, DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetActionCommand")]
        public static extern ushort GEVSetActionCommand(byte cam_nr, uint device_key, uint group_key, uint group_mask, uint action_time);
        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVIssueActionCommandBroadcast")]
        private static extern ushort GEVIssueActionCommandBroadcast(byte[] cam_nr, UIntPtr count, in ACTION_KEYS keys, ulong actiontime, uint timeoutms, CallbackActionAcknowledge callback, IntPtr param);
        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVIssueActionCommandAdapter")]
        private static extern ushort GEVIssueActionCommandAdapter(uint[] adapterip, UIntPtr count, in ACTION_KEYS keys, ulong actiontime, uint timeoutms, CallbackActionAcknowledge callback, IntPtr param);
        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVIssueActionCommandUnicast")]
        public static extern ushort GEVIssueActionCommandUnicast(byte cam_nr, in ACTION_KEYS keys, ulong actiontime);
        public static ushort GEVIssueActionCommandBroadcast(byte[] cam_nr, in ACTION_KEYS keys, ulong actiontime, uint timeoutms, CallbackActionAcknowledge callback, IntPtr param)
            => GEVIssueActionCommandBroadcast(cam_nr, (UIntPtr)cam_nr.Length, keys, actiontime, timeoutms, callback, param);
        public static ushort GEVIssueActionCommandAdapter(uint[] adapterip, in ACTION_KEYS keys, ulong actiontime, uint timeoutms, CallbackActionAcknowledge callback, IntPtr param)
            => GEVIssueActionCommandAdapter(adapterip, (UIntPtr)adapterip.Length, keys, actiontime, timeoutms, callback, param);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetTraversingFirewallsInterval")]
        public static extern ushort GEVSetTraversingFirewallsInterval(byte cam_nr, uint interval);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVEnableFirewallException")]
        public static extern ushort GEVEnableFirewallException(String app_name_with_path, String rule_name, out byte status);

        // xml functions
        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureList")]
        //        public static extern ushort GEVGetFeatureList(byte cam_nr, out _FeatureList featureListPtr, out byte maxLevel);
        public static extern ushort GEVGetFeatureList(byte cam_nr, out _FeatureList featureListPtr, out byte maxLevel);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureParameter")]
        public static extern ushort GEVGetFeatureParameter(byte cam_nr, String feature_name, out FEATURE_PARAMETER f_param);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureInteger")]
        public static extern ushort GEVGetFeatureInteger(byte cam_nr, String feature_name, out Int64 int_value);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetFeatureInteger")]
        public static extern ushort GEVSetFeatureInteger(byte cam_nr, String feature_name, Int64 int_value);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureString")]
        public static extern ushort GEVGetFeatureString(byte cam_nr, String feature_name, StringBuilder str_value);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetFeatureString")]
        public static extern ushort GEVSetFeatureString(byte cam_nr, String feature_name, String str_value);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureBoolean")]
        public static extern ushort GEVGetFeatureBoolean(byte cam_nr, String feature_name, out uint bool_value);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetFeatureBoolean")]
        public static extern ushort GEVSetFeatureBoolean(byte cam_nr, String feature_name, uint bool_value);

        [Obsolete, DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureCommand")]
        public static extern ushort GEVGetFeatureCommand(byte cam_nr, String feature_name, out uint cmd_value);

        [Obsolete, DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetFeatureCommand")]
        public static extern ushort GEVSetFeatureCommand(byte cam_nr, String feature_name, uint cmd_value);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVExecuteFeatureCommand")]
        public static extern ushort GEVExecuteFeatureCommand(byte cam_nr, String feature_name);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureEnumeration")]
        public static extern ushort GEVGetFeatureEnumeration(byte cam_nr, String feature_name, StringBuilder enum_name, int str_len);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetFeatureEnumeration")]
        public static extern ushort GEVSetFeatureEnumeration(byte cam_nr, String feature_name, StringBuilder enum_name, int str_len);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureEnumerationName")]
        public static extern ushort GEVGetFeatureEnumerationName(byte cam_nr, String feature_name, byte enum_index, StringBuilder enum_name, int str_len);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureFloat")]
        public static extern ushort GEVGetFeatureFloat(byte cam_nr, String feature_name, out double float_value);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetFeatureFloat")]
        public static extern ushort GEVSetFeatureFloat(byte cam_nr, String feature_name, double float_value);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureDisplayName")]
        public static extern ushort GEVGetFeatureDisplayName(byte cam_nr, String feature_name, StringBuilder display_name, int display_name_length);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureTooltip")]
        public static extern ushort GEVGetFeatureTooltip(byte cam_nr, String feature_name, StringBuilder tooltip_name, int tooltip_name_length);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetXmlFile")]
        public static extern ushort GEVSetXmlFile(byte cam_nr, String xml_name);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVInitXml")]
        public static extern ushort GEVInitXml(byte cam_nr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureRegister")]
        public static extern ushort GEVGetFeatureRegister(byte cam_nr, String feature_name, uint len, [MarshalAs(UnmanagedType.LPArray)] byte[] pbuffer);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetFeatureRegister")]
        public static extern ushort GEVSetFeatureRegister(byte cam_nr, String feature_name, uint len, [MarshalAs(UnmanagedType.LPArray)] byte[] pbuffer);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureUnit")]
        public static extern ushort GEVGetFeatureUnit(byte cam_nr, String feature_name, StringBuilder unit_name, uint len);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureEnableStatus")]
        public static extern ushort GEVGetFeatureEnableStatus(byte cam_nr, String feature_name, out byte enable);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetXmlSize")]
        public static extern ushort GEVGetXmlSize(byte cam_nr, out uint size);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetXmlFile")]
        public static extern ushort GEVGetXmlFile(byte cam_nr, ref byte xmlfile);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeatureInvalidator")]
        public static extern ushort GEVGetFeatureInvalidator(byte cam_nr, String feature_name, byte index, String invalidator_name, int str_len);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFeaturePort")]
        public static extern ushort GEVGetFeaturePort(byte cam_nr, String feature_name, String port_name, int port_name_length);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetSchemaPath")]
        public static extern ushort GEVSetSchemaPath(byte cam_nr, String schema_path);

        // Camera functions
        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVAcquisitionStart")]
        public static extern ushort GEVAcquisitionStart(byte cam_nr, uint number_images_to_acquire);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVAcquisitionStartEx")]
        public static extern ushort GEVAcquisitionStartEx(byte cam_nr, uint number_images_to_acquire, uint image_size);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVAcquisitionStop")]
        public static extern ushort GEVAcquisitionStop(byte cam_nr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetImage")]
        public static extern ushort GEVGetImage(byte cam_nr, out IMAGE_HEADER image_header);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetImageBuffer")]
        public static extern ushort GEVGetImageBuffer(byte cam_nr, out IMAGE_HEADER image_header, [MarshalAs(UnmanagedType.LPArray)] byte[] image_buffer);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetImageRingBuffer")]
        public static extern ushort GEVGetImageRingBuffer(byte cam_nr, out IMAGE_HEADER image_header, out ushort image_buffer_index);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVQueueRingBuffer")]
        public static extern ushort GEVQueueRingBuffer(byte cam_nr, ushort image_buffer_index);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetRingBuffer")]
        public static extern ushort GEVSetRingBuffer(byte cam_nr, ushort index, IntPtr image_buffer);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVReleaseRingBuffer")]
        public static extern ushort GEVReleaseRingBuffer(byte cam_nr);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVAddRingBufferElement")]
        public static extern ushort GEVAddRingBufferElement(byte cam_nr, uint size, IntPtr image_buffer);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVRemoveRingBufferElement")]
        public static extern ushort GEVRemoveRingBufferElement(byte cam_nr, IntPtr image_buffer);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetPacketResend")]
        public static extern ushort GEVSetPacketResend(byte cam_nr, byte enable);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetPacketResend")]
        public static extern ushort GEVGetPacketResend(byte cam_nr, out byte enable);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVPacketResend")]
        public static extern ushort GEVPacketResend(byte cam_nr, ushort stream_channel, Int64 block_id, uint first_packet_id, uint last_packet_id);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetImageFPS")]
        public static extern ushort GEVGetImageFPS(byte cam_nr, out double fps);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetBufferCount")]
        public static extern ushort GEVSetBufferCount(byte cam_nr, ushort count);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetBufferCount")]
        public static extern ushort GEVGetBufferCount(byte cam_nr, out ushort count);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetFreeBufferCount")]
        public static extern ushort GEVGetFreeBufferCount(byte cam_nr, out ushort count);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetSecureTransfer")]
        public static extern ushort GEVSetSecureTransfer(byte cam_nr, byte enable, MulticastDelegate callback);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetSecureTransfer")]
        public static extern ushort GEVGetSecureTransfer(byte cam_nr, out byte enable);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVGetPacketsOutOfOrder")]
        public static extern ushort GEVGetPacketsOutOfOrder(byte cam_nr, out byte packets_out_of_order);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVSetPacketsOutOfOrder")]
        public static extern ushort GEVSetPacketsOutOfOrder(byte cam_nr, byte packets_out_of_order);

        // camera link functions
        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "CANCamInitClinkSerial")]
        public static extern ushort CANCamInitClinkSerial(byte cam_nr, uint baud);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "CANCamGetClinkStatus")]
        public static extern ushort CANCamGetClinkStatus(byte cam_nr, out CLINK_STATUS status);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "CANCamSendClink")]
        public static extern ushort CANCamSendClink(byte cam_nr, byte count, [MarshalAs(UnmanagedType.LPArray)] byte[] send_buffer);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "CANCamReceiveClink")]
        public static extern ushort CANCamReceiveClink(byte cam_nr, byte count_buffer, [MarshalAs(UnmanagedType.LPArray)] byte[] recv_buffer, out byte recv_count);

        // Test functions
        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVTestPacketResend")]
        public static extern ushort GEVTestPacketResend(byte cam_nr, byte on_off, ushort paket_number, ushort count);

        [DllImport("KowaGigEVisionLib.dll", CharSet = CharSet.Ansi, EntryPoint = "GEVTestFindMaxPacketSize")]
        public static extern ushort GEVTestFindMaxPacketSize(byte cam_nr, out ushort paket_size, ushort ps_min, ushort ps_max, ushort ps_inc);

        public static void GetErrorString(byte cam_nr, ushort error, out string errorStr)
        {
            switch (error)
            {
                case GEV_STATUS_NOT_IMPLEMENTED: errorStr = "STATUS_NOT_IMPLEMENTED"; break;
                case GEV_STATUS_INVALID_PARAMETER: errorStr = "STATUS_INVALID_PARAMETER"; break;
                case GEV_STATUS_INVALID_ADDRESS: errorStr = "STATUS_INVALID_ADDRESS"; break;
                case GEV_STATUS_WRITE_PROTECT: errorStr = "STATUS_WRITE_PROTECT"; break;
                case GEV_STATUS_BAD_ALIGNMENT: errorStr = "STATUS_BAD_ALIGNMENT"; break;
                case GEV_STATUS_ACCESS_DENIED: errorStr = "STATUS_ACCESS_DENIED"; break;
                case GEV_STATUS_BUSY: errorStr = "STATUS_BUSY"; break;
                case GEV_STATUS_LOCAL_PROBLEM: errorStr = "STATUS_LOCAL_PROBLEM"; break;
                case GEV_STATUS_MSG_MISMATCH: errorStr = "STATUS_MSG_MISMATCH"; break;
                case GEV_STATUS_INVALID_PROTOCOL: errorStr = "STATUS_INVALID_PROTOCOL"; break;
                case GEV_STATUS_NO_MSG: errorStr = "STATUS_NO_MSG"; break;
                case GEV_STATUS_PACKET_UNAVAILABLE: errorStr = "STATUS_PACKET_UNAVAILABLE"; break;
                case GEV_STATUS_DATA_OVERRUN: errorStr = "STATUS_DATA_OVERRUN"; break;
                case GEV_STATUS_INVALID_HEADER: errorStr = "STATUS_INVALID_HEADER"; break;
                case GEV_STATUS_WRONG_CONFIG: errorStr = "STATUS_WRONG_CONFIG"; break;
                case GEV_STATUS_PACKET_NOT_YET_AVAILABLE: errorStr = "STATUS_PACKET_NOT_YET_AVAILABLE"; break;
                case GEV_STATUS_PACKET_AND_PREV_REMOVED_FROM_MEMORY: errorStr = "STATUS_PACKET_AND_PREV_REMOVED_FROM_MEMORY"; break;
                case GEV_STATUS_PACKET_REMOVED_FROM_MEMORY: errorStr = "STATUS_PACKET_REMOVED_FROM_MEMORY"; break;
                case GEV_STATUS_NO_REF_TIME1: errorStr = "STATUS_NO_REF_TIME1"; break;
                case GEV_STATUS_PACKET_TEMPORARILY_UNAVAILABLE: errorStr = "STATUS_PACKET_TEMPORARILY_UNAVAILABLE"; break;
                case GEV_STATUS_OVERFLOW: errorStr = "STATUS_OVERFLOW"; break;
                case GEV_STATUS_ACTION_LATE: errorStr = "STATUS_ACTION_LATE"; break;
                case GEV_STATUS_ERROR: errorStr = "STATUS_ERROR"; break;

                case GEV_STATUS_CAMERA_NOT_INIT: errorStr = "STATUS_CAMERA_NOT_INIT"; break;
                case GEV_STATUS_CAMERA_ALWAYS_INIT: errorStr = "STATUS_CAMERA_ALWAYS_INIT"; break;
                case GEV_STATUS_CANNOT_CREATE_SOCKET: errorStr = "STATUS_CANNOT_CREATE_SOCKET"; break;
                case GEV_STATUS_SEND_ERROR: errorStr = "STATUS_SEND_ERROR"; break;
                case GEV_STATUS_CANNOT_ALLOC_MEMORY: errorStr = "STATUS_RECEIVE_ERROR"; break;
                case GEV_STATUS_RECEIVE_ERROR: errorStr = "STATUS_CANNOT_ALLOC_MEMORY"; break;
                case GEV_STATUS_TIMEOUT: errorStr = "STATUS_TIMEOUT"; break;
                case GEV_STATUS_SOCKET_ERROR: errorStr = "STATUS_SOCKET_ERROR"; break;
                case GEV_STATUS_INVALID_ACK: errorStr = "STATUS_INVALID_ACK"; break;
                case GEV_STATUS_CANNOT_START_THREAD: errorStr = "STATUS_CANNOT_START_THREAD"; break;
                case GEV_STATUS_CANNOT_SET_SOCKET_OPT: errorStr = "STATUS_CANNOT_SET_SOCKET_OPT"; break;
                case GEV_STATUS_CANNOT_OPEN_DRIVER: errorStr = "STATUS_CANNOT_OPEN_DRIVER"; break;
                case GEV_STATUS_HEARTBEAT_READ_ERROR: errorStr = "STATUS_HEARTBEAT_READ_ERROR"; break;
                case GEV_STATUS_EVALUATION_EXPIRED: errorStr = "STATUS_EVALUATION_EXPIRED"; break;
                case GEV_STATUS_GRAB_ERROR: errorStr = "STATUS_GRAB_ERROR"; break;
                case GEV_STATUS_XML_READ_ERROR: errorStr = "STATUS_XML_READ_ERROR"; break;
                case GEV_STATUS_XML_OPEN_ERROR: errorStr = "STATUS_XML_OPEN_ERROR"; break;
                case GEV_STATUS_XML_FEATURE_ERROR: errorStr = "STATUS_XML_FEATURE_ERROR"; break;
                case GEV_STATUS_XML_COMMAND_ERROR: errorStr = "STATUS_XML_COMMAND_ERROR"; break;
                case GEV_STATUS_GAIN_NOT_SUPPORTED: errorStr = "STATUS_GAIN_NOT_SUPPORTED"; break;
                case GEV_STATUS_EXPOSURE_NOT_SUPPORTED: errorStr = "STATUS_EXPOSURE_NOT_SUPPORTED"; break;
                case GEV_STATUS_CANNOT_GET_ADAPTER_INFO: errorStr = "STATUS_CANNOT_GET_ADAPTER_INFO"; break;
                case GEV_STATUS_ERROR_INVALID_HANDLE: errorStr = "STATUS_ERROR_INVALID_HANDLE"; break;
                case GEV_STATUS_CLINK_SET_BAUD: errorStr = "STATUS_CLINK_SET_BAUD"; break;
                case GEV_STATUS_CLINK_SEND_BUFFER_FULL: errorStr = "STATUS_CLINK_SEND_BUFFER_FULL"; break;
                case GEV_STATUS_CLINK_REVEICE_BUFFER_NO_DATA: errorStr = "STATUS_CLINK_REVEICE_BUFFER_NO_DATA"; break;
                case GEV_STATUS_FEATURE_NOT_AVAILABLE: errorStr = "STATUS_FEATURE_NOT_AVAILABLE"; break;
                case GEV_STATUS_MATH_PARSER_ERROR: errorStr = "STATUS_MATH_PARSER_ERROR"; break;
                case GEV_STATUS_FEATURE_ITEM_NOT_AVAILABLE: errorStr = "STATUS_FEATURE_ITEM_NOT_AVAILABLE"; break;
                case GEV_STATUS_NOT_SUPPORTED: errorStr = "STATUS_NOT_SUPPORTED"; break;
                case GEV_STATUS_GET_URL_ERROR: errorStr = "STATUS_GET_URL_ERROR"; break;
                case GEV_STATUS_READ_XML_MEM_ERROR: errorStr = "STATUS_READ_XML_MEM_ERROR"; break;
                case GEV_STATUS_XML_SIZE_ERROR: errorStr = "STATUS_XML_SIZE_ERROR"; break;
                case GEV_STATUS_XML_ZIP_ERROR: errorStr = "STATUS_XML_ZIP_ERROR"; break;
                case GEV_STATUS_XML_ROOT_ERROR: errorStr = "STATUS_XML_ROOT_ERROR"; break;
                case GEV_STATUS_XML_FILE_ERROR: errorStr = "STATUS_XML_FILE_ERROR"; break;
                case GEV_STATUS_DIFFERENT_IMAGE_HEADER: errorStr = "STATUS_DIFFERENT_IMAGE_HEADER"; break;
                case GEV_STATUS_XML_SCHEMA_ERROR: errorStr = "STATUS_XML_SCHEMA_ERROR"; break;
                case GEV_STATUS_XML_STYLESHEET_ERROR: errorStr = "STATUS_XML_STYLESHEET_ERROR"; break;
                case GEV_STATUS_FEATURE_LIST_ERROR: errorStr = "STATUS_FEATURE_LIST_ERROR"; break;
                case GEV_STATUS_ALREADY_OPEN: errorStr = "STATUS_ALREADY_OPEN"; break;
                case GEV_STATUS_TEST_PACKET_DATA_ERROR: errorStr = "STATUS_TEST_PACKET_DATA_ERROR"; break;
                case GEV_STATUS_FEATURE_NOT_FLOAT: errorStr = "STATUS_FEATURE_NOT_FLOAT"; break;
                case GEV_STATUS_FEATURE_NOT_INTEGER: errorStr = "STATUS_FEATURE_NOT_INTEGER"; break;
                case GEV_STATUS_XML_DLL_NOT_FOUND: errorStr = "STATUS_XML_DLL_NOT_FOUND"; break;
                case GEV_STATUS_XML_NOT_INIT: errorStr = "STATUS_XML_NOT_INIT"; break;
                case GEV_STATUS_NOT_SAME_SUBNET: errorStr = "STATUS_NOT_SAME_SUBNET"; break;
                default: errorStr = "UNKNOWN"; break;
            }
        }
    }
}
