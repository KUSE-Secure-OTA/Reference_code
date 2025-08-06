# "v0.0.0"
cmake_minimum_required(VERSION 3.5)
project(IC_someip LANGUAGES CXX)

set(OE_QMAKE_PATH_EXTERNAL_HOST_BINS "$ENV{OE_QMAKE_PATH_EXTERNAL_HOST_BINS}")
set(CMAKE_INCLUDE_CURRENT_DIR ON)

set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)

set(PRJ_NAME IC_someip)
# QtCreator supports the following variables for Android, which are identical to qmake Android variables.
# Check http://doc.qt.io/qt-5/deployment-android.html for more information.
# They need to be set before the find_package(Qt5 ...) call.

#if(ANDROID)
#    set(ANDROID_PACKAGE_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/android")
#    if (ANDROID_ABI STREQUAL "armeabi-v7a")
#        set(ANDROID_EXTRA_LIBS
#            ${CMAKE_CURRENT_SOURCE_DIR}/path/to/libcrypto.so
#            ${CMAKE_CURRENT_SOURCE_DIR}/path/to/libssl.so)
#    endif()
#endif()

#set(PRJ_SRC_GEN_PATH ../src-gen)
#set(PRJ_SRC_GEN_COMMONAPI_SOMEIP_PATH ${PRJ_SRC_GEN_PATH}/someip/v0/commonapi)
#FILE(GLOB PRJ_SOMEIP_LIB_SRCS ${PRJ_SRC_GEN_COMMONAPI_SOMEIP_PATH}/*cpp)


set(CMAKE_PREFIX_PATH "../cmake")

message("flag 0")
find_package(Qt5 COMPONENTS Core Quick Widgets REQUIRED)
message("flag 00")
set(CMAKE_PREFIX_PATH "/home/ota/Documents/install_folder/lib/cmake")
#find_package (CommonAPI-SomeIP 3.2.3 REQUIRED)
#find_package (vsomeip3 REQUIRED)

#for outer communication
set(PRJ_SRC_GEN_PATH /home/ota/Documents/Instrument-Cluster/src-gen)
set(PRJ_SRC_GEN_COMMONAPI_PATH ${PRJ_SRC_GEN_PATH}/core/v0/commonapi)
set(PRJ_SRC_GEN_COMMONAPI_SOMEIP_PATH ${PRJ_SRC_GEN_PATH}/someip/v0/commonapi)
#for inner communication
set(PRJ_SRC_GEN_PATH-inter /home/ota/Documents/Instrument-Cluster/src-gen-inter)
set(PRJ_SRC_GEN_COMMONAPI_PATH-inter ${PRJ_SRC_GEN_PATH-inter}/core/v0/commonapi)
set(PRJ_SRC_GEN_COMMONAPI_SOMEIP_PATH-inter ${PRJ_SRC_GEN_PATH-inter}/someip/v0/commonapi)
# Application
FILE(GLOB PRJ_PROXY_GEN_SRCS ${PRJ_SRC_GEN_COMMONAPI_PATH}/*Proxy.cpp)
FILE(GLOB PRJ_STUB_GEN_SRCS ${PRJ_SRC_GEN_COMMONAPI_PATH}/*Stub*.cpp)
FILE(GLOB PRJ_STUB_IMPL_SRCS ${PRJ_SRC_COMMONAPI_PATH}/*Stub*.cpp)
 #Boost
# set(CMAKE_PREFIX_PATH "../boost")
#find_package( Boost 1.66 COMPONENTS system thread log REQUIRED )
#include_directories( ${Boost_INCLUDE_DIR} )

FILE(GLOB PRJ_SOMEIP_LIB_SRCS
    ${PRJ_SRC_GEN_COMMONAPI_SOMEIP_PATH}/*cpp
    ${PRJ_SRC_GEN_COMMONAPI_SOMEIP_PATH-inter}/*cpp
    )
message("flag 1")
if(ANDROID)
    add_library(IC_someip SHARED
      main.cpp
      qml.qrc
    )
else()
    add_executable(IC_someip
      main.cpp
      qml.qrc
#      ../src-gen/someip/v0/commonapi/ICSomeIPDeployment.cpp
#      ../src-gen/someip/v0/commonapi/ICSomeIPProxy.cpp
#      ../src-gen/someip/v0/commonapi/ICSomeIPStubAdapter.cpp
#      ../src-gen-inter/someip/v0/commonapi/IC_interSomeIPDeployment.cpp
#      ../src-gen-inter/someip/v0/commonapi/IC_interSomeIPProxy.cpp
#      ../src-gen-inter/someip/v0/commonapi/IC_interSomeIPStubAdapter.cpp
      ICStubImpl.cpp
      gear.cpp
      speed.cpp
      battery.cpp
      batteryupdate.cpp
      battery_gauge.cpp
      Clock.h
      receiver.cpp
      lrsign.cpp
      mode.cpp
      get_battery.cpp
      ic_interstubimpl.cpp
      pdc.cpp
      pdc.h
      sender.cpp
      sender.h
      speedProvider.h
    )
endif()
message("flag 2")
# Include directories =
include_directories(
    /home/ota/Documents/Instrument-Cluster/src-gen/
    /home/ota/Documents/Instrument-Cluster/src-gen-inter/
    /home/ota/Documents/install_folder/include/CommonAPI-3.2
    /home/ota/Documents/install_folder/include
    /home/ota/Documents/install_folder/lib
    /home/ota/Documents/Instrument-Cluster/src-gen/core
    /home/ota/Documents/Instrument-Cluster/src-gen/someip
    /home/ota/Documents/Instrument-Cluster/src-gen-inter/core
    /home/ota/Documents/Instrument-Cluster/src-gen-inter/someip
)
message("flag 3")

target_compile_definitions(IC_someip
  PRIVATE $<$<OR:$<CONFIG:Debug>,$<CONFIG:RelWithDebInfo>>:QT_QML_DEBUG>)
link_directories(
    /home/ota/Documents/install_folder/lib)
# CommonAPI 라이브러리 찾기
set(CMAKE_PREFIX_PATH "../cmake/Qt5Core" "../cmake/Qt5Quick")
find_library(COMMONAPI_LIB CommonAPI PATHS /home/ota/Documents/install_folder/lib)
find_library(COMMONAPI_SOMEIP_LIB CommonAPI-SomeIP PATHS /home/ota/Documents/install_folder/lib)
find_library(VSOMEIP_LIB vsomeip3 PATHS /home/ota/Documents/install_folder/lib)
message("COMMONAPI_LIB: ${COMMONAPI_LIB}")
message("COMMONAPI_SOMEIP_LIB: ${COMMONAPI_SOMEIP_LIB}")
message("VSOMEIP_LIB: ${VSOMEIP_LIB}")
# 라이브러리 연결
target_link_libraries(IC_someip
    PRIVATE Qt5::Core Qt5::Quick
    ${COMMONAPI_LIB}
    ${COMMONAPI_SOMEIP_LIB}
    ${VSOMEIP_LIB}
)


add_library(${PRJ_NAME}-someip SHARED ${PRJ_SOMEIP_LIB_SRCS})
message("PRJ_SOMEIP_LIB_SRCS = ${PRJ_SOMEIP_LIB_SRCS}")
target_link_libraries(${PRJ_NAME}-someip CommonAPI-SomeIP)
