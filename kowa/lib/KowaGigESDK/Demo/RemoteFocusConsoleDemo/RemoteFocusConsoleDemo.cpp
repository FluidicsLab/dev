/*****************************************************************************/
/*
 *	RemoteFocusConsolDemo.cpp -- sample application to control RemoteFocus
 *
 *****************************************************************************
 * This sample demonstrates how to use the KowaExternalControlLibrary to
 * control RemoteFocus.
 * For reference of the uses Kowa library function, refer to its documentation.
 * The code is delivered "as is" without any warranty and can be freely used
 * for own applications.
 */
 /*****************************************************************************/
#if defined( __GNUC__ )
#include <termios.h>
#include <fcntl.h>
#include <pthread.h>
#include <inttypes.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <unistd.h>
#else
#define _CRT_SECURE_NO_WARNINGS
#define _WINSOCK_DEPRECATED_NO_WARNINGS
#pragma warning(disable: 4996)
#include <Winsock2.h>
#include <iphlpapi.h>
#include <conio.h>


#endif

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "include_opencv.hpp"
#include "KowaGigEVisionLib.h"	 // include KowaGigEVisionLib header file
#include "KowaExternalControlLib.h"	// include KowaExternalControlLib header file


#if defined( __GNUC__ )
int _kbhit();
int getch(void);
#endif

// if you want to use user buffer handling, enable RING_BUFFER define
//#define RING_BUFFER	1
#define BUFFER_COUNT	4

// Acquisition thread parameter
typedef struct
{
    BOOL Kill;
    BYTE Device;

}DEVICE_PARAMS, * PDEVICE_PARAMS;

#if defined( __GNUC__ )
typedef struct
{
    unsigned short	 bfType;
    u_int32_t		bfSize;
    unsigned short	 bfReserved1;
    unsigned short	 bfReserved2;
    u_int32_t		bfOffBits;
} __attribute__((packed)) BITMAPFILEHEADER;

typedef struct
{
    u_int32_t		biSize;
    u_int32_t		biWidth;
    u_int32_t		biHeight;
    unsigned short	biPlanes;
    unsigned short	biBitCount;
    u_int32_t		biCompression;
    u_int32_t		biSizeImage;
    u_int32_t		biXPelsPerMeter;
    u_int32_t		biYPelsPerMeter;
    u_int32_t		biClrUsed;
    u_int32_t		biClrImportant;
} BITMAPINFOHEADER;

typedef struct
{
    unsigned char rgbRed;
    unsigned char rgbGreen;
    unsigned char rgbBlue;
    unsigned char rgbReserved;
} RGBQUAD;

#define Sleep sleep
#define FALSE 0
#define TRUE 1
#endif

// global variables
DEVICE_PARAMS DeviceParams;
DWORD mod_count;

// functions
void get_error(BYTE camera, WORD error, char* err_str);
ERROR_CALLBACK_FUNC error_callback_func(BYTE cam_nr, char* error_str);

// main program
int main(int argc, char* argv[])
{
    WORD error;
    DISCOVERY dis;
    int i;
    CONNECTION con;
    char l_str[150];
    BYTE camera = 1;
    struct sockaddr_in addr;

    // discovery devices on the net work.
    error = GEVDiscovery(&dis, NULL, 200, 0, 0);
    if (error)
    {
        printf("[ERROR] - GEVDiscovery error: %04X\n", error);
        return(0);
    }

    // if no device found exit application
    if (dis.Count == 0)
    {
        printf("[INFO] - No GigEDevice found. Exit with any key.\n");
        getch();
        return(0);
    }

    //Printf out discovered device number.
    printf("[INFO] - Count: %d\n", dis.Count);

    // Printf out device info of found devices
    for (i = 0; i < dis.Count; i++)
    {
        printf("\n\n");
        printf("[INFO] - Device: %d\n", i + 1);

        printf("[INFO] - %s\n", dis.param[i].manuf);
        printf("[INFO] - %s\n", dis.param[i].model);

        addr.sin_addr.s_addr = dis.param[i].IP;

        addr.sin_addr.s_addr = dis.param[i].AdapterIP;

        addr.sin_addr.s_addr = dis.param[i].AdapterMask;
    }

    // if we found more than one, select device you want to use
    if (dis.Count > 1)
    {
        printf("Select Device: ");
        if (scanf("%d", &i))
            camera = i;
        printf("camera: %d\n", camera);
#if defined( __GNUC__ )
        i = getch();
#else
        fflush(stdin);
#endif
    }

    // set CONNECTION parameter for GEVInit function
    con.AdapterIP = dis.param[camera - 1].AdapterIP;				// network adapter ip address
    con.AdapterMask = dis.param[camera - 1].AdapterMask;			// network	adapter mask
    con.IP_CANCam = dis.param[camera - 1].IP;						// device ip address
    con.PortCtrl = 49149;										// control port, set 0 to port than automatic port is use
    con.PortData = 49150;										// stream port, set 0 to port than automatic port is use
    strcpy(con.adapter_name, dis.param[camera - 1].adapter_name);	// name of network adapter


    // initialize GigE device
    // error_callback_func, this function gets information, warning and error strings from KowaGigEVisionLib
    error = GEVInit(camera, &con, (ERROR_CALLBACK_FUNC)error_callback_func, 0, EXCLUSIVE_ACCESS);
    // if error occured, exit application
    if (error)
    {
        get_error(camera, error, l_str);
        printf("[ERROR] - GEVInit: %s\n", l_str);
        return(0);
    }


#ifdef _DEBUG
    // if debug mode is used, set heartbeat to 10 seconds (needed for single-step execution)
    error = GEVSetHeartbeatRate(camera, 10000);
    if (error)
    {
        get_error(camera, error, l_str);
        printf("GEVSetHeartbeatRate error: %s\n", l_str);
        goto END;
    }
#endif

    // init xml parser
    error = GEVInitXml(camera);
    if (error)
    {
        get_error(camera, error, l_str);
        printf("[ERROR] - GEVInitXml error: %s\n", l_str);
        goto END;
    }

    // open stream channel of GigE device
    error = GEVOpenStreamChannel(camera, con.AdapterIP, con.PortData, 0);
    if (error)
    {
        get_error(camera, error, l_str);
        printf("[ERROR] - GEVOpenStreamChannel error: %s\n", l_str);
        goto END;
    }

    // disable packet resend
    error = GEVSetPacketResend(camera, 0);
    if (error)
    {
        get_error(camera, error, l_str);
        printf("[ERROR] - GEVSetPacketResend: %s\n", l_str);
        //goto END;
    }

    // set stream channel packet delay to 500 (default 0)
    error = GEVSetFeatureInteger(camera, (char*)"GevSCPD", 500);
    if (error)
    {
        get_error(camera, error, l_str);
        printf("[ERROR] - GEVSetFeatureInteger(GevSCPD): %s\n", l_str);
    }

    printf("[INFO] - Start acquisition continuous mode with any key.\n");
    printf("[INFO] - Cancel acquisition with any key.\n");
#if defined( __GNUC__ )
    getch();
#else
    _getch();
#endif

    DeviceParams.Device = camera;

    IMAGE_HEADER img_header;
    INT64 dw64;
    DWORD width, height, img_size;
    BYTE* ppixel[BUFFER_COUNT];
    DWORD acquisition_counter;
    DWORD img_counter;
    acquisition_counter = 0;
    img_counter = 0;
#ifdef RING_BUFFER
    BYTE index;
    index = 0;
    int i;
#endif

    ppixel[0] = NULL;

    // get current image width from the device
    error = GEVGetFeatureInteger(DeviceParams.Device, (char*)"Width", &dw64);
    if (error)
    {
        get_error(DeviceParams.Device, error, l_str);
        printf("[ERROR] - GEVGetFeatureInteger(Width) error: %s\n", l_str);
        goto AQ_END;
    }
    width = (DWORD)dw64;

    // get current image height from the device
    error = GEVGetFeatureInteger(DeviceParams.Device, (char*)"Height", &dw64);
    if (error)
    {
        get_error(DeviceParams.Device, error, l_str);
        printf("[ERROR] - GEVGetFeatureInteger(Height) error: %s\n", l_str);
        goto AQ_END;
    }
    height = (DWORD)dw64;

    // printf out image information is done by the KowaGigEVisionLib with error_callback_func function

    // get current image size (payload size) from the device
    error = GEVGetFeatureInteger(DeviceParams.Device, (char*)"PayloadSize", &dw64);
    if (error)
    {
        get_error(DeviceParams.Device, error, l_str);
        printf("[ERROR] - GEVGetFeatureInteger(PayloadSize) error: %s\n", l_str);
        goto AQ_END;
    }
    img_size = (int)dw64;

#ifdef RING_BUFFER
    // allocate memory for the user ring buffer, ringbuffer is handled by user application
    for (i = 0; i < BUFFER_COUNT; i++)
    {
        ppixel[i] = (BYTE*)malloc(img_size);
        GEVSetRingBuffer(DeviceParams.Device, i, ppixel[i]);	//used by function GEVGetImageRingBuffer
    }
#else
    // allocate memory for the image, ringbuffer is handled directly in library
    ppixel[0] = new BYTE[img_size * 4];							 //used by function GEVGetImageBuffer

#endif

    // Enable Filter Driver
    GEVInitFilterDriver(DeviceParams.Device);

    // Packet resend enable
    GEVSetPacketResend(DeviceParams.Device, 1);

    // start acquisition
    error = GEVAcquisitionStart(DeviceParams.Device, acquisition_counter);
    if (error)
    {
        get_error(DeviceParams.Device, error, l_str);
        printf("[ERROR] - GEVAcquisitionStart error: %s\n", l_str);
        goto AQ_END;
    }

    int key;
    key = 0;
    // PWM parameter
    int mode;			// 0:Manual 1:Strob
    int manual;			// 0:LED OFF 1:LED ON (in manual mode)
    int delay;			// triger delay
    int led_width;		// output time
    int duty;			// duty ratio index

    cv::namedWindow("frame");
    cv::createTrackbar("LED OFF/ON", "frame", &manual, 1);	cv::setTrackbarPos("LED OFF/ON", "frame", 0);
    cv::createTrackbar("mode", "frame", &mode, 1);	cv::setTrackbarPos("mode", "frame", 0);
    cv::createTrackbar("delay", "frame", &delay, 25);	cv::setTrackbarPos("delay", "frame", 0);
    cv::createTrackbar("width", "frame", &led_width, 30);	cv::setTrackbarPos("width", "frame", 0);
    cv::createTrackbar("duty", "frame", &duty, 15);	cv::setTrackbarPos("duty", "frame", 0);

    while (key != 'q')
    {
        short current_step_count = 0;

        // get image and header info
#ifdef RING_BUFFER
        error = GEVGetImageRingBuffer(DeviceParams.Device, &img_header, (WORD*)&index);
#else
        error = GEVGetImageBuffer(DeviceParams.Device, &img_header, ppixel[0]);
#endif
        if ((error) && (error != GEV_STATUS_GRAB_ERROR))
        {
            get_error(DeviceParams.Device, error, l_str);
            printf("[ERROR] - GEVGetImage: %s\n", l_str);
        }
        else
        {

#ifdef RING_BUFFER
            // queued user buffer
            GEVQueueRingBuffer(DeviceParams.Device, index);
#endif

            img_counter++;

            // RemoteFocus Control

            // get current step count
            RemoteFocusGetStepCount(DeviceParams.Device, &current_step_count);

            // LED Control
            manual = cv::getTrackbarPos("LED OFF/ON", "frame");
            mode = cv::getTrackbarPos("mode", "frame");
            delay = cv::getTrackbarPos("delay", "frame");
            led_width = cv::getTrackbarPos("width", "frame");
            duty = cv::getTrackbarPos("duty", "frame");
            // set PWM parameter
            PwmSetParameter(DeviceParams.Device, mode, delay * 100, led_width * 20000, duty);
            // LED trun on/off (in manual mode)
            PwmSetManualCtrl(DeviceParams.Device, manual);


            cv::Mat frame((int)height, (int)width, CV_8U, *ppixel);
            cv::Mat center(frame, cv::Rect((width / 2 - 320), (height / 2 - 240), 640, 480));
            cv::resize(frame, frame, cv::Size(640, 480), (0, 0), (0, 0), cv::INTER_AREA);
            cv::cvtColor(frame, frame, cv::COLOR_GRAY2BGR);

            cv::putText(frame, "Step Count : " + std::to_string(current_step_count), cv::Point(0, height / 40), cv::FONT_HERSHEY_SIMPLEX, 0.7, cv::Scalar(255, 200, 0));

            cv::putText(frame, "Keyboard Ctrl", cv::Point(0, frame.rows * 16 / 25), cv::FONT_HERSHEY_SIMPLEX, 0.6, cv::Scalar(255, 200, 0));
            cv::putText(frame, "[e]:Return to origin", cv::Point(0, frame.rows * 17 / 25), cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(255, 200, 0));
            cv::putText(frame, "[a]:Increase 1 step", cv::Point(0, frame.rows * 18 / 25), cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(255, 200, 0));
            cv::putText(frame, "[s]:Increase 10 step", cv::Point(0, frame.rows * 19 / 25), cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(255, 200, 0));
            cv::putText(frame, "[d]:Increase 100 step", cv::Point(0, frame.rows * 20 / 25), cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(255, 200, 0));
            cv::putText(frame, "[z]:Decrease 1 step", cv::Point(0, frame.rows * 21 / 25), cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(255, 200, 0));
            cv::putText(frame, "[x]:Decrease 10 step", cv::Point(0, frame.rows * 22 / 25), cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(255, 200, 0));
            cv::putText(frame, "[c]:Decrease 100 step", cv::Point(0, frame.rows * 23 / 25), cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(255, 200, 0));
            cv::putText(frame, "[q]:Exit", cv::Point(0, frame.rows * 24 / 25), cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(255, 200, 0));

            cv::imshow("frame", frame);
            cv::imshow("center", center);
            key = cv::waitKey(1);
            switch (key)
            {
            case 'e':
                // send a command return to origin
                RemoteFocusSetOrigin(DeviceParams.Device);
                break;
            case 'a':
                // add 1 step count
                RemoteFocusAddStepCount(DeviceParams.Device, 1);
                break;
            case 's':
                // add 10 step count
                RemoteFocusAddStepCount(DeviceParams.Device, 10);
                break;
            case 'd':
                // add 100 step count
                RemoteFocusAddStepCount(DeviceParams.Device, 100);
                break;
            case 'z':
                // subtract 1 step count
                RemoteFocusSubStepCount(DeviceParams.Device, 1);
                break;
            case 'x':
                // subtract 10 step count
                RemoteFocusSubStepCount(DeviceParams.Device, 10);
                break;
            case 'c':
                // subtract 100 step count
                RemoteFocusSubStepCount(DeviceParams.Device, 100);
                break;
            default:
                break;
            }
        }

        if (acquisition_counter)
        {
            if (img_counter >= acquisition_counter)
                key = 'q';
        }
    }

    // LED OFF (in manual mode)
    PwmSetManualCtrl(DeviceParams.Device, 0);

    cv::destroyAllWindows();

    // stop acquisition
    error = GEVAcquisitionStop(DeviceParams.Device);
    if (error)
    {
        get_error(DeviceParams.Device, error, l_str);
        printf("[ERROR] - GEVAcquisitionStop: %s\n", l_str);
        goto AQ_END;
    }
AQ_END:

#ifdef RING_BUFFER
    // free user ring buffer memory
    if (ppixel[0])
    {
        for (i = 0; i < BUFFER_COUNT; i++)
            free(ppixel[i]);
    }
    GEVReleaseRingBuffer(DeviceParams.Device);
#else
    // free image memory
    if (ppixel[0])
        delete ppixel[0];
#endif

    // run acquisition as long as no key was pressed
    while (!_kbhit())
        Sleep(0);

#if defined( __GNUC__ )
    getch();
#else
    _getch();
#endif

END:

    printf("[INFO] - Exit application with any key.\n");

#if defined( __GNUC__ )
    getch();
#else
    _getch();
#endif

    // close stream channel
    GEVCloseStreamChannel(camera);
    // close GigE device
    GEVClose(camera);
    return 0;
}

// function to return error string
void get_error(BYTE camera, WORD error, char* err_str)
{
    switch (error)
    {
    case GEV_STATUS_NOT_IMPLEMENTED: strcpy(err_str, "STATUS_NOT_IMPLEMENTED"); break;
    case GEV_STATUS_INVALID_PARAMETER: strcpy(err_str, "STATUS_INVALID_PARAMETER"); break;
    case GEV_STATUS_INVALID_ADDRESS: strcpy(err_str, "STATUS_INVALID_ADDRESS"); break;
    case GEV_STATUS_WRITE_PROTECT: strcpy(err_str, "STATUS_WRITE_PROTECT"); break;
    case GEV_STATUS_BAD_ALIGNMENT: strcpy(err_str, "STATUS_BAD_ALIGNMENT"); break;
    case GEV_STATUS_ACCESS_DENIED: strcpy(err_str, "STATUS_ACCESS_DENIED"); break;
    case GEV_STATUS_BUSY: strcpy(err_str, "STATUS_BUSY"); break;
    case GEV_STATUS_LOCAL_PROBLEM: strcpy(err_str, "STATUS_LOCAL_PROBLEM"); break;
    case GEV_STATUS_MSG_MISMATCH: strcpy(err_str, "STATUS_MSG_MISMATCH"); break;
    case GEV_STATUS_INVALID_PROTOCOL: strcpy(err_str, "STATUS_INVALID_PROTOCOL"); break;
    case GEV_STATUS_NO_MSG: strcpy(err_str, "STATUS_NO_MSG"); break;
    case GEV_STATUS_PACKET_UNAVAILABLE: strcpy(err_str, "STATUS_PACKET_UNAVAILABLE"); break;
    case GEV_STATUS_DATA_OVERRUN: strcpy(err_str, "STATUS_DATA_OVERRUN"); break;
    case GEV_STATUS_INVALID_HEADER: strcpy(err_str, "STATUS_INVALID_HEADER"); break;
    case GEV_STATUS_WRONG_CONFIG: strcpy(err_str, "STATUS_WRONG_CONFIG"); break;
    case GEV_STATUS_PACKET_NOT_YET_AVAILABLE: strcpy(err_str, "STATUS_PACKET_NOT_YET_AVAILABLE"); break;
    case GEV_STATUS_PACKET_AND_PREV_REMOVED_FROM_MEMORY: strcpy(err_str, "STATUS_PACKET_AND_PREV_REMOVED_FROM_MEMORY"); break;
    case GEV_STATUS_PACKET_REMOVED_FROM_MEMORY: strcpy(err_str, "STATUS_PACKET_REMOVED_FROM_MEMORY"); break;
    case GEV_STATUS_ERROR: strcpy(err_str, "STATUS_ERROR"); break;

    case GEV_STATUS_CAMERA_NOT_INIT: strcpy(err_str, "STATUS_CAMERA_NOT_INIT"); break;
    case GEV_STATUS_CAMERA_ALWAYS_INIT: strcpy(err_str, "STATUS_CAMERA_ALWAYS_INIT"); break;
    case GEV_STATUS_CANNOT_CREATE_SOCKET: strcpy(err_str, "STATUS_CANNOT_CREATE_SOCKET"); break;
    case GEV_STATUS_SEND_ERROR: strcpy(err_str, "STATUS_SEND_ERROR"); break;
    case GEV_STATUS_RECEIVE_ERROR: strcpy(err_str, "STATUS_RECEIVE_ERROR"); break;
    case GEV_STATUS_CANNOT_ALLOC_MEMORY: strcpy(err_str, "STATUS_CANNOT_ALLOC_MEMORY"); break;
    case GEV_STATUS_TIMEOUT: strcpy(err_str, "STATUS_TIMEOUT"); break;
    case GEV_STATUS_SOCKET_ERROR: strcpy(err_str, "STATUS_SOCKET_ERROR"); break;
    case GEV_STATUS_INVALID_ACK: strcpy(err_str, "STATUS_INVALID_ACK"); break;
    case GEV_STATUS_CANNOT_START_THREAD: strcpy(err_str, "STATUS_CANNOT_START_THREAD"); break;
    case GEV_STATUS_CANNOT_SET_SOCKET_OPT: strcpy(err_str, "STATUS_CANNOT_SET_SOCKET_OPT"); break;
    case GEV_STATUS_CANNOT_OPEN_DRIVER: strcpy(err_str, "STATUS_CANNOT_OPEN_DRIVER"); break;
    case GEV_STATUS_HEARTBEAT_READ_ERROR: strcpy(err_str, "STATUS_HEARTBEAT_READ_ERROR"); break;
    case GEV_STATUS_EVALUATION_EXPIRED: strcpy(err_str, "STATUS_EVALUATION_EXPIRED"); break;
    case GEV_STATUS_GRAB_ERROR: strcpy(err_str, "STATUS_GRAB_ERROR"); break;
    case GEV_STATUS_XML_READ_ERROR: strcpy(err_str, "STATUS_XML_READ_ERROR"); break;
    case GEV_STATUS_XML_OPEN_ERROR: strcpy(err_str, "STATUS_XML_OPEN_ERROR"); break;
    case GEV_STATUS_XML_FEATURE_ERROR: strcpy(err_str, "STATUS_XML_FEATURE_ERROR"); break;
    case GEV_STATUS_XML_COMMAND_ERROR: strcpy(err_str, "STATUS_XML_COMMAND_ERROR"); break;
    case GEV_STATUS_GAIN_NOT_SUPPORTED: strcpy(err_str, "STATUS_GAIN_NOT_SUPPORTED"); break;
    case GEV_STATUS_EXPOSURE_NOT_SUPPORTED: strcpy(err_str, "STATUS_EXPOSURE_NOT_SUPPORTED"); break;
    case GEV_STATUS_CANNOT_GET_ADAPTER_INFO: strcpy(err_str, "STATUS_CANNOT_GET_ADAPTER_INFO"); break;
    case GEV_STATUS_ERROR_INVALID_HANDLE: strcpy(err_str, "STATUS_ERROR_INVALID_HANDLE"); break;
    case GEV_STATUS_CLINK_SET_BAUD: strcpy(err_str, "STATUS_CLINK_SET_BAUD"); break;
    case GEV_STATUS_CLINK_SEND_BUFFER_FULL: strcpy(err_str, "STATUS_CLINK_SEND_BUFFER_FULL"); break;
    case GEV_STATUS_CLINK_RECEIVE_BUFFER_NO_DATA: strcpy(err_str, "STATUS_CLINK_REVEICE_BUFFER_NO_DATA"); break;
    case GEV_STATUS_FEATURE_NOT_AVAILABLE: strcpy(err_str, "STATUS_FEATURE_NOT_AVAILABLE"); break;
    case GEV_STATUS_MATH_PARSER_ERROR: strcpy(err_str, "STATUS_MATH_PARSER_ERROR"); break;
    case GEV_STATUS_FEATURE_ITEM_NOT_AVAILABLE: strcpy(err_str, "STATUS_FEATURE_ITEM_NOT_AVAILABLE"); break;
    case GEV_STATUS_NOT_SUPPORTED: strcpy(err_str, "STATUS_NOT_SUPPORTED"); break;
    case GEV_STATUS_GET_URL_ERROR: strcpy(err_str, "STATUS_GET_URL_ERROR"); break;
    case GEV_STATUS_READ_XML_MEM_ERROR: strcpy(err_str, "STATUS_READ_XML_MEM_ERROR"); break;
    case GEV_STATUS_XML_SIZE_ERROR: strcpy(err_str, "STATUS_XML_SIZE_ERROR"); break;
    case GEV_STATUS_XML_ZIP_ERROR: strcpy(err_str, "STATUS_XML_ZIP_ERROR"); break;
    case GEV_STATUS_XML_ROOT_ERROR: strcpy(err_str, "STATUS_XML_ROOT_ERROR"); break;
    case GEV_STATUS_XML_FILE_ERROR: strcpy(err_str, "STATUS_XML_FILE_ERROR"); break;
    case GEV_STATUS_DIFFERENT_IMAGE_HEADER: strcpy(err_str, "STATUS_DIFFERENT_IMAGE_HEADER"); break;
    case GEV_STATUS_XML_SCHEMA_ERROR: strcpy(err_str, "STATUS_XML_SCHEMA_ERROR"); break;
    case GEV_STATUS_XML_STYLESHEET_ERROR: strcpy(err_str, "STATUS_XML_STYLESHEET_ERROR"); break;
    case GEV_STATUS_FEATURE_LIST_ERROR: strcpy(err_str, "STATUS_FEATURE_LIST_ERROR"); break;
    case GEV_STATUS_ALREADY_OPEN: strcpy(err_str, "STATUS_ALLREADY_OPEN"); break;
    case GEV_STATUS_TEST_PACKET_DATA_ERROR: strcpy(err_str, "STATUS_TEST_PACKET_DATA_ERROR"); break;
    case GEV_STATUS_FEATURE_NOT_FLOAT: strcpy(err_str, "STATUS_FEATURE_NOT_FLOAT"); break;
    case GEV_STATUS_XML_DLL_NOT_FOUND: strcpy(err_str, "STATUS_XML_DLL_NOT_FOUND"); break;
    case GEV_STATUS_XML_NOT_INIT: strcpy(err_str, "STATUS_XML_NOT_INIT"); break;
    default: strcpy(err_str, "UNKNOWN");	printf("error: %X", error); break;
    }
}

// error callback funtion
ERROR_CALLBACK_FUNC  error_callback_func(BYTE cam_nr, char* error_str)
{
    printf("%s\n", error_str);
    return(0);
}


#if defined( __GNUC__ )
int _kbhit()
{
    // Get the parameters associated with STDIN_FILENO (= the default standard
    // input file descriptor number).
    struct termios OldConfig;
    // File descriptor number
    const int FileDescriptor = STDIN_FILENO;
    tcgetattr(FileDescriptor, &OldConfig);
    // Copy the original configuraiton.
    struct termios NewConfig(OldConfig);
    // Do not echo & disable canonical processing.
    NewConfig.c_lflag &= ~(ICANON | ECHO);
    // Apply new configuration.
    tcsetattr(FileDescriptor, TCSANOW, &NewConfig);
    // Get the file status flags and file access modes.
    int OldFlags = fcntl(FileDescriptor, F_GETFL, 0);
    // Set the file status flags; set non-blocking.
    fcntl(FileDescriptor, F_SETFL, OldFlags | O_NONBLOCK);
    // Get an input.
    int Ch = getchar();
    // Revert STDIN_FILENO to the original configuration.
    tcsetattr(FileDescriptor, TCSANOW, &OldConfig);
    fcntl(FileDescriptor, F_SETFL, OldFlags);
    // Check the character if it's a chanracter which is not EOF.
    int Hit = 0; // false
    if (Ch != EOF) {
        // Put it back to evaluate it at the following block.
        ungetc(Ch, stdin);
        Hit = 1; // true: Hit a valid character.
    }
    return Hit;
}

int getch(void)
{
    int c = 0;

    struct termios org_opts, new_opts;
    int res = 0;
    //-----	store old settings -----------
    res = tcgetattr(STDIN_FILENO, &org_opts);
    //---- set new terminal parms --------
    memcpy(&new_opts, &org_opts, sizeof(new_opts));
    new_opts.c_lflag &= ~(ICANON | ECHO | ECHOE | ECHOK | ECHONL | ECHOPRT | ECHOKE | ICRNL);
    tcsetattr(STDIN_FILENO, TCSANOW, &new_opts);
    c = getchar();
    //------	restore old settings ---------
    res = tcsetattr(STDIN_FILENO, TCSANOW, &org_opts);
    return(c);
}
#endif
