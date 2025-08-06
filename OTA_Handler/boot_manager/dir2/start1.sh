#!/bin/bash

LD_LIBRARY_PATH=/usr/lib:/opt/OTA_Handler/boot_manager/dir1:/opt/OTA_Handler/boot_manager/dir2
COMMONAPI_CONFIG=/opt/IC_someip/commonapi4someip.ini
VSOMEIP_CONFIGURATION=/opt/IC_someip/json/IC.json
VSOMEIP_APPLICATION_NAME=IC-service

export LD_LIBRARY_PATH
export COMMONAPI_CONFIG
export VSOMEIP_CONFIGURATION
export VSOMEIP_APPLICATION_NAME

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$DIR/IC_someip"
"$DIR/IC_someip"
