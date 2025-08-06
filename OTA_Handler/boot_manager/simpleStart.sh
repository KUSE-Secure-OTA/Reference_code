#!/bin/bash

STATUS="/opt/OTA_Handler/boot_manager/status.json"
LOG="/opt/OTA_Handler/boot_manager/log.txt"

NEXT_DIR=$(jq -r '.priority[0]' "$STATUS")

echo "[Simple] Next Dir: $NEXT_DIR" >> "$LOG"

NEXT_FILE=$(find "/opt/OTA_Handler/boot_manager/$NEXT_DIR" -type f -name "*.sh" | head -n 1)

echo "[Simple] Next File: $NEXT_FILE" >> "$LOG"

bash "$NEXT_FILE" &

echo "$(date): Start: $NEXT_FILE" >> "$LOG"

