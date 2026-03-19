# Rove R2-4K-DUAL Reverse Engineering

Comprehensive reverse engineering of the Rove R2-4K-DUAL dashcam, covering the Android companion app (APK) and the camera firmware. Research conducted March 2026.

## Contents

| Document | Description |
|----------|-------------|
| [HARDWARE.md](HARDWARE.md) | SoC identification, sensor specs, hardware architecture |
| [FIRMWARE.md](FIRMWARE.md) | Firmware structure, boot sequence, filesystem layout, key binaries |
| [NETWORK.md](NETWORK.md) | Network services, ports, protocols, streaming architecture |
| [API.md](API.md) | Complete HTTP API reference (both /?custom=1 and CGI interfaces) |
| [APP.md](APP.md) | Android app decompilation, streaming implementation per model |
| [CARDV_BINARY.md](CARDV_BINARY.md) | Advanced `cardv` binary analysis: disassembly, RTSP flow, command table |
| [CUSTOM_FIRMWARE.md](CUSTOM_FIRMWARE.md) | Feasibility analysis for custom firmware development |
| [ref/](ref/) | Extracted reference files from firmware and APK |

## Camera Identification

| Property | Value |
|----------|-------|
| Model | Rove R2-4K-DUAL |
| SoC | SigmaStar (MStar subsidiary), ARM Cortex-A7 |
| Kernel | Linux 4.9.227 |
| Front sensor | Sony IMX675 (4K MIPI, STARVIS 2) |
| Rear sensor | TP9950 (1080p analog-to-digital, AHD mode) |
| WiFi IP | 192.168.1.252 |
| WiFi SSID | ROVE_R2-4K-DUAL_<MAC> |
| WiFi Password | 12345678 |
| Main app binary | `cardv` (CarDV platform) |
| Recording codec | H.265 (HEVC) at 30 Mbps (front 4K), 10 Mbps (rear 1080p) |
| WiFi live stream | MJPEG 640x360 @ 25fps on port 8192 |

## Key Discovery Summary

The camera runs a SigmaStar CarDV platform with four network services. The live WiFi stream is limited to 640x360 MJPEG -- this is a hardware pipeline limitation, not a software restriction. The firmware contains a compiled-in live555 RTSP server with H.264/H.265 capability, but the RTSP encoder channels are commented out in the default configuration. Enabling RTSP would require modifying `default.ini` and potentially rebuilding firmware.

Port 8081 is a GPS WebSocket server, not a video stream.

The most significant finding from binary analysis: the **RTSP server is already running** on port 554 every time WiFi is enabled (`net_toggle.sh` sends `rtsp 1`). It has zero media sessions because no `VencType=3` encoder channels are configured. Adding them to `default.ini` would activate H.264 RTSP streaming without any binary modification.
