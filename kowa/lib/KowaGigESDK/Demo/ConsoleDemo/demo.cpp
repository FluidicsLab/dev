#include "KowaGigEVisionLib.h"   // include KowaGigEVisionLib header file
#include "utility.h"


#include <memory>
#include <iostream>
#include <sstream>
#include <string>
#include <cstring>

std::unique_ptr<DISCOVERY> discovery() {
    WORD error;
    std::unique_ptr<DISCOVERY> dis(new DISCOVERY);

    // discovery devices, auto port
    if ((error = GEVDiscovery(dis.get(), NULL, 200, 0, 0)) != 0) {
        std::cerr
            << "[ERROR] - GEVDiscovery: "
            << get_strerror(error)
            << std::endl;
        return nullptr;
    }

    return dis;
}

CONNECTION make_connection(const DEVICE_PARAM& dev){
    CONNECTION ret;
    ret.AdapterIP = dev.AdapterIP;
    ret.AdapterMask = dev.AdapterMask;
    ret.IP_CANCam = dev.IP;
    ret.PortCtrl = 0;
    ret.PortData = 0;
    ret.PortMessage = 0;
    strncpy(ret.adapter_name, dev.adapter_name, sizeof(ret.adapter_name));
    return ret;
}

std::string inetaddr2string(uint32_t addr) {
    // Note: addr is network byte order(bigendian).
    union c4 {
        uint32_t value;
        struct u8children {
            uint8_t a, b, c, d;
        }children;
    };
    c4 u{addr};

    std::ostringstream oss;
    oss
        << static_cast<int>(u.children.a) << "."
        << static_cast<int>(u.children.b) << "."
        << static_cast<int>(u.children.c) << "."
        << static_cast<int>(u.children.d);
    return oss.str();
}

std::ostream& operator<<(std::ostream&os, const DEVICE_PARAM& dev) {
    os
        << "("
        << dev.manuf << ", "
        << dev.model << ", "
        << dev.version << ", "
        << "IP=" << inetaddr2string(dev.IP) << ", "
        << "AdapterIP=" << inetaddr2string(dev.AdapterIP) << ", "
        << "AdapterMask=" << inetaddr2string(dev.AdapterMask) << ", "
        << "AdapterName=" << dev.adapter_name << ", "
        << "Status=" << (int)dev.status << ")";

    return os;
}

const DEVICE_PARAM* select_device(const DISCOVERY& dis) {
    for (int i = 0; i < dis.Count; ++i) {
        std::cout
            << "[INFO] - Device[" << i << "]: "
            << dis.param[i]
            << std::endl;
    }

    switch (dis.Count) {
    case 0:
        std::cout << "No GigE device found." << std::endl;
        return nullptr;
    case 1:
        return &dis.param[0];
    default: {
        int d = -1;
        while (std::cin) {
            std::cout
                << "select device(0-"
                << static_cast<int>(dis.Count) - 1
                << "): "
                << std::flush;
            std::cin >> d;
            if (0 <= d && d < dis.Count) {
                return &dis.param[d];
            }
        }
        return nullptr;
    }
    }
}

bool setupdevice(const KOWAGIGEVISION_CAMNR& cam, const CONNECTION& connection) {
    WORD error;
    if ((error = GEVInitXml(cam)) != 0) {
        std::cerr << "[ERROR] - GEVInitXml: " << get_strerror(error) << std::endl;
        return false;
    }
    if ((error = GEVOpenStreamChannel(cam, connection.AdapterIP, connection.PortData, 0)) != 0) {
        std::cerr << "[ERROR] - GEVOpenStreamChannel: " << get_strerror(error) << std::endl;
        return false;
    }
    if ((error = GEVSetPacketResend(cam, 0)) != 0) {
        std::cerr << "[ERROR] - GEVSetPacketResend: " << get_strerror(error) << std::endl;
        return false;
    }

    if ((error = GEVSetFeatureInteger(cam, "GevSCPD", 500)) != 0) {
        std::cerr << "[ERROR] - GEVSetFeatureInteger('GevSCPD'): " << get_strerror(error) << std::endl;
        return false;
    }
    FEATURE_PARAMETER f_param;
    if ((error = GEVGetFeatureParameter(cam, "GevSCPSPacketSize", &f_param)) != 0) {
        std::cout << "[INFO] - GevSCPSPacketSize is not Available" << std::endl;
    } else {
        auto ps_min = static_cast<WORD>(f_param.Min != -1 ? f_param.Min : 0);
        auto ps_max = static_cast<WORD>(f_param.Max != -1 ? f_param.Max : 20000);
        auto ps_inc = static_cast<WORD>(f_param.Inc !=  1 ? f_param.Inc : 4);
        WORD packet_size;
        if ((error = GEVTestFindMaxPacketSize(cam, &packet_size, ps_min, ps_max, ps_inc)) != 0) {
            std::cerr << "[ERROR] - GEVTestFindMaxPacketSize('GevSCPD'): " << get_strerror(error) << std::endl;
            return false;
        }
        std::cout << "[INFO] - Find maximal packet size: " << packet_size << std::endl;
    }
    if ((error = GEVInitFilterDriver(cam)) != 0) {
        std::cerr << "[ERROR] - GEVInitFilterDriver: " << get_strerror(error) << std::endl;
        return false;
    }

    BYTE version_major, version_minor;
    if ((error = GEVGetFilterDriverVersion(cam, &version_major, &version_minor)) != 0) {
        std::cerr << "[ERROR] - GEVGetFilterDriverVersion: " << get_strerror(error) << std::endl;
        return false;
    } else {
        std::cout
            << "[INFO] - Filter driver version :"
            << static_cast<int>(version_major) << "."
            << static_cast<int>(version_minor >> 4) << "."
            << static_cast<int>(version_minor & 0x0f)
            << std::endl;
    }

    return true;
}

bool closedevice(const KOWAGIGEVISION_CAMNR& cam) {
    bool allsucceed = true;
    WORD error;
    if ((error = GEVCloseStreamChannel(cam)) != 0) {
        std::cerr << "[ERROR] - GEVCloseStreamChannel: " << get_strerror(error) << std::endl;
        allsucceed = false;
    }
    if ((error = GEVCloseFilterDriver(cam)) != 0) {
        std::cerr << "[ERROR] - GEVCloseFilterDriver: " << get_strerror(error) << std::endl;
        allsucceed = false;
    }
    if ((error = GEVClose(cam)) != 0) {
        std::cerr << "[ERROR] - GEVClose: " << get_strerror(error) << std::endl;
        allsucceed = false;
    }
    return allsucceed;
}

// note: imgnum == -1: infinity
bool stream(const KOWAGIGEVISION_CAMNR& cam, int imgnum) {
    int64_t bufi64;
    WORD error;
    if ((error = GEVGetFeatureInteger(cam, "Width", &bufi64)) != 0) {
        std::cerr << "[ERROR] - GEVGetFeatureInteger-Width: "
                  << get_strerror(error) << std::endl;
        return false;
    }
    int width = static_cast<int>(bufi64);
    std::cout << "[INFO] - Width: " << width << std::endl;

    if ((error = GEVGetFeatureInteger(cam, "Height", &bufi64)) != 0) {
        std::cerr << "[ERROR] - GEVGetFeatureInteger-Height: "
                  << get_strerror(error) << std::endl;
        return false;
    }
    int height = static_cast<int>(bufi64);
    std::cout << "[INFO] - Height: " << height << std::endl;

    if ((error = GEVGetFeatureInteger(cam, "PixelFormat", &bufi64)) != 0) {
        std::cerr << "[ERROR] - GEVGetFeatureInteger-PixelFormat: "
                  << get_strerror(error) << std::endl;
        return false;
    }
    int pixel_format = static_cast<int>(bufi64);
    std::cout << "[INFO] - PixelFormat: " << pixel_format << std::endl;

    if ((error = GEVGetFeatureInteger(cam, "PayloadSize", &bufi64)) != 0) {
        std::cerr << "[ERROR] - GEVGetFeatureInteger-PayloadSize: "
                  << get_strerror(error) << std::endl;
        return false;
    }
    int payload_size = static_cast<int>(bufi64);
    std::cout << "[INFO] - PayloadSize: " << payload_size << std::endl;

    if ((error = GEVAcquisitionStart(cam, imgnum)) != 0) {
        std::cerr << "[ERROR] - GEVAcquisitionStart: "
                  << get_strerror(error) << std::endl;
        return false;
    }

    std::unique_ptr<char> img_buffer(new char[payload_size]);
    IMAGE_HEADER img_header;
    for(int i = 0; i != imgnum; i++) {
        switch(error = GEVGetImageBuffer(cam, &img_header,
                                         reinterpret_cast<BYTE*>(img_buffer.get()))) {
        case GEV_STATUS_SUCCESS:
        case GEV_STATUS_GRAB_ERROR:
        {
            std::cout
                << "[INFO] - Image: " << img_header.FrameCounter << ", "
                << "Missing Packets: " << img_header.MissingPacket
                << std::endl;

            std::ostringstream oss;
            oss << "image" << i << ".bmp";
            save_mono_bitmap(oss.str(), height, width, width, img_buffer.get());
            break;
        }
        default:
        {
            std::cerr << "[ERROR] - GEVGetImageBuffer: "
                      << get_strerror(error) << std::endl;
            GEVAcquisitionStop(cam);
            return false;
            break;
        }
    }
    }
    if ((error = GEVAcquisitionStop(cam)) != 0) {
        std::cerr << "[ERROR] - GEVAcquisitionStop: "
                  << get_strerror(error) << std::endl;
        return false;
    }

    return true;
}

int main(int argc, char*argv[]) {
    auto dis = discovery();
    if (!dis) {
        return 2;
    }

    const DEVICE_PARAM* dev = select_device(*dis);
    if (dev == nullptr) {
        return 1;
    }
    CONNECTION con = make_connection(*dev);

    WORD error;
    KOWAGIGEVISION_CAMNR cam = 1;
    if ((error = GEVInit(cam, &con, nullptr, 0, EXCLUSIVE_ACCESS)) != 0) {
        std::cerr << "[ERROR] - GEVInit: " << get_strerror(error) << std::endl;
        return 2;
    }
    if (!setupdevice(cam, con)) {
        closedevice(cam);
        return 2;
    }

    stream(cam, 16);

    closedevice(cam);
    return 0;
}
