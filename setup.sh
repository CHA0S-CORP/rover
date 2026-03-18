#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Rover Setup ==="

# Install system dependencies
echo "Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg network-manager python3-venv python3-pip

# Create Python venv
echo "Setting up Python virtual environment..."
python3 -m venv "$SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/pip" install --upgrade pip -q
"$SCRIPT_DIR/.venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q

# Install NetworkManager profile
echo "Installing network profile..."
bash "$SCRIPT_DIR/network/setup-network.sh"

# Install systemd service
echo "Installing systemd service..."
sudo cp "$SCRIPT_DIR/rover.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rover.service

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit network/dashcam-wifi.nmconnection with your dashcam's SSID"
echo "  2. Connect to dashcam: sudo nmcli connection up dashcam-wifi"
echo "  3. Start Rover: sudo systemctl start rover"
echo "  4. Open http://$(hostname -I | awk '{print $1}'):8080"
