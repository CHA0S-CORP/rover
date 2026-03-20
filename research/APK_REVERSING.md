# Rove R2-4K-DUAL: Complete APK & Firmware Reverse Engineering Report

## Abstract

This document presents a comprehensive reverse engineering analysis of the **Rove dashcam Android companion app** (`com.rovedashcam`, ~410 MB across two split APKs) and its interaction with the Rove R2-4K-DUAL dashcam firmware. The work combines static analysis of the decompiled APK (via jadx), binary analysis of the on-device `cardv` ELF binary (via radare2), network traffic inspection, firmware extraction, and reconstruction of undocumented internal APIs. The primary objective was to fully understand the camera's streaming architecture and identify a path to enabling dormant RTSP capabilities that exist in the firmware but are disabled in production.

---

## 1. Target Overview

| Property | Value |
|----------|-------|
| **APK Package** | `com.rovedashcam` |
| **APK Size** | 155 MB (base) + 255 MB (firmware split) |
| **Min SDK** | Android 7.0 (API 24) |
| **Architectures** | arm64-v8a, armeabi-v7a |
| **Framework** | Android Jetpack + Kotlin + Java |
| **Decompiler** | jadx (Java decompilation from DEX) |
| **Camera SoC** | SigmaStar SSC33x/SSC35x ("Ikayaki" family), ARM Cortex-A7 |
| **Camera OS** | Linux 4.9.227 |
| **Main Binary** | `cardv` (629 KB, stripped ARM ELF, Thumb-2, GCC 9.1.0) |

The Rove app is a multi-model companion app supporting 10+ dashcam variants. Each model has its own Fragment class for live video, its own hardcoded IP address, and a distinct streaming implementation. The R2-4K-DUAL model — our primary target — uses MJPEG-over-HTTP at a fixed 640x360 resolution, while other models (R3) use proper RTSP with ijkplayer.

---

## 2. APK Structure and Decompilation

### 2.1 Split APK Architecture

The app ships as **two split APKs**:

1. **`rove_base.apk`** (155 MB) — Main application code, UI resources, native libraries, and base assets.
2. **`rove_split_firmware_pack.apk`** (255 MB) — Firmware tarballs for all supported camera models, stored in `assets/`.

The firmware split APK contains OTA update packages:
- `assets/R2D.tar` — R2-4K-DUAL firmware (29 MB)
- `assets/R2.tar`, `assets/R3.tar`, etc. — Other model firmware

This split APK approach keeps the base install smaller and allows Google Play to deliver firmware updates independently of app code updates.

### 2.2 Decompilation Methodology

The APK was decompiled using **jadx**, which converts Dalvik bytecode (`.dex`) back to readable Java source. Key decompilation targets:

| Package / Class | Purpose |
|----------------|---------|
| `com.rovedashcam.newmodeule.rover24kdual.livevideo.view.RoveR24kDualLiveVideoFragment` | R2-4K-DUAL live video UI |
| `com.rovedashcam.newmodeule.rover2.livevideo.view.Rove2LiveVideoFragment` | Generic R2-series live video |
| `com.rovedashcam.newmodeule.rover3.livevideo.view.Rove3LiveVideoFragment` | R3 live video (RTSP) |
| `com.rovedashcam.newmodeule.rover3ntk.livevideo.view.Rove3NtkLiveVideoFragment` | R3-NTK live video |
| `com.rovedashcam.newmodeule.rover4.livevideo.view.RoveR4ChannelLiveVideoFragment` | R4 live video (WebRTC) |
| `R2RetrofitService.java` | Retrofit HTTP API client interface |

---

## 3. Per-Model Streaming Architecture

The decompiled APK reveals that each camera model uses a fundamentally different streaming approach — there is no unified streaming abstraction.

### 3.1 Model-to-Implementation Mapping

| Model | Fragment Class | Camera IP | Stream Method | Port | Protocol |
|-------|---------------|-----------|---------------|------|----------|
| R2-4K | `Rove2LiveVideoFragment` | 192.168.1.254 | WebView MJPEG `<img>` | 8192 | HTTP multipart |
| R2-4K-Pro | `Rove2LiveVideoFragment` | 192.168.1.250 | WebView MJPEG `<img>` | 8192 | HTTP multipart |
| R2-4K-8MP | `Rove2LiveVideoFragment` | 192.168.1.247 | WebView MJPEG `<img>` | 8192 | HTTP multipart |
| R2-4K-NTK | `Rove2LiveVideoFragment` | 192.168.1.251 | WebView MJPEG `<img>` | 8192 | HTTP multipart |
| **R2-4K-DUAL** | **`RoveR24kDualLiveVideoFragment`** | **192.168.1.252** | **WebView MJPEG `<img>`** | **8192** | **HTTP multipart** |
| R2-4K-DUAL-PRO | `Rove2LiveVideoFragment` | 192.168.1.253 | WebView MJPEG `<img>` | 8192 | HTTP multipart |
| R3 | `Rove3LiveVideoFragment` | 192.168.0.1 | GSYVideoPlayer (IJK) | 554 | RTSP/RTP |
| R3-Sigma | `RoveR3SigmaLiveVideoFragment` | 192.168.1.248 | WebView MJPEG `<img>` | 8192 | HTTP multipart |
| R3-NTK | `Rove3NtkLiveVideoFragment` | 192.168.1.249 | WebView MJPEG `<img>` | 8192 | HTTP multipart |
| R4 | `RoveR4ChannelLiveVideoFragment` | 10.179.121.24 | WebView loadUrl | 8888 | HTTP/WebRTC |

Each camera model uses a different static IP on the 192.168.1.0/24 subnet. This means the app relies entirely on the WiFi SSID (containing the model name) to determine which Fragment to instantiate, and each Fragment hardcodes its own IP and stream URL.

### 3.2 R2-4K-DUAL: MJPEG WebView Implementation (Primary Target)

**Source**: `RoveR24kDualLiveVideoFragment.java`

#### 3.2.1 Hardcoded Stream URL

```java
// Line 95 of RoveR24kDualLiveVideoFragment.java
private String mFilePath = "http://192.168.1.252:8192";
```

The stream URL is a compile-time constant. There is no negotiation, no resolution selection, and no fallback logic.

#### 3.2.2 Connection Sequence

The app performs a strict sequence of HTTP API calls before displaying the stream:

```
Step 1: GET /?custom=1&cmd=2016    → Check camera connected (recording time query)
Step 2: GET /?custom=1&cmd=3014    → Get camera settings/config
Step 3: GET /?custom=1&cmd=3001&par=1  → Set mode to "photo" (unclear why)
Step 4: GET /?custom=1&cmd=2001&par=1  → Start recording
Step 5: Load WebView with MJPEG <img> tag
```

Steps 1-4 use the Novatek-compatible XML API (detailed in Section 5). Step 5 creates an Android `WebView` that renders a minimal HTML page.

#### 3.2.3 HTML Template (WebView Content)

At line 511, the Fragment constructs an HTML string loaded into a WebView:

```html
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0,
          maximum-scale=1.0, user-scalable=no">
    <style>
        html, body {
            margin: 0; padding: 0;
            width: 100%; height: 100%;
            overflow: hidden; background: black;
        }
        #container {
            width: 100%; height: 100%;
            display: flex; align-items: center; justify-content: center;
        }
        #stream {
            width: 100%; height: 100%;
            object-fit: contain;
        }
    </style>
</head>
<body>
    <div id="container">
        <img id="stream" src="http://192.168.1.252:8192" />
    </div>
</body>
</html>
```

The `<img>` tag directly loads the MJPEG multipart HTTP stream. Android's WebView (Chromium-based) natively handles `multipart/x-mixed-replace` content on `<img>` tags, continuously replacing the image as new JPEG frames arrive.

The `object-fit: contain` CSS property performs GPU-accelerated upscaling from the camera's native 640x360 output to the phone's display resolution (typically 1080x2400), masking the low source resolution behind smooth CSS interpolation.

#### 3.2.4 What the App Does NOT Do

This is the most significant finding from the APK analysis — the app makes **zero** quality negotiation calls:

- Does **not** send `cmd=2010` (set liveview size)
- Does **not** send `cmd=2014` (set liveview bitrate)
- Does **not** access port 8081 (GPS WebSocket, not video)
- Does **not** use any native video player (ExoPlayer, ijkplayer, MediaCodec)
- Does **not** offer quality settings for the live stream
- Does **not** attempt RTSP on port 554

The app treats the camera as a dumb MJPEG source with no configurability.

### 3.3 R3: RTSP with ijkplayer (Comparison)

The R3 model demonstrates what proper streaming looks like:

```java
// Rove3LiveVideoFragment.java line 84
private String mFilePath = "rtsp://192.168.0.1:554/livestream/1";

// Line 530-593: GSYVideoPlayer setup
StandardGSYVideoPlayer player = new StandardGSYVideoPlayer(context);
player.setUp(mFilePath, true, "Live RTSP Stream");
player.startPlayLogic();
```

The R3 uses **GSYVideoPlayer** (a wrapper around bilibili's ijkplayer, itself a wrapper around FFmpeg) to decode an RTSP H.264 stream at native resolution via RTP. This delivers dramatically better quality than the R2's MJPEG approach.

### 3.4 Native Libraries

| Library | Size | Used By | Purpose |
|---------|------|---------|---------|
| `libijkffmpeg.so` | ~8 MB | R3 only | FFmpeg core for RTSP/H.264 decoding |
| `libijkplayer.so` | ~2 MB | R3 only | IJKPlayer media engine |
| `libijksdl.so` | ~500 KB | R3 only | SDL rendering layer for video output |
| `libjingle_peerconnection_so.so` | ~15 MB | R4 / TestVideo | Google WebRTC peer connection |
| `libsammp4v2.so` | ~300 KB | File playback | MP4 container parsing |
| `libmp4v2.so` | ~400 KB | File playback | MP4 container parsing |

The presence of ijkplayer (R3) and WebRTC (R4) libraries shows that Rove has engineering capability for modern streaming — the R2's MJPEG limitation is a product/platform decision, not a company-wide technical constraint.

---

## 4. HTTP API Client: Retrofit Service

### 4.1 `R2RetrofitService.java`

The app uses **Retrofit** (Square's type-safe HTTP client for Android, built on OkHttp) to communicate with the camera's Novatek-compatible XML API.

The Retrofit service interface defines all API endpoints as annotated Java methods. Each method maps to a `GET /?custom=1&cmd=<CMD>` request and returns an XML `<Function>` response.

Key characteristics:
- **Base URL**: `http://192.168.1.252/?custom=1` (hardcoded per model)
- **Transport**: OkHttp with short timeouts (camera is on local WiFi, latency <5ms)
- **Response parsing**: XML `<Function>` elements parsed with Android's built-in XML parser
- **Error handling**: Minimal — the app generally ignores failures and retries on next user action

### 4.2 Reconstructed API Client (Python)

Our reverse-engineered Python client (`app/novatek.py`) reimplements the Retrofit service using `httpx`:

```python
class NovatekClient:
    async def _cmd(self, cmd: int, par=None, str_param=None) -> str:
        url = f"{CAM_API_BASE}&cmd={cmd}"
        if par is not None:
            url += f"&par={par}"
        if str_param is not None:
            url += f"&str={str_param}"
        resp = await self._client.get(url)
        return resp.text
```

Key API methods reverse-engineered from the APK:

| Method | Cmd | Parameters | Description |
|--------|-----|-----------|-------------|
| `ping()` | 3016 | — | Heartbeat (returns Status -256, treated as success) |
| `get_status()` | 3019, 3017, 3024, 2016 | — | Battery, free space, SD card, recording state |
| `start_recording()` | 2001 | str=1 | Start video recording |
| `stop_recording()` | 2001 | str=0 | Stop video recording |
| `take_photo()` | 1001 | — | Capture single photo |
| `get_config()` | 3014 | — | Get camera configuration string |
| `set_mode()` | 3001 | par=0/1/2 | Set video/photo/playback mode |
| `get_firmware_version()` | 3012 | — | Returns "0" (unhelpful on this camera) |
| `delete_file()` | 4003 | str=path | Delete file from SD card |
| `get_file_list()` | — | — | HTTP directory listing parse (not a Novatek command) |

---

## 5. Dual API Surface: Novatek XML vs. CGI

A critical discovery: the camera exposes **two completely separate HTTP APIs** on port 80, handled by different code paths.

### 5.1 API Surface 1: Novatek-Compatible XML API

**URL Pattern**: `http://192.168.1.252/?custom=1&cmd=<CMD>&par=<VALUE>&str=<STRING>`
**Handler**: `cardv` binary directly (intercepts requests before GoAhead)
**Response Format**:
```xml
<?xml version="1.0" encoding="UTF-8" ?>
<Function>
  <Cmd>3016</Cmd>
  <Status>0</Status>
  <Parameters>VALUE</Parameters>
</Function>
```

This API is what the Android app uses. It is a **subset** of the standard Novatek dashcam API, with several divergences:

| Feature | Standard Novatek | This Camera (SigmaStar) |
|---------|-----------------|-------------------------|
| Value element | `<Value>` | `<Parameters>` |
| Heartbeat (3016) | Status 0 | Status -256 |
| File list (3015) | Full XML file listing | Just a count |
| Battery (3019) | Numeric level 0-5 | No value, just Status=0 |
| Recording start | `cmd=2001&par=1` | `cmd=2001&str=1` |
| Liveview start (2015) | Supported | Status -256 (unsupported) |
| List commands (3002) | Returns command list | Status -256 |

The `-256` status code means "command not supported." Many standard Novatek commands return this, indicating the SigmaStar firmware only implements a minimal Novatek compatibility layer.

### 5.2 API Surface 2: CGI API

**URL Pattern**: `http://192.168.1.252/cgi-bin/Config.cgi?action=<ACTION>&property=<PROP>&value=<VAL>`
**Handler**: GoAhead web server → `CGI_PROCESS.sh` (50 KB shell script) → `/tmp/cardv_fifo` (named pipe)

This API is **not used by the Android app** but is documented in `CGI_COMMAND.txt` on the device. It provides far richer control:

#### Actions

| Action | Description | Example |
|--------|-------------|---------|
| `set` | Set a property | `set property=Videores&value=1080P30fps` |
| `get` | Get a property | `get property=Camera.Menu.*` |
| `dir` | List directory | `dir property=Video&format=all&count=16&from=0` |
| `del` | Delete file | `del property=$mnt$sdcard$Video$Front$file.mp4` |

#### Streaming Control (CGI-exclusive)

```
set property=streamer&value=start          # Start MJPEG user-stream encoders
set property=streamer&value=stop           # Stop MJPEG user-stream encoders
set property=forceiframe                   # Force I-frame in video encoder
set property=setbitrate&value=1000000      # Change encoder bitrate (bps)
set property=setframerate&value=30         # Change frame rate
set property=setvideogop&value=30          # Change GOP size
```

#### Video Resolution (CGI-exclusive)

```
set property=Videores&value=2160P25fps
set property=Videores&value=1440P30fps
set property=Videores&value=1080P30fps
set property=Videores&value=1080P27.5fpsHDR
set property=Videores&value=720P30fps
set property=Videores&value=720P27.5fpsHDR
set property=Videores&value=720P60fps
set property=Videores&value=VGA
```

#### Image Tuning (CGI-exclusive)

```
set property=Brightness&value=128          # 0-255
set property=Contrast&value=128            # 0-255
set property=Saturation&value=128          # 0-255
set property=Sharpness&value=128           # 0-255
set property=Hue&value=0                   # -180 to 180
set property=Gamma&value=128               # 0-255
set property=Exposure&value=0              # -5 to 5
set property=AE&value=1                    # Auto exposure on/off
```

#### Camera Source Selection

```
set property=Camera.Preview.Source.1.Camid&value=front
set property=Camera.Preview.Source.1.Camid&value=rear
set property=Camera.Preview.RTSP.av&value=4        # Audio+video over RTSP
```

#### Network Configuration

```
get property=Net*
set property=Net.WIFI_AP.SSID&value=MyDashcam
set property=Net.WIFI_AP.CryptoKey&value=newpassword
```

#### Device Information

```
get property=devinfo.fwver
get property=devinfo.macaddr
get property=devinfo.linuxkernelver
```

#### System Commands

```
set property=reset_to_default&value=1      # Factory reset
set property=reboot                        # Reboot camera
set property=TimeSettings&value=2026%2403%2419%2413%2448%2430%24
```

### 5.3 CGI Command Flow

The CGI API follows this execution path:

```
HTTP Request
  → GoAhead web server (port 80)
    → /cgi-bin/Config.cgi (symlink)
      → CGI_PROCESS.sh (50 KB bash script)
        → echo "<command>" > /tmp/cardv_fifo
          → cardv binary (reads FIFO, executes command)
```

`CGI_PROCESS.sh` is a massive case-switch shell script that translates CGI properties into FIFO commands. For example:

```bash
# CGI_PROCESS.sh — Recording control
RECORDING() {
    if [ "$1" = "1" ]; then
        echo "rec 1" > $VIDEOPARAM      # $VIDEOPARAM = /tmp/cardv_fifo
    elif [ "$1" = "0" ]; then
        echo "rec 0" > $VIDEOPARAM
    fi
}

# Video resolution
VIDEO_RESOLUTION_FPS() {
    case $1 in
        "2160P25fps") REC_RES="3840 2160" ;;
        "1080P30fps") REC_RES="1920 1080" ;;
        "720P60fps")  REC_RES="1280 720"  ;;
    esac
    echo "vidres $REC_RES" > $VIDEOPARAM
}

# ISP tuning
BRIGHTNESS() {
    echo "bri $VALUE" > $VIDEOPARAM
}
```

---

## 6. Network Services Architecture

### 6.1 Port Map

| Port | Service | Binary/Library | Protocol | Purpose |
|------|---------|---------------|----------|---------|
| **80** | GoAhead | `/customer/wifi/goahead` + `libgo.so` | HTTP | Web API, CGI, file browser |
| **8192** | samJPGWeb | `libsamJPGWeb.so` (loaded by `cardv`) | HTTP MJPEG | Live video stream (640x360) |
| **8081** | samGPSServer | `libsamJPGWeb.so` (loaded by `cardv`) | WebSocket | GPS NMEA telemetry |
| **554** | live555 | Statically linked in `cardv` | RTSP | H.264/H.265 (disabled) |

### 6.2 Port 80: GoAhead Web Server

**Binary**: `/customer/wifi/goahead` (dynamically linked with `libgo.so`)
**Started by**: `run_goahead.sh` after WiFi AP is up
**Document root**: `/customer/wifi/webserver/www`

Dual function:
1. **Static file server** — SD card browsing via HTML `<table>` directory listings
2. **CGI gateway** — `/cgi-bin/Config.cgi` dispatches to `CGI_PROCESS.sh`

File naming on the SD card: `REC<YYYYMMDD>-<HHMMSS>-<SEQNUM>.mp4` (e.g., `REC20260315-115649-5058.mp4`). Files are 260 MB each (60-second H.265 segments at 30 Mbps).

### 6.3 Port 8192: MJPEG Stream Server

**Library**: `libsamJPGWeb.so` — a CivetWeb-based embedded HTTP server
**Loaded by**: `cardv` via `dlopen("libsamJPGWeb.so")` → `dlsym("module_samjpgweb_start")`
**Server ID**: `samMJPGServer/1.0`

#### MJPEG Protocol Details

- **Content-Type**: `multipart/x-mixed-replace;boundary=arflebarfle`
- **Frame Content-Type**: `image/jpeg`
- **Resolution**: 640x360 (hardcoded in hardware scaler Scl4)
- **Frame rate**: ~25fps (tied to sensor timing)
- **Bitrate**: 2 Mbps JPEG quality
- **Latency**: ~40ms (1 frame + network)
- **Boundary string**: `arflebarfle` (custom, hardcoded in library)

#### MJPEG Startup Sequence

```
1. ap_delay.sh sends: echo "usrstream 0" > /tmp/cardv_fifo
2. cardv starts "user" type (7) JPEG encoders:
   - Venc4/Ch5 (front): Scl4/HWScl5 → 640x360 → JPEG @ 2 Mbps
   - Venc3/Ch10 (rear): Scl3/HWScl5 → 640x360 → JPEG @ 2 Mbps
3. Hardware scaler feeds frames to JPEG encoder at 25fps
4. cardv calls samJPGServer_writeFrame() to push each JPEG to HTTP clients
5. Clients receive continuous multipart MJPEG stream
```

#### Key Exported Functions (from `libsamJPGWeb-strings.txt`)

```c
module_samjpgweb_start()          // Initialize and start the MJPEG server
samJPGServer_writeFrame()         // Push a JPEG frame to all connected clients
startStreaming()                  // Begin frame delivery
stopStreaming()                   // Stop frame delivery
JPGSession_Init()                // Initialize a client session
JPGSession_Deinit()              // Tear down a client session
```

### 6.4 Port 8081: GPS WebSocket Server

**Library**: Same `libsamJPGWeb.so`
**Protocol**: WebSocket (RFC 6455)

Serves GPS NMEA data to WebSocket clients. **This port does NOT serve video** — HTTP GET requests return 404 because it only speaks WebSocket.

Key function: `samGPSServerGetGPSPacket()` — retrieves GPS data for delivery.

```
samGPSServer[%u]:module_samGPSServer_start 8081
samGPSServer[%u]:Websocket server running
```

### 6.5 Port 554: RTSP Server (Dormant)

**Implementation**: live555 library, statically linked into `cardv`
**Trigger**: `echo "rtsp 1" > /tmp/cardv_fifo` (sent by `net_toggle.sh` every time WiFi enables)

The RTSP server is **already running** on port 554 whenever WiFi is enabled. It has zero media sessions because no encoder channels are configured with `VencType=3`. This is the most significant finding of the entire reverse engineering effort — detailed in Section 8.

---

## 7. Firmware Architecture

### 7.1 Firmware Distribution via APK

The OTA firmware update flow:

```
1. Android app extracts R2D.tar from split APK's assets/
2. R2D.tar is written to the camera's SD card root
3. App sends reboot command to camera
4. Camera bootloader detects R2D.tar on SD card
5. Bootloader flashes: IPL → IPL_CUST → UBOOT → R2D.bin
6. Camera reboots into new firmware
```

### 7.2 R2D.tar Contents

```
R2D.tar
├── IPL           — Initial Program Loader (SigmaStar bootROM payload)
├── IPL_CUST      — Customer-specific IPL configuration
├── UBOOT         — U-Boot bootloader
└── R2D.bin       — Combined kernel + rootfs + UBIFS image
```

### 7.3 R2D.bin Layout (from binwalk)

| Offset | Content | Size | Description |
|--------|---------|------|-------------|
| 0x18000 | uImage | ~2.6 MB | ARM Linux 4.9.227, LZMA compressed |
| 0x2BF000 | cpio rootfs | ~8.7 MB | gzip compressed, main root filesystem |
| 0xB59000 | UBIFS | ~17 MB | Flash filesystem (/config, /customer) |

### 7.4 Root Filesystem

```
/
├── bin/                          BusyBox symlinks
├── bootconfig/
│   ├── bin/
│   │   ├── cardv                 MAIN APPLICATION (629 KB ARM ELF)
│   │   ├── default.ini           Video pipeline configuration
│   │   ├── default_norear.ini    Single-camera variant
│   │   ├── default_rzw.ini       Alternate hardware revision
│   │   └── default_norear_rzw.ini
│   ├── demo.sh                   Boot script
│   ├── iqfile/isp_api.bin        ISP image quality tuning
│   ├── modules/4.9.227/          Kernel modules (30+)
│   └── venc_fw/chagall.bin       Video encoder firmware blob
├── lib/
│   ├── libsamJPGWeb.so           MJPEG + GPS WebSocket server
│   └── libmi_*.so                SigmaStar MI framework libraries
└── customer/
    └── wifi/
        ├── goahead               GoAhead web server
        ├── CGI_PROCESS.sh        CGI command handler (50 KB)
        ├── net_toggle.sh         WiFi enable/disable + RTSP toggle
        ├── ap_delay.sh           AP startup (triggers MJPEG stream)
        └── hostapd.conf          5GHz WiFi AP configuration
```

### 7.5 Boot Sequence

```
Power on
  └─ demo.sh
       ├─ GPIO init (power, camera detect, hw version)
       ├─ Load 25+ kernel modules in order:
       │   Core:    mhal.ko, mi_common.ko, mi_sys.ko
       │   Video:   mi_sensor.ko, mi_isp.ko, mi_scl.ko, mi_venc.ko
       │   Display: mi_fb.ko, mi_mipitx.ko, mi_disp.ko, mi_panel.ko
       │   Sensors: imx675_MIPI.ko (front 4K), tp9950_MIPI.ko (rear 1080p)
       │   Storage: kdrv_sdmmc.ko, fat.ko, vfat.ko
       ├─ Configure clocks: ISP 432MHz, Scaler 480MHz, VENC 384MHz
       ├─ Start cardv: cardv /bootconfig/bin/default.ini &
       ├─ Mount /customer (UBIFS)
       ├─ Load UVC webcam driver: g_webcam.ko streaming_maxpacket=3072
       └─ Load WiFi driver: rcInsDriver.sh

WiFi enable (button press)
  └─ net_toggle.sh
       ├─ echo "rtsp 1" > /tmp/cardv_fifo      ← RTSP server starts
       ├─ nvconf set Camera.Menu.WiFi ON
       └─ ap.sh start
            └─ ap_delay.sh
                 ├─ Load WiFi firmware (bcmdhd.ko + BCM43456 firmware)
                 ├─ ifconfig wlan0 up
                 ├─ Start hostapd (5GHz AP, SSID: ROVE_R2-4K-DUAL_<MAC>)
                 ├─ Start udhcpd (DHCP for connected clients)
                 ├─ echo "usrstream 0" > /tmp/cardv_fifo  ← MJPEG starts
                 └─ run_goahead.sh                         ← Web server starts
```

---

## 8. `cardv` Binary: Deep Analysis via radare2

### 8.1 Binary Profile

| Property | Value |
|----------|-------|
| Size | 644,140 bytes (629 KB) |
| Architecture | ARM 32-bit, EABI5, Thumb-2 |
| Compiler | GCC 9.1.0 |
| Linking | Dynamic (42 shared libraries) |
| Symbols | 3,173 total, 2,597 functions |
| Code size | 329 KB (.text) |
| BSS | 113 KB (uninitialized data) |
| Security | NX enabled, no stack canary, partial RELRO |

### 8.2 Key Linked Libraries

| Library | Purpose |
|---------|---------|
| `libmi_venc.so` | SigmaStar hardware video encoder |
| `libmi_isp.so` | Image signal processor |
| `libmi_scl.so` | Hardware scaler |
| `libmi_vif.so` | Video input frontend |
| `libmi_ai.so` / `libmi_ao.so` | Audio input/output |
| `libsamJPGWeb.so` | MJPEG streaming + GPS WebSocket |
| `libavformat.so.58` | FFmpeg format layer |
| `libavcodec.so.58` | FFmpeg codec layer |
| `libfdk-aac.so.2` | AAC audio codec (Fraunhofer) |
| `libIPC_msg.so` | Inter-process communication |

### 8.3 FIFO Command Dispatch System

Commands arrive via `/tmp/cardv_fifo` and are dispatched through a linked-list command table.

#### Registration: `CarDVAddCmdHandler()` at `0x000654d4`

```c
// Reconstructed from disassembly
void CarDVAddCmdHandler(const char* name, int argCount, void (*callback)(int, char**));
```

Each handler is a 0x14-byte linked list node. `CarDVExecCmdHandler()` at `0x000655a0` walks the list, matches by `strcmp`, and invokes the callback.

#### Complete Command Table (55+ commands)

**System commands** (`system_process_cmd`):
| Command | Args | Description |
|---------|------|-------------|
| `rec` | 1 | Start/stop recording |
| `capture` | 0 | Take photo |
| `rtsp` | 1 | Enable/disable live555 RTSP server |
| `usrstream` | 1 | Start/stop user-stream MJPEG encoders |
| `park` | 1 | Parking mode (0-3) |
| `gsensor` | 1 | G-sensor sensitivity (0-3) |
| `zoom` | — | Digital zoom |
| `voice` | — | Voice recording on/off |
| `srcchg` | — | Switch camera source (front/rear) |
| `prerec` | — | Pre-record buffer toggle |
| `autorec` | — | Auto record toggle |
| `flip` | — | Video flip/rotate |
| `reset` | — | Factory reset |
| `reboot` | — | System reboot |
| `quit` | — | Exit cardv process |
| `dumpimpl` | — | **Undocumented**: dump internal state |
| `dumpimpl2` | — | **Undocumented**: dump internal state v2 |

**Video commands** (`video_process_cmd`):
| Command | Args | Description |
|---------|------|-------------|
| `bitrate` | 2 | Set encoder bitrate (`bitrate <ch> <value>`) |
| `vidres` | 3 | Set video resolution (`vidres <id> <w> <h>`) |
| `capres` | 3 | Set capture resolution |
| `codec` | — | Change codec (H.264/H.265) at runtime |
| `setFrameRate` | 1 | Set frame rate |
| `seamless` | — | Seamless recording restart |
| `loop` | — | Loop recording time |
| `timelapse` | — | Timelapse recording |
| `slowmotion` | — | Slow motion mode |
| `lock` | — | Lock current recording (protect from overwrite) |

**ISP commands** (`isp_process_cmd`):
| Command | Description |
|---------|-------------|
| `scene` | Scene mode |
| `flicker` | Anti-flicker (50/60Hz) |
| `shutter` | Shutter speed |
| `gamma` | Gamma correction |
| `effect` | Image effect |
| `night` | Night mode |
| `bri` / `sat` / `iso` / `wdr` / `hdr` | ISP image adjustments |

**Audio commands** (`audio_process_cmd`):
| Command | Description |
|---------|-------------|
| `audioplay` | Play audio file |
| `audiorec` | Audio recording & RTSP mute |
| `pbvolume` | Playback volume |
| `audio` | Audio on/off |

**Display commands** (`display_process_cmd`):
| Command | Description |
|---------|-------------|
| `disp` | Display control |
| `sclrotate` | SCL rotation |
| `lcdbri` / `lcdcon` / `lcdhue` / `lcdsat` | LCD adjustments |

**Other**:
| Command | Handler | Description |
|---------|---------|-------------|
| `uvc` | `uvc_process_cmd` | USB webcam mode |
| `muxdebug` | `mux_process_cmd` | Muxer debug logging |

### 8.4 Hardware Video Encoding Pipeline

The `default.ini` configuration file defines the entire hardware encoding pipeline. The `cardv` binary parses this at startup and configures the SigmaStar MI (Media Interface) hardware accordingly.

#### Scaler Chains (Hardware Image Scaling)

```
Front Camera: Sony IMX675 (4K MIPI, STARVIS 2)
  └─ ISP Dev 0 (4K processing)
       ├─ Scl0/HWScl0: 3840x2160 → Venc0 (H.265 recording @ 30 Mbps)
       ├─ Scl0/HWScl1: 640x360   → Venc1 (H.264 UVC webcam @ 8 Mbps)
       ├─ Scl0/HWScl4: 1920x1080 → [available for sub-recording]
       ├─ Scl1/HWScl5: 432x240   → [display PIP thumbnail]
       ├─ Scl2/HWScl5: 160x90    → [motion detection / VDF]
       ├─ Scl3/HWScl5: 256x144   → [display PIP rear overlay]
       └─ Scl4/HWScl5: 640x360   → Venc4 (JPEG WiFi stream @ 2 Mbps)

Rear Camera: TP9950 (1080p analog-to-digital, AHD)
  └─ VIF Dev 12 (analog decode)
       ├─ Scl0/HWScl2: 1920x1080 → Venc0 (H.265 recording @ 10 Mbps)
       ├─ Scl0/HWScl3: 640x360   → [sub-stream scaler]
       ├─ Scl3/HWScl5: 640x360   → Venc3 (JPEG WiFi stream @ 2 Mbps)
       └─ Scl4/HWScl5: 1920x1080 → [display full-screen rear]
```

#### Encoder Channel Table

| Cam | Venc | Type | Codec | Resolution | Bitrate | Purpose |
|-----|------|------|-------|------------|---------|---------|
| Front | 0 | rec (0) | H.265 | 3840x2160 | 30 Mbps | SD recording |
| Front | 1 | uvc (4) | H.264 | 640x360 | 8 Mbps | USB webcam |
| Front | 2 | cap (2) | JPEG | 2048x2048 | — | Photo capture |
| Front | ~~3~~ | ~~subrec (1)~~ | ~~H.264~~ | ~~640x360~~ | ~~800 Kbps~~ | **Commented out** |
| Front | 4 | thumb (5) | JPEG | 720x720 | — | Thumbnails |
| Front | 5 | user (7) | JPEG | 640x360 | 2 Mbps | **WiFi MJPEG** |
| Rear | 6 | rec (0) | H.265 | 1920x1080 | 10 Mbps | SD recording |
| Rear | 7 | cap (2) | JPEG | 2048x2048 | — | Photo capture |
| Rear | ~~8~~ | ~~subrec (1)~~ | ~~H.264~~ | ~~640x360~~ | ~~800 Kbps~~ | **Commented out** |
| Rear | 9 | thumb (5) | JPEG | 720x720 | — | Thumbnails |
| Rear | 10 | user (7) | JPEG | 640x360 | 2 Mbps | **WiFi MJPEG** |

`VencType` enum: `rec=0, subrec=1, cap=2, rtsp=3, uvc=4, thumb=5, share=6, user=7`

#### The Commented-Out Channels (from `default.ini`)

```ini
# Front camera sub-stream — COMMENTED OUT
#Venc3Chn = 3
#Venc3Type = 1           # subrec
#Venc3Codec = 0          # H.264
#Venc3BitRate = 800000   # 800 Kbps
#Venc3InBindMod = 34
#Venc3InBindDev = 0
#Venc3InBindChn = 0
#Venc3InBindPort = 1     # Scl0/HWScl1 (640x360)

# Rear camera sub-stream — COMMENTED OUT
#Venc2Chn = 8
#Venc2Type = 1           # subrec
#Venc2Codec = 0          # H.264
#Venc2BitRate = 800000   # 800 Kbps
```

These channels were designed to feed an RTSP server but were disabled — likely to conserve memory on the dual-camera model (each encoder channel requires DMA buffers from limited SRAM).

---

## 9. live555 RTSP Server: The Dormant Capability

### 9.1 Class Hierarchy (Reconstructed from Disassembly)

```
RTSPServer (stock live555)
  └─ Created by live555::createNew()

live555 (custom wrapper class, 0x28 bytes)
  ├─ [+0x00] state: 0=uninit, 1=created, 2=stopped, 3=stopping
  ├─ [+0x04] stop flag
  ├─ [+0x08] TaskScheduler*
  ├─ [+0x0C] UsageEnvironment*
  ├─ [+0x14] RTSPServer*
  ├─ [+0x18] ServerMediaSession* [0]   (front camera)
  ├─ [+0x1C] ServerMediaSession* [1]   (rear camera)
  └─ [+0x24] session count (max 2, hardcoded)

LiveVideoServerMediaSubsession (custom, extends OnDemandServerMediaSubsession)
  ├─ createNewStreamSource() → LiveVideoSource or LiveJPEGVideoStreamSource
  ├─ createNewRTPSink() → H264VideoRTPSink or H265VideoRTPSink
  └─ adjustBitRateByRtd() → Adaptive bitrate based on round-trip delay

LiveVideoSource (custom, extends FramedSource)
  ├─ Reads from MI_VENC hardware encoder
  ├─ findH264NalUnit() — NAL unit parsing for H.264
  ├─ findH265NalUnit() — NAL unit parsing for H.265
  └─ incomingDataHandler1() — Main frame processing (816 bytes of code)

LiveJPEGVideoStreamSource (custom, extends JPEGVideoSource)
  └─ Wraps a FramedSource for JPEG-over-RTP

LivePCMAAudioServerMediaSubsession (custom)
  └─ G.711 A-law audio over RTP
```

### 9.2 Key Addresses (radare2)

| Symbol | Address | Description |
|--------|---------|-------------|
| `live555::live555()` | `0x00065ba0` | Constructor |
| `live555::createNew()` | `0x00065c98` | Full server setup |
| `live555::createServerMediaSession()` | `0x00065d7c` | Create per-camera stream session |
| `live555::startLive555Server()` | `0x00065e2c` | Start serving (bind port, enter event loop) |
| `live555::stopLive555Server()` | `0x00065e8c` | Stop serving |
| `live555::fRtspServerPortNum` | `0x000bc89c` | Port number storage (.data section, writable) |
| `live555::fIsRunning` | `0x000c8064` | Running flag |
| `live555_Task` | `0x00065af4` | Event loop thread entry |
| `LiveVideoSource::createNew()` | `0x00066cd0` | Video source factory |
| `LiveVideoSource::incomingDataHandler1()` | `0x00066eac` | Frame processing |
| `LiveVideoSource::findH264NalUnit()` | `0x00066d0c` | H.264 NAL parser |
| `LiveVideoSource::findH265NalUnit()` | `0x00066dc4` | H.265 NAL parser |

### 9.3 RTSP Initialization Flow (Disassembled)

When `echo "rtsp 1" > /tmp/cardv_fifo` is received by `system_process_cmd` at `0x000633dc`:

```
system_process_cmd:
  │
  ├─ Check if live555 instance exists (global pointer)
  │   If NULL:
  │     └─ live555::createNew()
  │          ├─ BasicTaskScheduler::createNew(10000)    // 10s timeout
  │          ├─ fRtspServerPortNum = 554
  │          ├─ BasicUsageEnvironment::createNew()
  │          └─ RTSPServer::createNew(env, Port(554), NULL, 6)
  │
  ├─ Iterate all VENC channels (0..31, stride 0x7C):
  │     For each channel:
  │       ldrb r3, [encoder+0x68]    // load VencType
  │       cmp  r3, #3                // is it RTSP type?
  │       bne  skip                  // no → skip
  │       │
  │       └─ live555::createServerMediaSession(videoEnc, audioEnc, name, flag)
  │            ├─ Check session count <= 2 (HARDCODED MAX)
  │            ├─ ServerMediaSession::createNew(env, name)
  │            ├─ If audio: LivePCMAAudioServerMediaSubsession::createNew()
  │            ├─ LiveVideoServerMediaSubsession::createNew(env, flag, videoEnc)
  │            └─ session->addSubsession(...)
  │
  └─ live555::startLive555Server()
       ├─ For each session: addServerMediaSession(), print rtspURL()
       ├─ fIsRunning = 1
       └─ doEventLoop() (blocks in live555_Task thread)
```

### 9.4 The VencType=3 Gate (Critical Finding)

The assembly at `0x000633dc` contains this critical gate:

```arm
ldrb r3, [r3, #0x68]    ; Load VencType from encoder object (+0x68)
cmp  r3, #3              ; Compare with RTSP type constant
bne  .skip_channel       ; Skip if not RTSP
```

**Current state**: The RTSP server starts successfully every time WiFi enables (via `net_toggle.sh` → `echo "rtsp 1" > /tmp/cardv_fifo`). It creates an `RTSPServer` on port 554, enters the event loop — but creates **zero `ServerMediaSession` objects** because no encoder channels have `VencType=3`.

**To activate**: Uncomment the sub-stream encoder channels in `default.ini` and change their type from `1` (subrec) to `3` (rtsp):

```ini
Venc3Chn = 3
Venc3Type = 3          # Changed from 1 (subrec) to 3 (rtsp)
Venc3Codec = 0          # H.264
Venc3BitRate = 2000000   # 2 Mbps
Venc3InBindMod = 34
Venc3InBindDev = 0
Venc3InBindChn = 0
Venc3InBindPort = 1     # Scl0/HWScl1 (640x360)
```

### 9.5 Stream_Task Thread (Per-Encoder Data Path)

At `0x0005777c`, each active encoder channel runs a `Stream_Task` thread:

```c
// Reconstructed from disassembly
void Stream_Task(MI_VideoEncoder* enc) {
    while (1) {
        enc->pollingStream();           // Wait for frame from hardware
        MI_VENC_GetStream();            // Get encoded frame buffer

        if (enc->VencType > 2) {        // Type 3 (RTSP), 4 (UVC), etc.
            enc->handlerStreamPost();   // Feed to live555 or UVC
        } else {                        // Type 0, 1 (recording)
            // Muxer/file write path
        }

        MI_VENC_ReleaseStream();        // Release frame buffer
    }
}
```

This confirms the RTSP data path is complete: hardware encoder → `Stream_Task` → `handlerStreamPost()` → `LiveVideoSource` → `FramedSource::afterGetting()` → RTP packetization → network.

### 9.6 MI_VideoEncoder Internal Structure

Reconstructed from disassembly (0x100+ bytes per instance):

| Offset | Type | Field | Notes |
|--------|------|-------|-------|
| +0x00 | int | channel index | VENC channel number |
| +0x04 | int | MI_VENC device | Device ID |
| +0x08 | int | state | -1 = uninitialized |
| +0x20 | struct | CarDV_VencAttr_s | 0x78 bytes, copied from INI |
| +0x28 | byte | VencType (in attr) | Offset +0x28 within attr struct |
| +0x68 | byte | VencType (copy) | Accessed for RTSP check |
| +0xF0 | byte | rtspAudioActive | Set by start/stopAudioRtsp |
| +0xF8 | byte | streamActive | Checked in Stream_Task |

#### CarDV_VencAttr_s (0x78 bytes)

| Offset | Type | Field |
|--------|------|-------|
| +0x00 | byte | enabled |
| +0x02 | byte | cameraIndex |
| +0x0C | int | MaxW |
| +0x10 | int | MaxH |
| +0x14 | int | BufSize |
| +0x18 | int | BitRate |
| +0x1C | byte | codec (0=H264, 1=H265, 2=JPEG) |
| +0x20 | int | GOP (default 0x50 = 80 frames) |
| +0x24 | int | VencChn |
| +0x28 | byte | VencType |
| +0x2C | int | actual channel from INI |
| +0x44 | int | FPS numerator |
| +0x4C | int | BufSize (computed: bitrate/8 * 4) |

#### Codec Values (from `setBitrate()` and `initVideoEncoder()`)

| Value | Codec | Context |
|-------|-------|---------|
| 0 | H.264 | Record, RTSP, UVC |
| 1 | H.265 | Record |
| 2 | JPEG | Capture, thumbnails, user-stream |
| 6 | Special | UVC (type 4) |
| 8 | H.264 | RTSP type 3 (setBitrate path) |
| 9 | H.265 | RTSP type 3 (setBitrate path) |

### 9.7 Additional RTSP Findings

1. **Adaptive bitrate**: `LiveVideoServerMediaSubsession::adjustBitRateByRtd()` at `0x000664e8` dynamically adjusts encoder bitrate based on RTCP round-trip delay measurements — a QoS feature for unstable WiFi.

2. **Audio support**: G.711 A-law audio via `LivePCMAAudioServerMediaSubsession`. Controlled by `Camera.Preview.RTSP.av` nvconf key (value 4 = audio+video) and `audiorec` FIFO command.

3. **Maximum 2 streams**: Hardcoded check `cmp r0, 2; bgt return_error` in `createServerMediaSession()`. Sufficient for front + rear camera.

4. **Writable port number**: `fRtspServerPortNum` at `0x000bc89c` is in `.data` (not `.rodata`). If modified before `createNew()` is called, the RTSP port could be changed.

5. **VencType=3 initialization**: Falls through to generic encoder creation path in `initVideoEncoder()`. The encoder channel **will** be created — `setBitrate()` handles type=3 explicitly for H.264 (codec=8) and H.265 (codec=9).

---

## 10. Reconstructed Rover Proxy Application

Based on the reverse engineering findings, a Python proxy application was built to sit between the camera and end users:

### 10.1 Architecture

```
Camera (192.168.1.252)          Rover Proxy (Raspberry Pi)         Clients
  :8192 (MJPEG) ──────────────→ StreamManager ────────────────→ /api/stream/mjpeg
                                     │
                                     ├─ ffmpeg MJPEG→H.264 ──→ /hls/live.m3u8
                                     │
  :554 (RTSP, if enabled) ────→     └─ ffmpeg RTSP→copy ────→ /hls/live.m3u8

  :80 (Novatek XML API) ──────→ NovatekClient ────────────────→ /api/status
                                                                  /api/record/start
                                                                  /api/record/stop
                                                                  /api/photo
                                                                  /api/files
```

### 10.2 `NovatekClient` (`app/novatek.py`)

Async HTTP client (httpx) implementing the Novatek XML API:

- **`_cmd(cmd, par, str_param)`** — Core request method, constructs `/?custom=1&cmd=X` URL
- **`_cmd_xml()`** — Parses XML `<Function>` response
- **`_xml_param()`** — Extracts value from `<Parameters>`, `<Value>`, or `<String>` (handles this camera's non-standard response format)
- **`ping()`** — Heartbeat via cmd 3016 (ignores -256 status)
- **`get_status()`** — Aggregates battery (3019), free space (3017), SD card (3024), recording time (2016)
- **`get_file_list()`** — Recursively parses HTML directory listings (not a Novatek command)
- **`_DirListingParser`** — HTMLParser subclass that extracts file entries from GoAhead's `<table>` directory listings

### 10.3 `StreamManager` (`app/stream.py`)

Manages three streaming modes:

1. **MJPEG Proxy** — Direct passthrough of `multipart/x-mixed-replace` from camera port 8192. Zero transcoding overhead, ~40ms latency. Frame caching for snapshot endpoint.

2. **MJPEG→HLS Transcoder** — ffmpeg process: reads MJPEG, encodes to H.264 (libx264 ultrafast/zerolatency), outputs HLS segments. ~5s latency, embeddable in `<video>` tags via hls.js. Auto-restart with exponential backoff (5 retries).

3. **RTSP→HLS (Copy)** — ffmpeg process: reads RTSP H.264 stream, copies (no transcode) to HLS segments. Only works if RTSP is enabled on camera. Near-zero CPU usage since it's a protocol conversion, not a transcode.

### 10.4 FastAPI Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/status` | — | Camera status (battery, SD, recording) |
| `POST /api/record/start` | — | Start recording |
| `POST /api/record/stop` | — | Stop recording |
| `POST /api/photo` | — | Take photo |
| `GET /api/config` | — | Raw camera config |
| `POST /api/mode` | `{mode: 0/1/2}` | Set video/photo/playback |
| `GET /api/files` | — | List all files on SD card |
| `GET /api/files/download?path=...` | — | Stream file download |
| `DELETE /api/files?path=...` | — | Delete file |
| `GET /api/stream/mjpeg` | — | MJPEG proxy (for `<img>` tag) |
| `GET /api/stream/snapshot` | — | Single JPEG frame |
| `POST /api/stream/hls/start` | — | Start MJPEG→HLS transcoder |
| `POST /api/stream/hls/stop` | — | Stop HLS transcoder |
| `GET /hls/{filename}` | — | Serve HLS segments (.m3u8, .ts) |
| `POST /api/stream/rtsp/start` | — | Start RTSP→HLS passthrough |
| `POST /api/stream/rtsp/stop` | — | Stop RTSP→HLS |
| `GET /api/stream/status` | — | Stream manager state |

### 10.5 Firmware Build Toolchain

A Makefile-based toolchain (`firmware/Makefile`) automates the firmware modification cycle:

```
make setup        # Extract R2D.tar from APK → R2D.bin + rootfs
make backup       # Back up stock default.ini
make edit         # Open default.ini in $EDITOR
make diff         # Review changes from stock
make build        # Repack rootfs → R2D.bin
make tar          # Create R2D.tar
make flash-sd SD=/Volumes/SDCARD  # Copy to SD card for OTA
make verify       # Post-flash verification (ping, RTSP, MJPEG)
```

---

## 11. Security Observations

1. **Default WiFi password**: `12345678` — trivially guessable. Anyone within WiFi range can connect.
2. **No authentication on APIs**: Both the Novatek XML API and CGI API accept unauthenticated requests. GoAhead's `auth.txt` has no entries configured.
3. **FIFO command injection**: `CGI_PROCESS.sh` passes user-supplied values to shell commands with minimal sanitization. The `$` path delimiter in `del` actions could potentially be exploited.
4. **No HTTPS/TLS**: All communication is plaintext HTTP over WiFi.
5. **Partial RELRO, no stack canary**: The `cardv` binary has weak exploit mitigations. NX is enabled (non-executable stack) but no stack canary protection.
6. **Factory reset via unauthenticated HTTP**: `set property=reset_to_default&value=1` wipes all camera settings.

---

## 12. Key Findings Summary

1. **The Android app is deliberately simple** — it uses a WebView with an `<img>` tag to display MJPEG. No native video player, no quality negotiation, no resolution selection. The app treats the camera as a black box.

2. **Two separate API surfaces exist** — the Novatek XML API (used by the app) and the CGI API (undocumented, far richer). The CGI API provides streaming control, image tuning, and RTSP configuration that the app never touches.

3. **RTSP is fully implemented in the firmware binary** — the `cardv` binary contains a complete live555 RTSP server with custom H.264/H.265/JPEG sources, adaptive bitrate, and audio support. The code path is complete and functional.

4. **RTSP is disabled by configuration, not code** — the sub-stream encoder channels (`VencType=3`) are commented out in `default.ini`. The RTSP server starts every time WiFi enables but has zero media sessions to serve.

5. **Enabling RTSP requires only a config change** — uncommenting the encoder channels and changing `VencType` from 1 to 3 in `default.ini` would activate H.264 RTSP streaming without any binary modification.

6. **The firmware is distributed inside the APK** — enabling extraction, modification, and reflashing through the normal OTA update mechanism.

7. **Undocumented debug commands exist** — `dumpimpl` and `dumpimpl2` FIFO commands may dump internal encoder/pipeline state, useful for runtime debugging.

8. **The 640x360 MJPEG limitation is a hardware pipeline configuration choice** — the SoC is capable of much higher resolution streaming, but the scaler feeding the WiFi stream encoder is configured for 640x360 to conserve bandwidth and encoder resources.
