#!/usr/bin/env bash
# Probe the dashcam API to discover the actual response format.
# Run while connected to the dashcam WiFi.
set -euo pipefail

CAM_IP="${CAM_IP:-192.168.1.252}"
BASE="http://${CAM_IP}/?custom=1"

dim()   { printf "\033[90m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }

probe() {
    local label="$1" url="$2"
    echo ""
    bold "=== $label ==="
    dim "$url"
    curl -sf --connect-timeout 3 --max-time 5 "$url" 2>/dev/null || echo "(no response)"
}

echo "Probing dashcam at $CAM_IP"
echo "=========================="

# Core commands
probe "Heartbeat (3016)"          "${BASE}&cmd=3016"
probe "Battery (3019)"            "${BASE}&cmd=3019"
probe "Free space (3017)"         "${BASE}&cmd=3017"
probe "SD card status (3024)"     "${BASE}&cmd=3024"
probe "Firmware version (3012)"   "${BASE}&cmd=3012"
probe "Config (3014)"             "${BASE}&cmd=3014"
probe "Recording time (2016)"     "${BASE}&cmd=2016"
probe "File list (3015)"          "${BASE}&cmd=3015"
probe "List commands (3002)"      "${BASE}&cmd=3002"

# Try the file browser HTML
echo ""
bold "=== SD Card Browser (HTML) ==="
dim "http://${CAM_IP}/"
curl -sf --connect-timeout 3 --max-time 5 "http://${CAM_IP}/" 2>/dev/null | head -50 || echo "(no response)"

# Try known subdirectories
for dir in DCIM CARDV SD Video Photo Movie; do
    echo ""
    bold "=== Browse /${dir}/ ==="
    resp=$(curl -sf --connect-timeout 2 --max-time 3 "http://${CAM_IP}/${dir}/" 2>/dev/null || true)
    if [[ -n "$resp" ]]; then
        echo "$resp" | head -30
    else
        dim "(no response or 404)"
    fi
done

# Try alternative stream URLs
echo ""
bold "=== Stream Probes ==="
for url in \
    "rtsp://${CAM_IP}/xxx.mov" \
    "rtsp://${CAM_IP}/live" \
    "rtsp://${CAM_IP}/stream" \
    "rtsp://${CAM_IP}/live.sdp" \
    "rtsp://${CAM_IP}:554/live" \
    "rtsp://${CAM_IP}:8554/live"; do
    printf "  %-45s " "$url"
    if command -v ffprobe > /dev/null 2>&1; then
        if timeout 5 ffprobe -v quiet -rtsp_transport tcp -i "$url" -show_entries format=duration -of csv=p=0 2>/dev/null; then
            green "OK"
        else
            dim "no"
        fi
    else
        dim "skip (no ffprobe)"
    fi
done

# Try HTTP stream ports
for port in 8192 8080 80 554 8554; do
    printf "  http://${CAM_IP}:%-5s    " "$port"
    if curl -sf --connect-timeout 2 --max-time 2 -o /dev/null "http://${CAM_IP}:${port}" 2>/dev/null; then
        green "responds"
    else
        dim "no"
    fi
done

# Try toggling to preview mode first, then re-probe RTSP
echo ""
bold "=== Set preview mode (3001 par=2) then retry RTSP ==="
curl -sf --connect-timeout 3 "${BASE}&cmd=3001&par=2" 2>/dev/null || true
sleep 2
if command -v ffprobe > /dev/null 2>&1; then
    printf "  rtsp://${CAM_IP}/xxx.mov  "
    if timeout 8 ffprobe -v quiet -rtsp_transport tcp -i "rtsp://${CAM_IP}/xxx.mov" -show_entries stream=codec_name,width,height -of json 2>/dev/null; then
        green "OK"
    else
        dim "still no"
    fi
fi

echo ""
bold "=== Done ==="
