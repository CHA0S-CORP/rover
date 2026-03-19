#!/usr/bin/env bash
# Deep probe for video stream on the dashcam.
set -euo pipefail

CAM_IP="${CAM_IP:-192.168.1.252}"
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }
dim()   { printf "\033[90m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }

bold "=== Port scan (common dashcam ports) ==="
for port in 80 554 1935 3478 4747 5000 5555 6666 7070 7878 8000 8001 8080 8081 8192 8443 8554 8888 9000 9090; do
    printf "  %-6s " "$port"
    if nc -z -w 1 "$CAM_IP" "$port" 2>/dev/null; then
        green "OPEN"
    else
        dim "closed"
    fi
done

bold ""
bold "=== RTSP paths (port 554) ==="
if command -v ffprobe > /dev/null 2>&1; then
    for path in / /live /stream /h264 /ch0 /ch1 /cam /video /media /main /sub /live.sdp /0 /1 /11 /12 /xxx.mov /live.mov /av0_0 /av0_1 /user=admin; do
        printf "  rtsp://${CAM_IP}%-25s " "$path"
        if timeout 3 ffprobe -v quiet -rtsp_transport tcp -i "rtsp://${CAM_IP}${path}" 2>/dev/null; then
            green "OK"
        else
            dim "no"
        fi
    done
else
    dim "ffprobe not available"
fi

bold ""
bold "=== HTTP content-type sniff on port 80 ==="
for path in / /live /stream /video /mjpeg /cgi-bin/snapshot.cgi /cgi-bin/stream.cgi /videostream.cgi /snap.jpg /tmpfs/auto.jpg; do
    printf "  %-40s " "http://${CAM_IP}${path}"
    ct=$(curl -sfI --connect-timeout 2 --max-time 3 "http://${CAM_IP}${path}" 2>/dev/null | grep -i content-type || true)
    if [[ -n "$ct" ]]; then
        green "$ct"
    else
        dim "no response"
    fi
done

bold ""
bold "=== Check /Video/Front/ for actual files ==="
curl -sf --connect-timeout 3 "http://${CAM_IP}/Video/Front/" 2>/dev/null | head -30 || dim "(empty or no response)"

bold ""
bold "=== Try cmd 2015 (start liveview) then re-probe ==="
curl -sf "http://${CAM_IP}/?custom=1&cmd=2015&par=1" 2>/dev/null || true
sleep 2
bold "Re-checking ports after liveview start..."
for port in 554 8192 8554 6666; do
    printf "  %-6s " "$port"
    if nc -z -w 2 "$CAM_IP" "$port" 2>/dev/null; then
        green "OPEN"
    else
        dim "closed"
    fi
done
if command -v ffprobe > /dev/null 2>&1; then
    printf "  rtsp://${CAM_IP}/xxx.mov  "
    if timeout 5 ffprobe -v quiet -rtsp_transport tcp -i "rtsp://${CAM_IP}/xxx.mov" 2>/dev/null; then
        green "OK"
    else
        dim "no"
    fi
fi
# Stop liveview
curl -sf "http://${CAM_IP}/?custom=1&cmd=2015&par=0" 2>/dev/null || true

bold ""
bold "=== Done ==="
