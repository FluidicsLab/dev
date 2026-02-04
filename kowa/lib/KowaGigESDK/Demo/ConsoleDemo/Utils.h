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
#ifndef __UTILS_H
#define __UTILS_H

#if defined( __GNUC__ )
typedef struct
{
  unsigned short   bfType;
  u_int32_t    bfSize;
  unsigned short   bfReserved1;
  unsigned short   bfReserved2;
  u_int32_t    bfOffBits;
} __attribute__((packed)) BITMAPFILEHEADER;

typedef struct
{
  u_int32_t           biSize;
  u_int32_t           biWidth;
  u_int32_t           biHeight;
  unsigned short          biPlanes;
  unsigned short          biBitCount;
  u_int32_t           biCompression;
  u_int32_t           biSizeImage;
  u_int32_t           biXPelsPerMeter;
  u_int32_t           biYPelsPerMeter;
  u_int32_t           biClrUsed;
  u_int32_t          biClrImportant;
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

int _kbhit();
int getch(void);
#endif

void get_error(BYTE camera, WORD error, char *err_str);
unsigned short save_bmp(char *fname, DWORD w, DWORD h, BYTE bpp, BYTE *ppixel);
BYTE WINAPI error_callback_func(BYTE cam_nr, char *error_str, BYTE detailed_log);
BYTE WINAPI msg_callback_func(BYTE cam_nr, MESSAGECHANNEL_PARAMETER mcparam);
int dir_exists(const char* const path);
void create_dir(char* dir_name);

#endif
