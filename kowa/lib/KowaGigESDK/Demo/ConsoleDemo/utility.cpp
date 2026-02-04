#include "KowaGigEVisionLib.h"   // include KowaGigEVisionLib header file
#include "utility.h"


#include <fstream>

#pragma pack(push, 1)
struct BITMAPFILEHEADER {
    uint16_t bfType = 0x4d42;
    uint32_t bfSize;
    uint16_t bfReserved1 = 0;
    uint16_t bfReserved2 = 0;
    uint32_t bfOffBits = 54;
};
struct BITMAPINFOHEADER {
    uint32_t biSize = 40;
    uint32_t biWidth;
    uint32_t biHeight;
    uint16_t biPlanes = 1;
    uint16_t biBitCount;
    uint32_t biCompression = 0;
    uint32_t biSizeImage;
    uint32_t biXPelsPerMeter = 0;
    uint32_t biYPelsPerMeter = 0;
    uint32_t biClrUsed = 0;
    uint32_t biClrImportant = 0;
};
#pragma pack(pop)

struct Pallet {
    uint8_t b;
    uint8_t g;
    uint8_t r;
    uint8_t reserved;
};

#include <array>
static std::array<Pallet, 256> make_pallet_mono(){
    std::array<Pallet, 256> ret;
    for (int i = 0; i < 256; ++i) {
        auto c = static_cast<uint8_t>(i);
        ret[i] = Pallet{c,c,c,0};
    }
    return ret;
}

// return: errno
int save_mono_bitmap(const std::string& filename, int height, int width, int width_stride, const char* data) {
    // Note:
    //     eog(Ubuntu image viewer) needs image pallet for mono8 image.
    int ceil_width = (width - 1 + 4) / 4 * 4;
    std::array<Pallet, 256> mono8pallet = make_pallet_mono();
    BITMAPFILEHEADER bf;
    BITMAPINFOHEADER bi;
    bi.biWidth = width;
    bi.biHeight = height;

    bi.biBitCount = 8;
    bi.biSizeImage = ceil_width * height;
    bf.bfOffBits = sizeof(bf) + sizeof(bi) + sizeof(mono8pallet);
    bi.biClrUsed = 256;
    bi.biClrImportant = 256;
    bf.bfSize = bi.biSizeImage + bf.bfOffBits + sizeof(mono8pallet);

    std::ofstream os(filename,
                     std::ios::binary |
                     std::ios::out);
    if (!os) return errno;
    if (!os.write(reinterpret_cast<const char*>(&bf), sizeof(bf))) return errno;
    if (!os.write(reinterpret_cast<const char*>(&bi), sizeof(bi))) return errno;
    if (!os.write(reinterpret_cast<const char*>(&mono8pallet), sizeof(mono8pallet))) return errno;


    // Note: Bitmap pixeldata are stored "bottom-up".
    const char* pdata = data + ceil_width * (height - 1);
    char padding[] = {0, 0, 0};
    int padding_length = ceil_width - width;
    for (int y = 0; y < height; ++y, pdata -= width_stride) {
        if (!os.write(pdata, width)) return errno;
        if (!os.write(padding, padding_length)) return errno;
    }
    return 0;
}
