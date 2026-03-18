#!/usr/bin/env bash
set -euo pipefail

# Setup network configuration for dashcam WiFi adapter.
# The USB WiFi adapter (wlan1) connects to the dashcam network,
# while the primary interface (eth0 or wlan0) serves the web UI.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONN_FILE="$SCRIPT_DIR/dashcam-wifi.nmconnection"

if [ ! -f "$CONN_FILE" ]; then
    echo "Error: $CONN_FILE not found"
    exit 1
fi

echo "Installing NetworkManager connection profile..."
sudo cp "$CONN_FILE" /etc/NetworkManager/system-connections/
sudo chmod 600 /etc/NetworkManager/system-connections/dashcam-wifi.nmconnection
sudo nmcli connection reload

echo ""
echo "NOTE: Edit /etc/NetworkManager/system-connections/dashcam-wifi.nmconnection"
echo "      to set your dashcam's actual SSID (replace RoveR2_XXXX)."
echo ""
echo "To connect: sudo nmcli connection up dashcam-wifi"
echo "To verify:  ping -I wlan1 192.168.1.254"
