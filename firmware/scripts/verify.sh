#!/usr/bin/env bash
# Post-flash verification for Rove R2-4K-DUAL RTSP streaming.
# Usage: ./verify.sh [camera_ip]

set -euo pipefail

CAM_IP="${1:-192.168.1.252}"
RTSP_URL="rtsp://${CAM_IP}:554/"
MJPEG_URL="http://${CAM_IP}:8192"
TIMEOUT=5

red()   { printf '\033[0;31m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[0;33m%s\033[0m\n' "$*"; }

pass=0
fail=0

check() {
    local label="$1"
    shift
    printf "%-40s" "$label"
    if "$@" >/dev/null 2>&1; then
        green "OK"
        ((pass++))
    else
        red "FAIL"
        ((fail++))
    fi
}

echo "=== Rove R2-4K Firmware Verification ==="
echo "Camera IP: ${CAM_IP}"
echo

# 1. Ping
check "Ping camera" ping -c1 -W"${TIMEOUT}" "${CAM_IP}"

# 2. HTTP (GoAhead web server)
check "HTTP port 80" nc -z -w"${TIMEOUT}" "${CAM_IP}" 80

# 3. MJPEG port
check "MJPEG port 8192" nc -z -w"${TIMEOUT}" "${CAM_IP}" 8192

# 4. RTSP port
check "RTSP port 554" nc -z -w"${TIMEOUT}" "${CAM_IP}" 554

# 5. MJPEG stream produces data
check "MJPEG stream data" \
    bash -c "curl -sf --max-time ${TIMEOUT} '${MJPEG_URL}' | head -c 1000 | grep -q 'JFIF\|\\xff\\xd8'"

# 6. RTSP DESCRIBE (ffprobe)
if command -v ffprobe &>/dev/null; then
    echo
    echo "--- RTSP Stream Info ---"
    printf "%-40s" "RTSP stream reachable"
    if ffprobe -v error -rtsp_transport tcp -i "${RTSP_URL}" \
        -show_entries stream=codec_name,width,height,r_frame_rate \
        -of csv=p=0 -timeout "${TIMEOUT}000000" 2>/dev/null; then
        green "OK"
        ((pass++))

        echo
        echo "Stream details:"
        ffprobe -v error -rtsp_transport tcp -i "${RTSP_URL}" \
            -show_entries stream=codec_name,codec_long_name,width,height,r_frame_rate,bit_rate \
            -of default=noprint_wrappers=1 -timeout "${TIMEOUT}000000" 2>/dev/null || true
    else
        red "FAIL (no RTSP media sessions — is VencType=3 configured?)"
        ((fail++))
    fi
else
    yellow "ffprobe not found — skipping RTSP stream probe"
    echo "  Install with: brew install ffmpeg"
fi

# 7. Quick playability test
if command -v ffmpeg &>/dev/null; then
    echo
    printf "%-40s" "RTSP 3-second capture"
    tmpfile="$(mktemp /tmp/rtsp_test_XXXXXX.ts)"
    if ffmpeg -y -v error -rtsp_transport tcp -i "${RTSP_URL}" \
        -c:v copy -t 3 -f mpegts "${tmpfile}" 2>/dev/null; then
        fsize=$(stat -f%z "${tmpfile}" 2>/dev/null || stat -c%s "${tmpfile}" 2>/dev/null || echo 0)
        if [ "${fsize}" -gt 1000 ]; then
            green "OK (${fsize} bytes captured)"
            ((pass++))
        else
            red "FAIL (only ${fsize} bytes — stream may be empty)"
            ((fail++))
        fi
    else
        red "FAIL"
        ((fail++))
    fi
    rm -f "${tmpfile}"
fi

echo
echo "=== Results: ${pass} passed, ${fail} failed ==="
[ "${fail}" -eq 0 ] && green "All checks passed!" || red "Some checks failed."
exit "${fail}"
