# Hardware Architecture

## System-on-Chip

The Rove R2-4K-DUAL uses a **SigmaStar** SoC (subsidiary of MStar Semiconductor, acquired by MediaTek). The exact part number is not printed on the chip but the kernel modules and SDK artifacts identify it as part of the SigmaStar "Ikayaki" family (SSC33x/SSC35x series).

Evidence:
- Kernel module paths: `/sys/devices/virtual/mstar/`
- Register access tool: `riu_w` (MStar Register Interface Unit)
- ISP clock domain: `/sys/devices/virtual/mstar/isp0/isp_clk`
- Video encoder firmware: `chagall.bin` (SigmaStar codename)
- Max H.26x encode: 4608x2592 (from `mi_venc.ko` parameters)

## Image Sensors

### Front Camera: Sony IMX675 (STARVIS 2)
- **Interface**: 4-lane MIPI CSI-2
- **Kernel module**: `imx675_MIPI.ko chmap=1 lane_num=4`
- **Max resolution**: 3840x2160 (4K UHD)
- **ISP binding**: VIF Dev 0 → ISP Dev 0 → Scaler chains
- **HDR**: Supported (HDR mode flag in `default.ini`, 27.5fps HDR modes in CGI)
- **STARVIS 2**: Sony's back-illuminated pixel technology for improved low-light

### Rear Camera: TP9950 (Analog-to-Digital)
- **Interface**: 2-lane MIPI (after analog decoding)
- **Kernel module**: `tp9950_MIPI.ko chmap=8 lane_num=2`
- **Analog mode**: AHD (Analog High Definition), mode=3 in config
- **Resolution**: 1920x1080 @ 25fps (PAL-based timing)
- **VIF Dev**: 12 (separate from front camera)

The TP9950 is a Techpoint analog video decoder that converts the analog camera signal to digital MIPI. The rear camera is a standard AHD security camera module connected via coax, not a digital MIPI sensor.

## Video Encoding Pipeline

The SoC's hardware video encoder (`mi_venc`) supports simultaneous encoding of multiple streams at different resolutions and codecs. The `default.ini` configures this pipeline:

### Scaler Chains (Hardware Image Scaling)

The ISP output feeds into multiple hardware scaler (SCL) instances that produce different resolution streams:

```
Front ISP Output (4K)
  ├─ Scl0/HWScl0: 3840x2160 → Venc0 (H.265 recording)
  ├─ Scl0/HWScl1: 640x360   → Venc1 (H.264 UVC webcam)
  ├─ Scl0/HWScl4: 1920x1080 → [available for sub-recording]
  ├─ Scl1/HWScl5: 432x240   → [display PIP thumbnail]
  ├─ Scl2/HWScl5: 160x90    → [motion detection / VDF]
  ├─ Scl3/HWScl5: 256x144   → [display PIP rear overlay]
  └─ Scl4/HWScl5: 640x360   → Venc4 (JPEG WiFi stream)

Rear Analog Input (1080p)
  ├─ Scl0/HWScl2: 1920x1080 → Venc0 (H.265 recording)
  ├─ Scl0/HWScl3: 640x360   → [sub-stream scaler]
  ├─ Scl1/HWScl5: 160x90    → [motion detection]
  ├─ Scl2/HWScl5: 256x144   → [thumbnail]
  ├─ Scl3/HWScl5: 640x360   → Venc3 (JPEG WiFi stream)
  └─ Scl4/HWScl5: 1920x1080 → [display full-screen rear]
```

### Encoder Channels

| Cam | Venc Ch | Type | Codec | Resolution | Bitrate | Source Scaler | Notes |
|-----|---------|------|-------|------------|---------|---------------|-------|
| Front | 0 | rec (0) | H.265 | 3840x2160 | 30 Mbps | Scl0/HWScl0 | SD card recording |
| Front | 1 | uvc (4) | H.264 | 640x360 | 8 Mbps | Scl0/HWScl1 | USB webcam (g_webcam) |
| Front | 2 | cap (2) | JPEG | up to 2048x2048 | - | Scl0/HWScl1 | Photo capture |
| Front | ~~3~~ | ~~subrec (1)~~ | ~~H.264~~ | ~~640x360~~ | ~~800 Kbps~~ | - | **Commented out** |
| Front | 4 | thumb (5) | JPEG | up to 720x720 | - | Scl1/HWScl5 | Thumbnail generation |
| Front | 5 | user (7) | JPEG | 640x360 | 2 Mbps | Scl4/HWScl5 | **WiFi MJPEG stream** |
| Rear | 6 | rec (0) | H.265 | 1920x1080 | 10 Mbps | Scl4/HWScl5 | SD card recording |
| Rear | 7 | cap (2) | JPEG | up to 2048x2048 | - | Scl4/HWScl5 | Photo capture |
| Rear | ~~8~~ | ~~subrec (1)~~ | ~~H.264~~ | ~~640x360~~ | ~~800 Kbps~~ | - | **Commented out** |
| Rear | 9 | thumb (5) | JPEG | up to 720x720 | - | Scl1/HWScl5 | Thumbnail generation |
| Rear | 10 | user (7) | JPEG | 640x360 | 2 Mbps | Scl3/HWScl5 | **WiFi MJPEG stream** |

The `VencType` enum: `rec=0, subrec=1, cap=2, rtsp=3, uvc=4, thumb=5, share=6, user=7`

### Commented-Out Sub-Recording Channels

Both cameras have a sub-recording encoder channel (type=1, subrec) that is **commented out** in `default.ini`:

```ini
# Front camera - COMMENTED OUT
#Venc3Chn = 3
#Venc3Type = 1           # subrec
#Venc3Codec = 0          # H.264
#Venc3BitRate = 800000   # 800 Kbps
#Venc3InBindMod = 34
#Venc3InBindDev = 0
#Venc3InBindChn = 0
#Venc3InBindPort = 1     # Scl0/HWScl1 (640x360)

# Rear camera - COMMENTED OUT
#Venc2Chn = 8
#Venc2Type = 1           # subrec
#Venc2Codec = 0          # H.264
#Venc2BitRate = 800000   # 800 Kbps
```

These channels would feed the live555 RTSP server if enabled. Their absence means RTSP has no encoder source to stream from, even though the RTSP server code is compiled into the `cardv` binary.

## Display

The camera has a built-in MIPI display (likely a small LCD panel), configured as a 360x640 portrait display with 90-degree rotation. The display shows a picture-in-picture (PIP) layout with the main camera full-screen and the secondary camera in a small overlay.

## GPIO Functions

From `demo.sh`:
- **GPIO 86**: Output, set high at boot (likely power enable)
- **GPIO 42, 52**: Input, hardware version detection (both low = v0.0)
- **GPIO 78**: Output, set high (likely rear camera power)
- **GPIO 88**: Output, set high (display backlight or power)
- **GPIO 111**: Output, set low (unknown)
- **GPIO 6**: Input, rear camera detection (low = rear present, high = no rear)

The GPIO 6 input determines which `default.ini` variant is loaded:
- GPIO 6 low + v0.0: `default.ini` (dual camera)
- GPIO 6 low + other: `default_rzw.ini` (dual camera, alternate)
- GPIO 6 high + v0.0: `default_norear.ini` (front only)
- GPIO 6 high + other: `default_norear_rzw.ini` (front only, alternate)
