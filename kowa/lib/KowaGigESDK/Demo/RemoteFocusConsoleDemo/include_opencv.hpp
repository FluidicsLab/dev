#pragma once

#ifndef OPENCV_INCLUDE_AND_SETUP_DEPENDENCY_LIBRARY_HPP
#define OPENCV_INCLUDE_AND_SETUP_DEPENDENCY_LIBRARY_HPP

#ifndef  _MSC_VER
#include <opencv2/opencv.hpp>
#else  //_MSC_VER

// ignore all warning from MSVC.
#pragma warning(push, 0)
#include <opencv2/opencv.hpp>
#pragma warning(pop)

// switch target lib by configuration.
#ifdef _DEBUG
#define CV_EXT_STR "d.lib"
#else
#define CV_EXT_STR ".lib"
#endif

// target opencv version
#ifdef  CVAUX_STR
#define CV_VERSION_STR \
    CVAUX_STR(CV_MAJOR_VERSION) \
    CVAUX_STR(CV_MINOR_VERSION) \
    CVAUX_STR(CV_SUBMINOR_VERSION)

// e.g. "opencv_world430.lib"
// e.g. "opencv_world470d.lib"
#pragma comment(lib, "opencv_world" CV_VERSION_STR CV_EXT_STR)
#endif//CVAUX_STR

#endif//_MSC_VER
#endif//OPENCV_INCLUDE_AND_SETUP_DEPENDENCY_LIBRARY_HPP
