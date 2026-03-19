#!/usr/bin/env bash
set -euo pipefail

CAM_IP="${CAM_IP:-192.168.1.252}"
BASE="http://${CAM_IP}/?custom=1"
PASS=0
FAIL=0

green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }
dim()   { printf "\033[90m%s\033[0m\n" "$*"; }

check() {
    local label="$1" url="$2"
    printf "  %-30s " "$label"
    if resp=$(curl -sf --connect-timeout 3 --max-time 5 "$url" 2>/dev/null); then
        green "OK"
        dim "    $resp" | head -c 200
        echo
        PASS=$((PASS + 1))
    else
        red "FAIL"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "=== Rover Camera Test ==="
echo "Target: $CAM_IP"
echo ""

# Connectivity
echo "[Connectivity]"
printf "  %-30s " "Ping"
if ping -c 1 -W 2 "$CAM_IP" > /dev/null 2>&1; then
    green "OK"
    PASS=$((PASS + 1))
else
    red "FAIL - not reachable. Are you on the dashcam WiFi?"
    FAIL=$((FAIL + 1))
    echo ""
    echo "Connect to the dashcam WiFi first (SSID: RoveR2_XXXX, password: 12345678)"
    exit 1
fi

# API commands
echo ""
echo "[Camera API]"
check "Heartbeat (3016)"       "${BASE}&cmd=3016"
check "Battery (3019)"         "${BASE}&cmd=3019"
check "Free space (3017)"      "${BASE}&cmd=3017"
check "SD card (3024)"         "${BASE}&cmd=3024"
check "Firmware (3012)"        "${BASE}&cmd=3012"
check "Config (3014)"          "${BASE}&cmd=3014"
check "Recording time (2016)"  "${BASE}&cmd=2016"
check "File list (3015)"       "${BASE}&cmd=3015"

# SD card browser
echo ""
echo "[HTTP Services]"
printf "  %-30s " "SD card browser"
if curl -sf --connect-timeout 3 --max-time 5 "http://${CAM_IP}/" > /dev/null 2>&1; then
    green "OK"
    PASS=$((PASS + 1))
else
    red "FAIL"
    FAIL=$((FAIL + 1))
fi

# RTSP probe
printf "  %-30s " "RTSP stream"
if command -v ffprobe > /dev/null 2>&1; then
    if ffprobe -v quiet -rtsp_transport tcp -i "rtsp://${CAM_IP}/xxx.mov" -show_entries format=duration -of csv=p=0 > /dev/null 2>&1; then
        green "OK"
        PASS=$((PASS + 1))
    else
        red "FAIL (camera may need to be in preview mode)"
        FAIL=$((FAIL + 1))
    fi
else
    dim "SKIP (ffprobe not installed)"
fi

# HTTP stream
printf "  %-30s " "HTTP stream (:8192)"
if curl -sf --connect-timeout 3 --max-time 2 "http://${CAM_IP}:8192" > /dev/null 2>&1; then
    green "OK"
    PASS=$((PASS + 1))
else
    dim "SKIP (not always available)"
fi

# Summary
echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
