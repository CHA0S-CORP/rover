#!/usr/bin/env bash
set -euo pipefail

CAM_IP="${CAM_IP:-192.168.1.252}"
BASE="http://${CAM_IP}/?custom=1"
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }
dim()   { printf "\033[90m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }

bold "=== Trying liveview start commands ==="
# Various start-streaming commands known from dashcam apps
for cmd_str in \
    "cmd=2015&par=1" \
    "cmd=2015&str=1" \
    "cmd=2015&par=0" \
    "cmd=3001&par=0" \
    "cmd=2001&par=0" \
    "cmd=2003&par=1" \
    "cmd=9001&par=1" \
    "cmd=9002&par=1"; do
    printf "  %-30s " "$cmd_str"
    resp=$(curl -sf --connect-timeout 3 "${BASE}&${cmd_str}" 2>/dev/null || echo "(fail)")
    status=$(echo "$resp" | grep -oP '(?<=<Status>)[^<]+' || echo "?")
    echo "Status=$status"
done

bold ""
bold "=== Checking port 8081 with GET, different paths ==="
for path in "" "/" "/live" "/stream" "/live.m3u8" "/stream.m3u8" "/index.m3u8" "/playlist.m3u8" "/ch0.m3u8" "/front" "/rear" "/0" "/1"; do
    printf "  :8081%-20s " "$path"
    ct=$(curl -sfI --connect-timeout 2 --max-time 3 "http://${CAM_IP}:8081${path}" 2>/dev/null | grep -i content-type || true)
    if [[ -n "$ct" ]]; then
        green "$ct"
    else
        dim "no"
    fi
done

bold ""
bold "=== Dump first bytes from 8081 various paths ==="
for path in "" "/" "/live" "/stream.m3u8"; do
    echo "--- :8081${path} ---"
    curl -sf --connect-timeout 2 --max-time 3 "http://${CAM_IP}:8081${path}" 2>/dev/null | head -c 500 || dim "(empty)"
    echo ""
done

bold ""
bold "=== Check if 8081 is RTSP ==="
if command -v ffprobe > /dev/null 2>&1; then
    printf "  ffprobe http://${CAM_IP}:8081   "
    ffprobe -v info -i "http://${CAM_IP}:8081" 2>&1 | head -15 || dim "(fail)"
fi

bold ""
bold "=== Try MJPEG on 8192 via ffprobe ==="
if command -v ffprobe > /dev/null 2>&1; then
    echo "--- ffprobe http://${CAM_IP}:8192 ---"
    ffprobe -v info -i "http://${CAM_IP}:8192" 2>&1 | head -15 || dim "(fail)"
fi

bold ""
bold "=== Try ffmpeg MJPEG→HLS (5 seconds) ==="
if command -v ffmpeg > /dev/null 2>&1; then
    mkdir -p /tmp/rover-hls-test
    echo "Recording 5s from :8192 to HLS..."
    ffmpeg -y -f mjpeg -i "http://${CAM_IP}:8192" \
        -c:v libx264 -preset ultrafast -tune zerolatency \
        -f hls -hls_time 1 -hls_list_size 3 \
        -hls_flags delete_segments \
        -t 5 /tmp/rover-hls-test/live.m3u8 2>&1 | tail -10
    echo ""
    echo "Result:"
    ls -la /tmp/rover-hls-test/ 2>/dev/null || dim "(no output)"
    rm -rf /tmp/rover-hls-test
else
    dim "(no ffmpeg)"
fi

bold ""
bold "=== Done ==="
