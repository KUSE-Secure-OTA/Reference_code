#!/bin/bash

DIR1="/opt/OTA_Handler/boot_manager/dir1"
DIR2="/opt/OTA_Handler/boot_manager/dir2"
TMP="/opt/OTA_Handler/boot_manager/tmp"
STATUS="/opt/OTA_Handler/boot_manager/status.json"
LOG="/opt/OTA_Handler/boot_manager/log.txt"

FILE1=$(find "$DIR1" -type f ! -name "*.sh" | head -n 1)
FILE2=$(find "$DIR2" -type f ! -name "*.sh" | head -n 1)
echo "FILE1: $FILE1" >> "$LOG"
echo "FILE2: $FILE2" >> "$LOG"

if [ -n "$FILE1" ] && [ -n "$FILE2" ]; then
    echo "$(date): start change json" >> "$LOG"
    jq '.priority |= reverse' "$STATUS" > "$STATUS.tmp" && mv "$STATUS.tmp" "$STATUS"
    echo "$(date): Change $FILE1 and $FILE2" >> "$LOG"
fi

NEXT_DIR=$(jq -r '.priority[0]' "$STATUS")
ALT_DIR=$(jq -r '.priority[1]' "$STATUS")

echo "Next Dir: $NEXT_DIR" >> "$LOG"
echo "ALT DIR: $ALT_DIR" >> "$LOG"

NEXT_FILE=$(find "/opt/OTA_Handler/boot_manager/$NEXT_DIR" -type f -name "*.sh" | head -n 1)
ALT_FILE=$(find "/opt/OTA_Handler/boot_manager/$ALT_DIR" -type f -name "*.sh" | head -n 1)

echo "Next File: $NEXT_FILE" >> "$LOG"
echo "ALT File: $ALT_FILE" >> "$LOG"

bash "$NEXT_FILE" &
PID=$!
echo "devsdfsdf PID = $PID"
sleep 0.5

echo "[INFO] '$Next_file' process.. PID=$PID" >> "$LOG"

if ps -p "$PID" > /dev/null 2>&1; then
    find "/opt/OTA_Handler/boot_manager/$ALT_DIR" -type f ! -name "*.sh" -exec mv {} "$TMP" \;
    echo "$(date): Success: $NEXT_FILE" >> "$LOG"
    exit 0
else
    bash "$ALT_FILE" &
    find "/opt/OTA_Handler/boot_manager/$NEXT_DIR" -type f ! -name "start1.sh" -delete
    jq '.priority |= reverse' "$STATUS" > "$STATUS.tmp" && mv "$STATUS.tmp" "$STATUS"
    echo "$(date): Failed: $NEXT_FILE, ran $ALT_FILE instead" >> "$LOG"
    exit 1
fi

