/*****************************************************************************/
/*
 *  Utils.cpp -- utils for sample application
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
#include <sys/errno.h>
#else
#include "stdafx.h"
#include <Winsock2.h>
#include <windows.h>
#include <iphlpapi.h>
#include <conio.h>
#include <direct.h>
#endif

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <sys/types.h>
#include <sys/stat.h>

#include "KowaGigEVisionLib.h"   // include KowaGigEVisionLib header file


#include "Utils.h"

// function to return error string
void get_error(BYTE camera, WORD error, char *err_str)
{
  switch(error)
  {
      case GEV_STATUS_NOT_IMPLEMENTED: strcpy(err_str,"STATUS_NOT_IMPLEMENTED"); break;
      case GEV_STATUS_INVALID_PARAMETER: strcpy(err_str,"STATUS_INVALID_PARAMETER"); break;
      case GEV_STATUS_INVALID_ADDRESS: strcpy(err_str,"STATUS_INVALID_ADDRESS"); break;
      case GEV_STATUS_WRITE_PROTECT: strcpy(err_str,"STATUS_WRITE_PROTECT"); break;
      case GEV_STATUS_BAD_ALIGNMENT: strcpy(err_str,"STATUS_BAD_ALIGNMENT"); break;
      case GEV_STATUS_ACCESS_DENIED: strcpy(err_str,"STATUS_ACCESS_DENIED"); break;
      case GEV_STATUS_BUSY: strcpy(err_str,"STATUS_BUSY"); break;
      case GEV_STATUS_LOCAL_PROBLEM: strcpy(err_str,"STATUS_LOCAL_PROBLEM"); break;
      case GEV_STATUS_MSG_MISMATCH: strcpy(err_str,"STATUS_MSG_MISMATCH"); break;
      case GEV_STATUS_INVALID_PROTOCOL: strcpy(err_str,"STATUS_INVALID_PROTOCOL"); break;
      case GEV_STATUS_NO_MSG: strcpy(err_str,"STATUS_NO_MSG"); break;
      case GEV_STATUS_PACKET_UNAVAILABLE: strcpy(err_str,"STATUS_PACKET_UNAVAILABLE"); break;
      case GEV_STATUS_DATA_OVERRUN: strcpy(err_str,"STATUS_DATA_OVERRUN"); break;
      case GEV_STATUS_INVALID_HEADER: strcpy(err_str,"STATUS_INVALID_HEADER"); break;
      case GEV_STATUS_WRONG_CONFIG: strcpy(err_str,"STATUS_WRONG_CONFIG"); break;
      case GEV_STATUS_PACKET_NOT_YET_AVAILABLE: strcpy(err_str,"STATUS_PACKET_NOT_YET_AVAILABLE"); break;
      case GEV_STATUS_PACKET_AND_PREV_REMOVED_FROM_MEMORY: strcpy(err_str,"STATUS_PACKET_AND_PREV_REMOVED_FROM_MEMORY"); break;
      case GEV_STATUS_PACKET_REMOVED_FROM_MEMORY: strcpy(err_str,"STATUS_PACKET_REMOVED_FROM_MEMORY"); break;
      case GEV_STATUS_ERROR: strcpy(err_str,"STATUS_ERROR"); break;

      case GEV_STATUS_CAMERA_NOT_INIT: strcpy(err_str,"STATUS_CAMERA_NOT_INIT"); break;
      case GEV_STATUS_CAMERA_ALWAYS_INIT: strcpy(err_str,"STATUS_CAMERA_ALWAYS_INIT"); break;
      case GEV_STATUS_CANNOT_CREATE_SOCKET: strcpy(err_str,"STATUS_CANNOT_CREATE_SOCKET"); break;
      case GEV_STATUS_SEND_ERROR: strcpy(err_str,"STATUS_SEND_ERROR"); break;
      case GEV_STATUS_RECEIVE_ERROR: strcpy(err_str,"STATUS_RECEIVE_ERROR"); break;
      case GEV_STATUS_CANNOT_ALLOC_MEMORY: strcpy(err_str,"STATUS_CANNOT_ALLOC_MEMORY"); break;
      case GEV_STATUS_TIMEOUT: strcpy(err_str,"STATUS_TIMEOUT"); break;
      case GEV_STATUS_SOCKET_ERROR: strcpy(err_str,"STATUS_SOCKET_ERROR"); break;
      case GEV_STATUS_INVALID_ACK: strcpy(err_str,"STATUS_INVALID_ACK"); break;
      case GEV_STATUS_CANNOT_START_THREAD: strcpy(err_str,"STATUS_CANNOT_START_THREAD"); break;
      case GEV_STATUS_CANNOT_SET_SOCKET_OPT: strcpy(err_str,"STATUS_CANNOT_SET_SOCKET_OPT"); break;
      case GEV_STATUS_CANNOT_OPEN_DRIVER: strcpy(err_str,"STATUS_CANNOT_OPEN_DRIVER"); break;
      case GEV_STATUS_HEARTBEAT_READ_ERROR: strcpy(err_str,"STATUS_HEARTBEAT_READ_ERROR"); break;
      case GEV_STATUS_EVALUATION_EXPIRED: strcpy(err_str,"STATUS_EVALUATION_EXPIRED"); break;
      case GEV_STATUS_GRAB_ERROR: strcpy(err_str,"STATUS_GRAB_ERROR"); break;
      case GEV_STATUS_XML_READ_ERROR: strcpy(err_str,"STATUS_XML_READ_ERROR"); break;
      case GEV_STATUS_XML_OPEN_ERROR: strcpy(err_str,"STATUS_XML_OPEN_ERROR"); break;
      case GEV_STATUS_XML_FEATURE_ERROR: strcpy(err_str,"STATUS_XML_FEATURE_ERROR"); break;
      case GEV_STATUS_XML_COMMAND_ERROR: strcpy(err_str,"STATUS_XML_COMMAND_ERROR"); break;
      case GEV_STATUS_GAIN_NOT_SUPPORTED: strcpy(err_str,"STATUS_GAIN_NOT_SUPPORTED"); break;
      case GEV_STATUS_EXPOSURE_NOT_SUPPORTED: strcpy(err_str,"STATUS_EXPOSURE_NOT_SUPPORTED"); break;
      case GEV_STATUS_CANNOT_GET_ADAPTER_INFO: strcpy(err_str,"STATUS_CANNOT_GET_ADAPTER_INFO"); break;
      case GEV_STATUS_ERROR_INVALID_HANDLE: strcpy(err_str,"STATUS_ERROR_INVALID_HANDLE"); break;
      case GEV_STATUS_CLINK_SET_BAUD: strcpy(err_str,"STATUS_CLINK_SET_BAUD"); break;
      case GEV_STATUS_CLINK_SEND_BUFFER_FULL: strcpy(err_str,"STATUS_CLINK_SEND_BUFFER_FULL"); break;
      case GEV_STATUS_CLINK_RECEIVE_BUFFER_NO_DATA: strcpy(err_str,"STATUS_CLINK_REVEICE_BUFFER_NO_DATA"); break;
      case GEV_STATUS_FEATURE_NOT_AVAILABLE: strcpy(err_str,"STATUS_FEATURE_NOT_AVAILABLE"); break;
      case GEV_STATUS_MATH_PARSER_ERROR: strcpy(err_str,"STATUS_MATH_PARSER_ERROR"); break;
      case GEV_STATUS_FEATURE_ITEM_NOT_AVAILABLE: strcpy(err_str,"STATUS_FEATURE_ITEM_NOT_AVAILABLE"); break;
      case GEV_STATUS_NOT_SUPPORTED: strcpy(err_str,"STATUS_NOT_SUPPORTED"); break;
      case GEV_STATUS_GET_URL_ERROR: strcpy(err_str,"STATUS_GET_URL_ERROR"); break;
      case GEV_STATUS_READ_XML_MEM_ERROR: strcpy(err_str,"STATUS_READ_XML_MEM_ERROR"); break;
      case GEV_STATUS_XML_SIZE_ERROR: strcpy(err_str,"STATUS_XML_SIZE_ERROR"); break;
      case GEV_STATUS_XML_ZIP_ERROR: strcpy(err_str,"STATUS_XML_ZIP_ERROR"); break;
      case GEV_STATUS_XML_ROOT_ERROR: strcpy(err_str,"STATUS_XML_ROOT_ERROR"); break;
      case GEV_STATUS_XML_FILE_ERROR: strcpy(err_str,"STATUS_XML_FILE_ERROR"); break;
      case GEV_STATUS_DIFFERENT_IMAGE_HEADER: strcpy(err_str,"STATUS_DIFFERENT_IMAGE_HEADER"); break;
      case GEV_STATUS_XML_SCHEMA_ERROR: strcpy(err_str,"STATUS_XML_SCHEMA_ERROR"); break;
      case GEV_STATUS_XML_STYLESHEET_ERROR: strcpy(err_str,"STATUS_XML_STYLESHEET_ERROR"); break;
      case GEV_STATUS_FEATURE_LIST_ERROR: strcpy(err_str,"STATUS_FEATURE_LIST_ERROR"); break;
      case GEV_STATUS_ALREADY_OPEN: strcpy(err_str,"STATUS_ALLREADY_OPEN"); break;
      case GEV_STATUS_TEST_PACKET_DATA_ERROR: strcpy(err_str,"STATUS_TEST_PACKET_DATA_ERROR"); break;
      case GEV_STATUS_FEATURE_NOT_FLOAT: strcpy(err_str,"STATUS_FEATURE_NOT_FLOAT"); break;
      case GEV_STATUS_XML_DLL_NOT_FOUND: strcpy(err_str,"STATUS_XML_DLL_NOT_FOUND"); break;
      case GEV_STATUS_XML_NOT_INIT: strcpy(err_str,"STATUS_XML_NOT_INIT"); break;
      default: strcpy(err_str,"UNKNOWN");  printf("error: %X",error); break;
  }
}

// function to save image
unsigned short save_bmp(char *fname, DWORD w, DWORD h, BYTE bpp, BYTE *ppixel)
{
  BITMAPFILEHEADER bmpfilehdr;
  BITMAPINFOHEADER bmpinfohdr;
  int i,bpp_h,h_off;
  int size, width, height;
  FILE *hfile;
  BYTE *phelp,lbpp;
  RGBQUAD pal1;

  if ((hfile = fopen(fname,"w+b" )) == NULL)
    return(1);

  if(bpp == 16)
    lbpp = 8;
  else
    lbpp = bpp;

  bpp_h = lbpp / 8;
  if(lbpp == 8)
   h_off = 1024;
  else
   h_off = 0;

  width  = (int)w;
  height = (int)h;
  size   = (width * bpp_h) * height;

  // build bmp headers
  bmpfilehdr.bfType = 0x4D42;
  bmpfilehdr.bfSize = size + sizeof(BITMAPINFOHEADER) + (sizeof(BITMAPFILEHEADER)) + h_off;
  bmpfilehdr.bfReserved1 = 0;
  bmpfilehdr.bfReserved2 = 0;
  bmpfilehdr.bfOffBits = sizeof(BITMAPINFOHEADER) + (sizeof(BITMAPFILEHEADER)) + h_off;

  bmpinfohdr.biSize = sizeof(BITMAPINFOHEADER);
  bmpinfohdr.biWidth = width;
  bmpinfohdr.biHeight = height;
  bmpinfohdr.biPlanes = 1;
  bmpinfohdr.biBitCount = lbpp;
  bmpinfohdr.biCompression = 0;
  bmpinfohdr.biSizeImage = size;
  bmpinfohdr.biXPelsPerMeter = 0;
  bmpinfohdr.biYPelsPerMeter = 0;

   if(bpp == 8)
   {
     bmpinfohdr.biClrUsed = 256;
     bmpinfohdr.biClrImportant = 256;
   }
   else
   {
     bmpinfohdr.biClrUsed = 0;
     bmpinfohdr.biClrImportant = 0;
   }

  if(fwrite( (unsigned char *)&bmpfilehdr, sizeof(BITMAPFILEHEADER),1,hfile) == 0)
    return(2);

  if(fwrite( (unsigned char *)&bmpinfohdr, sizeof(BITMAPINFOHEADER),1,hfile) == 0)
    return(2);

   if(lbpp == 8)
   {
      // Palette init.
      for(i = 0;i < 256;i++)
      {
         pal1.rgbRed = (unsigned char)i;
         pal1.rgbGreen = (unsigned char)i;
         pal1.rgbBlue = (unsigned char)i;
         pal1.rgbReserved = 0;
         if(fwrite(&pal1, sizeof(RGBQUAD),1,hfile) == 0)
            return(2);
      }
   }

   for(i = height - 1; i >= 0 ;i--)
   {
    phelp = ppixel + ((width * bpp_h) * i);
    if(fwrite(phelp,(width * bpp_h),1,hfile) == 0)
      return(2);
   }
   fclose(hfile);

   return(0);
}

// error callback funtion
BYTE WINAPI error_callback_func(BYTE cam_nr, char *error_str, BYTE detailed_log)
{
  printf("%s\n",error_str);
  return(0);
}

// message channel callback funtion
BYTE WINAPI msg_callback_func(BYTE cam_nr, MESSAGECHANNEL_PARAMETER mcparam)
{
  char l_str[150], id_str[20];
  int i;

  sprintf(l_str,"[INFO] - Message Channel Device %d -> ",cam_nr);
  switch (mcparam.EventID)
  {
    case EVENT_TRIGGER: strcat(l_str,"trigger event");
                 break;
    case EVENT_START_EXPOSURE: strcat(l_str,"start of exposure");
                 break;
    case EVENT_STOP_EXPOSURE: strcat(l_str,"end of exposure");
                 break;
    case EVENT_START_TRANSFER: strcat(l_str,"stream channel start of transfer");
                 break;
    case EVENT_STOP_TRANSFER: strcat(l_str,"stream channel end of transfer");
                 break;
    case EVENT_PRIMARY_APP_SWITCH: strcat(l_str,"primary application switchover has been granted.");
                 break;
    case EVENT_LINK_SPEED_CHANGE: strcat(l_str,"indicates that the link speed has changed.");
                 break;
    case EVENT_ACTION_LATE: strcat(l_str,"execution of a Scheduled Action Command was late");
                 break;
    default:     if ((mcparam.EventID >= EVENT_ERROR_BEGIN) && (mcparam.EventID <= EVENT_ERROR_END))
                 {
                    strcat(l_str,"error event");
                    break;
                 }
                 if (mcparam.EventID >= EVENT_DEVICE_SPECIFIC)
                 {
                    strcat(l_str,"device-specific event: ");
                    sprintf(id_str,"0x%04X",mcparam.EventID);
                    strcat(l_str, id_str);
                    break;
                 }
                 strcpy(l_str,"unknown event");
                 break;
  }

  if(mcparam.DataLength)
  {
    printf("Event: len: %d\n",mcparam.DataLength);
    for(i = 0;i < mcparam.DataLength;i++)
      printf("Event: data: %02X\n",mcparam.Data[i]);
  }

  printf("%s\n", l_str);
  return(0);
}

int dir_exists(const char* const path)
{
  struct stat info;

  int statRC = stat(path, &info);
  if (statRC != 0)
  {
    if (errno == ENOENT) { return 0; } // something along the path does not exist
    if (errno == ENOTDIR) { return 0; } // something in path prefix is not a dir
    return -1;
  }

  return (info.st_mode & S_IFDIR) ? 1 : 0;
}

void create_dir(char* dir_name) {
#if defined _MSC_VER
  _mkdir(dir_name);
#elif defined __GNUC__
  mkdir(dir_name, 0777);
#endif
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
  int c=0;

  struct termios org_opts, new_opts;
  int res=0;
          //-----  store old settings -----------
  res=tcgetattr(STDIN_FILENO, &org_opts);
	if(res != 0)
		return(0);
  //---- set new terminal parms --------
  memcpy(&new_opts, &org_opts, sizeof(new_opts));
  new_opts.c_lflag &= ~(ICANON | ECHO | ECHOE | ECHOK | ECHONL | ECHOPRT | ECHOKE | ICRNL);
  tcsetattr(STDIN_FILENO, TCSANOW, &new_opts);
  c=getchar();
  //------  restore old settings ---------
  res=tcsetattr(STDIN_FILENO, TCSANOW, &org_opts);
	if(res != 0)
		return(0);
  return(c);
}
#endif
