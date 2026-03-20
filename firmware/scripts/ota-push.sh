#!/usr/bin/env bash
# Push firmware to camera over WiFi and trigger OTA update.
#
# Reversed from the Rove Android app (GetR24KFirmwareImpl.kt):
#   1. cmd=1017&par=0  — stop recording
#   2. POST R2D.tar    — multipart upload to GoAhead (stored at /mnt/mmc/R2D.tar)
#   3. cmd=5001        — prepare OTA (extract tar, set up flash)
#   4. cmd=5002        — trigger firmware update (sets ota_upgrade_status=1, reboots)
#
# Usage: ./ota-push.sh <R2D.tar> [camera_ip]

set -euo pipefail

TAR="${1:?Usage: $0 <R2D.tar> [camera_ip]}"
CAM_IP="${2:-192.168.1.252}"
BASE="http://${CAM_IP}/?custom=1"
TIMEOUT=10

red()   { printf '\033[0;31m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
dim()   { printf '\033[0;90m%s\033[0m\n' "$*"; }

die() { red "Error: $*"; exit 1; }

[ -f "$TAR" ] || die "File not found: $TAR"
command -v curl >/dev/null || die "curl is required"

echo "=== Rove R2-4K OTA Push ==="
echo "Firmware: $TAR ($(du -h "$TAR" | awk '{print $1}'))"
echo "Camera:   $CAM_IP"
echo

# ── Preflight ──

printf "%-40s" "Checking camera reachable..."
if curl -sf --connect-timeout 3 --max-time "$TIMEOUT" "${BASE}&cmd=3016" >/dev/null 2>&1; then
    green "OK"
else
    die "Camera not reachable at $CAM_IP. Connect to dashcam WiFi first."
fi

# ── Step 1: Stop recording ──

printf "%-40s" "Stopping recording (cmd=1017)..."
resp=$(curl -sf --max-time "$TIMEOUT" "${BASE}&cmd=1017&par=0" 2>/dev/null) || true
green "OK"

sleep 1

# ── Step 2: Upload R2D.tar ──

printf "%-40s" "Uploading firmware..."
upload_resp=$(curl -sf --max-time 300 \
    -F "file1=@${TAR};filename=R2D.tar" \
    "http://${CAM_IP}/" 2>/dev/null) || die "Upload failed"

if echo "$upload_resp" | grep -q "stored as"; then
    green "OK"
    dim "  $upload_resp"
else
    die "Unexpected upload response: $upload_resp"
fi

# ── Step 3: Prepare OTA (cmd=5001) ──

printf "%-40s" "Preparing OTA (cmd=5001)..."
resp=$(curl -sf --max-time 30 "${BASE}&cmd=5001" 2>/dev/null) || die "cmd=5001 failed"
if echo "$resp" | grep -q "<Status>0</Status>"; then
    green "OK"
else
    dim "  Response: $resp"
    red "WARNING: unexpected status (continuing anyway)"
fi

sleep 2

# ── Step 4: Trigger firmware update (cmd=5002) ──

printf "%-40s" "Triggering firmware update (cmd=5002)..."
resp=$(curl -sf --max-time 30 "${BASE}&cmd=5002" 2>/dev/null) || true
green "SENT"

echo
green "=== OTA triggered ==="
echo "The camera should now be flashing. DO NOT power off."
echo "It will reboot automatically when done (30-60 seconds)."
echo
echo "After reboot, reconnect to dashcam WiFi and run:"
echo "  make verify"
