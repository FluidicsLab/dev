#ifndef KOWA_GIGEVISION_LIB_DEFINES_H
#define KOWA_GIGEVISION_LIB_DEFINES_H

#define GEV_SDK_VERSION_MAJOR     1
#define GEV_SDK_VERSION_MINOR     6
#define GEV_SDK_VERSION_MICRO     1

#ifdef GEV_SDK_BUILD
// current ABI version
// Note: If wish to Compare your app and SDK ABI version,
//       use `GEV_SDK_VERSION_*`.
#define GEV_SDK_VERSION_ABI_MAJOR 1
#define GEV_SDK_VERSION_ABI_MINOR 0
#define GEV_SDK_VERSION_ABI_MICRO 1
#endif

// environs
#ifdef  _WIN32
#define GEV_ENVIRON_WINDOWS
#endif
#ifdef  __unix__
#define GEV_ENVIRON_UNIX
#endif
#ifdef  __linux__
#define GEV_ENVIRON_LINUX
#endif
#ifdef  __APPLE__
#define GEV_ENVIRON_MACINTOSH
#endif

#ifdef  _MSC_VER
#define GEV_ENVIRON_MSVC
#endif
// end of environ

// build switch
// + GEV_EXPORT
// + GEV_API
//     + __stdcall, only Windows x86.
// + GEV_DEPRECATED
// + GEV_DEPRECATED_MESSAGE
// + GEV_ASSERT_PRIVATE
#ifdef  GEV_SDK_BUILD
#ifdef  GEV_ENVIRON_WINDOWS
#define GEV_EXPORT __declspec(dllexport)
#elif defined(__GNUC__)
#define GEV_EXPORT __attribute__((visibility("default")))
#endif

#if defined(__cplusplus)
#define GEV_ASSERT_PRIVATE() static_assert(true, "this is a private function.")
#else
#define GEV_ASSERT_PRIVATE() _Static_assert(1, "this is a private function.")
#endif
#else //GEV_BUILD
#ifdef  GEV_ENVIRON_WINDOWS
#define GEV_EXPORT __declspec(dllimport)
#elif defined(__GNUC__)
#define GEV_EXPORT
#endif
#if defined(__cplusplus)
#define GEV_ASSERT_PRIVATE() static_assert(false, "this is a private function.")
#else
#define GEV_ASSERT_PRIVATE() _Static_assert(0, "this is a private function.")
#endif
#endif//GEV_SDK_BUILD

#ifdef  GEV_ENVIRON_WINDOWS
#define GEV_DEPRECATED __declspec(deprecated)
#define GEV_DEPRECATED_MESSAGE(message) __declspec(deprecated(message))
#ifdef  _M_IX86
#define GEV_API __stdcall
#else
#define GEV_API
#endif
#elif defined(__GNUC__)
#define GEV_DEPRECATED __attribute__((deprecated))
#define GEV_DEPRECATED_MESSAGE(message) __attribute__((deprecated(message)))
#define GEV_API
#endif//environ
// end of build switch





#endif//__KOWA_GIGEVISION_LIB_DEFINES_H
