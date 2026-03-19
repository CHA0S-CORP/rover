#!/usr/bin/env bash
set -euo pipefail

CAM_IP="${CAM_IP:-192.168.1.252}"
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }
dim()   { printf "\033[90m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }

bold "=== Port 8192: content-type and first bytes ==="
echo "--- Headers ---"
curl -sfI --connect-timeout 3 --max-time 3 "http://${CAM_IP}:8192" 2>/dev/null || dim "(no headers)"
echo ""
echo "--- First 256 bytes (hex) ---"
curl -sf --connect-timeout 3 --max-time 3 "http://${CAM_IP}:8192" 2>/dev/null | head -c 256 | xxd | head -20 || dim "(no data)"
echo ""
echo "--- ffprobe HTTP 8192 ---"
if command -v ffprobe > /dev/null 2>&1; then
    timeout 10 ffprobe -v info -i "http://${CAM_IP}:8192" 2>&1 | head -30 || dim "(ffprobe failed)"
else
    dim "(no ffprobe)"
fi

bold ""
bold "=== Port 8081: content-type and first bytes ==="
echo "--- Headers ---"
curl -sfI --connect-timeout 3 --max-time 3 "http://${CAM_IP}:8081" 2>/dev/null || dim "(no headers)"
echo ""
echo "--- First 256 bytes (hex) ---"
curl -sf --connect-timeout 3 --max-time 3 "http://${CAM_IP}:8081" 2>/dev/null | head -c 256 | xxd | head -20 || dim "(no data)"
echo ""
echo "--- ffprobe HTTP 8081 ---"
if command -v ffprobe > /dev/null 2>&1; then
    timeout 10 ffprobe -v info -i "http://${CAM_IP}:8081" 2>&1 | head -30 || dim "(ffprobe failed)"
else
    dim "(no ffprobe)"
fi

bold ""
bold "=== Try RTSP on non-standard ports ==="
if command -v ffprobe > /dev/null 2>&1; then
    for port in 8081 8192; do
        for path in / /live /stream /h264 /xxx.mov; do
            printf "  rtsp://${CAM_IP}:${port}%-20s " "$path"
            if timeout 5 ffprobe -v quiet -rtsp_transport tcp -i "rtsp://${CAM_IP}:${port}${path}" 2>/dev/null; then
                green "OK"
            else
                dim "no"
            fi
        done
    done
fi

bold ""
bold "=== Raw TCP probe port 8192 (first 512 bytes) ==="
timeout 3 nc "${CAM_IP}" 8192 < /dev/null 2>/dev/null | head -c 512 | xxd | head -30 || dim "(no data or timeout)"

bold ""
bold "=== Raw TCP probe port 8081 (first 512 bytes) ==="
timeout 3 nc "${CAM_IP}" 8081 < /dev/null 2>/dev/null | head -c 512 | xxd | head -30 || dim "(no data or timeout)"

bold ""
bold "=== Done ==="
