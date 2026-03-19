# Network Services

## WiFi Configuration

The camera operates as a WiFi access point using a Broadcom AP6256 module (BCM43456, dual-band 2.4/5GHz, 802.11ac).

| Setting | Value | Source |
|---------|-------|--------|
| SSID | `ROVE_R2-4K-DUAL_<MAC_suffix>` | `nvconf get 1 wireless.ap.ssid` |
| Password | `12345678` | `nvconf get 1 wireless.ap.wpa.psk` |
| IP Address | `192.168.1.252` | `nvconf get 1 wireless.ap.ipaddr` |
| Band | 5GHz default, 2.4GHz configurable | `Camera.Menu.smWiFiMode` |
| hostapd | Standard Linux hostapd | `/customer/wifi/hostapd.conf` |
| DHCP | udhcpd | `/customer/wifi/udhcpd-ap.conf` |
| Station mode | Supported | `sta.sh`, `wpa_supplicant.conf` |

## Port Map

| Port | Service | Binary/Library | Protocol | Purpose |
|------|---------|---------------|----------|---------|
| **80** | GoAhead | `/customer/wifi/goahead` + `libgo.so` | HTTP | Web API, CGI commands, file browser |
| **8192** | samJPGWeb | `libsamJPGWeb.so` (loaded by `cardv`) | HTTP MJPEG | Live video stream (640x360 JPEG @ 25fps) |
| **8081** | samGPSServer | `libsamJPGWeb.so` (loaded by `cardv`) | WebSocket | GPS telemetry data |
| **554** | live555 | Statically linked in `cardv` | RTSP | H.264/H.265 stream (disabled by default) |

## Port 80: GoAhead Web Server

**Binary**: `/customer/wifi/goahead` (dynamically linked with `libgo.so`)
**Started by**: `run_goahead.sh` after WiFi AP is up
**Document root**: `/customer/wifi/webserver/www`
**Config**: `/customer/wifi/webserver/conf/route.txt`

Serves two functions:
1. **Static file server**: SD card browsing via HTML directory listings at `/`
2. **CGI gateway**: `/cgi-bin/Config.cgi` → calls `CGI_PROCESS.sh` → writes commands to `/tmp/cardv_fifo`

The directory listing uses `lighttpd`-style HTML output with `<table>` rows, sortable by name/date/size.

### Two API Surfaces

The camera exposes **two different HTTP APIs** on port 80:

1. **`/?custom=1&cmd=X`** — Novatek-compatible XML API (handled by `cardv` directly)
2. **`/cgi-bin/Config.cgi`** — CGI API (handled by GoAhead → `CGI_PROCESS.sh` → cardv FIFO)

The `?custom=1` API returns XML `<Function>` responses. The CGI API returns plain text or JSON-like responses. Both ultimately control `cardv` but through different code paths.

## Port 8192: MJPEG Stream Server

**Library**: `libsamJPGWeb.so` (CivetWeb embedded HTTP server)
**Loaded by**: `cardv` via `dlopen("libsamJPGWeb.so")` → `dlsym("module_samjpgweb_start")`
**Server ID**: `samMJPGServer/1.0`
**Content-Type**: `multipart/x-mixed-replace;boundary=arflebarfle`
**Frame Content-Type**: `image/jpeg`

### How It Works

1. `ap_delay.sh` sends `echo usrstream 0 > /tmp/cardv_fifo` after WiFi AP is ready
2. `cardv` starts the "user" type (7) JPEG encoders (Venc4/Ch5 for front, Venc3/Ch10 for rear)
3. The hardware scaler feeds 640x360 frames to the JPEG encoder at 2 Mbps
4. `cardv` calls `samJPGServer_writeFrame()` to push each encoded JPEG to connected HTTP clients
5. Clients receive a continuous MJPEG stream as multipart HTTP

### Key Functions (from string extraction)

```
module_samjpgweb_start     — Initialize and start the MJPEG server
samJPGServer_writeFrame    — Push a JPEG frame to all connected clients
startStreaming             — Begin frame delivery
stopStreaming              — Stop frame delivery
JPGSession_Init            — Initialize a client session
JPGSession_Deinit          — Tear down a client session
```

### Stream Characteristics

- **Resolution**: 640x360 (hardcoded in Scl4 scaler config)
- **Frame rate**: ~25fps (tied to sensor timing)
- **Bitrate**: 2 Mbps JPEG (from Venc4BitRate / Venc3BitRate)
- **Latency**: ~40ms (1 frame + network)
- **Boundary string**: `arflebarfle` (custom, hardcoded in library)

## Port 8081: GPS WebSocket Server

**Library**: Same `libsamJPGWeb.so`
**Loaded by**: `cardv` via `dlsym("module_samGPSServer_start")`
**Protocol**: WebSocket (RFC 6455)

Serves GPS NMEA data to connected WebSocket clients. Confirmed by log strings:
```
samGPSServer[%u]:module_samGPSServer_start 8081
samGPSServer[%u]:Websocket server running
```

Key function: `samGPSServerGetGPSPacket` — retrieves GPS data for delivery.

**This port does NOT serve video.** HTTP GET requests return 404 because it only speaks WebSocket.

## Port 554: RTSP Server (Disabled)

**Implementation**: live555 library, statically linked into `cardv`
**Started by**: `echo "rtsp 1" > /tmp/cardv_fifo` (called from `net_toggle.sh` when WiFi enables)

### live555 Architecture in cardv

From string analysis, the RTSP server has full H.264 and H.265 streaming capability:

```
live555::startLive555Server()
live555::stopLive555Server()
live555::createServerMediaSession(MI_VideoEncoder*, MI_AudioEncoder*, char*, int)
live555::fRtspServerPortNum        — Port number storage
live555_Task                        — Server thread
LiveJPEGVideoStreamSource          — JPEG stream source
H264VideoRTPSink                   — H.264 RTP packetizer
H265VideoRTPSink                   — H.265 RTP packetizer
LivePCMAAudioServerMediaSubsession — G.711 audio
RTSPServer::RTSPClientConnection   — Client handling
streamingOverTCPRecord             — TCP interleaved streaming
```

### Why RTSP Doesn't Work

1. **`net_toggle.sh` sends `rtsp 1`** when WiFi enables — the server starts
2. **But the encoder channels are commented out** in `default.ini` — no `VencType=3` (RTSP) or `VencType=1` (subrec) channels are active
3. Without an active encoder feeding frames, `createServerMediaSession()` has no video source
4. The server likely starts but has no media sessions to offer, resulting in empty or refused connections

### Enabling RTSP (Theoretical)

To enable RTSP, one would need to uncomment the subrec encoder channels in `default.ini`:

```ini
# Uncomment these for front camera H.264 sub-stream:
Venc3Chn = 3
Venc3Type = 1           # subrec (would need to change to 3 for rtsp type)
Venc3Codec = 0          # H.264
Venc3BitRate = 800000   # 800 Kbps
Venc3InBindMod = 34
Venc3InBindDev = 0
Venc3InBindChn = 0
Venc3InBindPort = 1     # Scl0/HWScl1 (640x360)
```

This would provide a 640x360 H.264 stream at 800 Kbps. Higher resolutions might be possible by changing the source scaler binding, but the WiFi bandwidth (~10 Mbps effective on 5GHz AP) constrains what's practical.

## Network Startup Sequence

```
Power on
  └─ demo.sh
       ├─ Load kernel modules
       ├─ Start cardv (reads default.ini, initializes pipeline)
       ├─ Mount /customer
       └─ rcInsDriver.sh
            └─ Load WiFi kernel module (bcmdhd.ko)

User enables WiFi (button press or menu)
  └─ net_toggle.sh
       ├─ echo "rtsp 1" > /tmp/cardv_fifo     ← RTSP server starts
       ├─ nvconf set Camera.Menu.WiFi ON
       └─ ap.sh start                          ← or sta.sh start
            └─ ap_delay.sh
                 ├─ Load WiFi firmware
                 ├─ ifconfig wlan0 up
                 ├─ Start hostapd
                 ├─ Start udhcpd
                 ├─ echo "usrstream 0" > /tmp/cardv_fifo  ← MJPEG encoders start
                 └─ run_goahead.sh              ← Web server starts (port 80)

MJPEG available at http://192.168.1.252:8192
GPS WebSocket available at ws://192.168.1.252:8081
Web API available at http://192.168.1.252/
```
