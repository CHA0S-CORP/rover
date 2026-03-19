# HTTP API Reference

The camera exposes two API surfaces on port 80.

## API Surface 1: Novatek-Compatible XML API

**Format**: `http://192.168.1.252/?custom=1&cmd=<CMD>&par=<VALUE>&str=<STRING>`
**Response**: XML `<Function>` elements
**Handler**: `cardv` binary directly (not CGI)

### Response Format

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<Function>
<Cmd>3016</Cmd>
<Status>0</Status>
<Parameters>VALUE</Parameters>
</Function>
```

**Note**: This camera uses `<Parameters>` instead of `<Value>` (standard Novatek uses `<Value>`). Status `-256` means "command not supported."

### Supported Commands

| Cmd | Parameters | Description | Response |
|-----|-----------|-------------|----------|
| 1001 | — | Take photo | Status 0 on success |
| 2001 | str=1/0 | Start/stop recording | Parameters=1 on success |
| 2016 | — | Get recording time (seconds) | Parameters=seconds |
| 3001 | par=0/1/2 | Set mode (video/photo/playback) | Status 0 |
| 3012 | — | Get firmware version | Parameters=0 (unhelpful) |
| 3014 | — | Get config | String (often whitespace) |
| 3015 | — | Get file count | Parameters=count (NOT file list) |
| 3016 | — | Heartbeat/ping | Status -256 (!) |
| 3017 | — | Get free space | Parameters=code |
| 3019 | — | Get battery status | Status 0 (no value) |
| 3024 | — | SD card status | Parameters: 0=removed, 1=ready, 2=present |
| 4003 | str=path | Delete file | Status 0 |

### Differences from Standard Novatek

| Feature | Standard Novatek | This Camera |
|---------|-----------------|-------------|
| Value field | `<Value>` | `<Parameters>` |
| Heartbeat | Status 0 | Status -256 |
| File list (3015) | Full XML file listing | Just a count |
| Battery (3019) | Numeric level 0-5 | No value, just Status |
| Recording start | `cmd=2001&par=1` | `cmd=2001&str=1` |
| Liveview (2015) | Supported | Status -256 (not supported) |
| List commands (3002) | Command list | Status -256 |

## API Surface 2: CGI API

**Format**: `http://192.168.1.252/cgi-bin/Config.cgi?action=<ACTION>&property=<PROP>&value=<VAL>`
**Handler**: GoAhead → `CGI_PROCESS.sh` → `/tmp/cardv_fifo`

### Actions

| Action | Description |
|--------|-------------|
| `set` | Set a property value |
| `get` | Get a property value |
| `dir` | List directory contents |
| `del` | Delete a file |

### Streaming Control

```
# Start/stop the MJPEG user-stream encoders
set property=streamer&value=start
set property=streamer&value=stop

# Force an I-frame in the video encoder
set property=forceiframe

# Change encoder bitrate (bits per second)
set property=setbitrate&value=1000000

# Change frame rate
set property=setframerate&value=30

# Change GOP size
set property=setvideogop&value=30
```

### Recording

```
# Toggle recording
set property=Video&value=record        # toggle
set property=Video&value=recordon      # force start
set property=Video&value=recordoff     # force stop

# Take photo
set property=Video&value=capture
```

### Video Resolution

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

### Camera Settings

```
# Get all camera settings
get property=Camera.Menu.*

# Get all preview/streaming settings
get property=Camera.Preview.*

# Get streamer status
get property=streamerstatus

# Individual settings
set property=Camera.Menu.AWB&value=AUTO
set property=Camera.Menu.EV&value=EV0
set property=Camera.Menu.Flicker&value=50Hz
set property=Camera.Menu.MTD&value=OFF         # Motion detection
set property=Camera.Menu.VideoRes&value=1080P30

# Image tuning
set property=Brightness&value=128              # 0-255
set property=Contrast&value=128                # 0-255
set property=Saturation&value=128              # 0-255
set property=Sharpness&value=128               # 0-255
set property=Hue&value=0                       # -180 to 180
set property=Gamma&value=128                   # 0-255
set property=Exposure&value=0                  # -5 to 5
set property=AE&value=1                        # Auto exposure on/off
```

### Streaming Source Selection

```
# Select front or rear camera for preview
set property=Camera.Preview.Source.1.Camid&value=front
set property=Camera.Preview.Source.1.Camid&value=rear

# RTSP configuration (value 4 = audio+video)
set property=Camera.Preview.RTSP.av&value=4
```

### Network Settings

```
get property=Net*
set property=Net.WIFI_AP.SSID&value=MyDashcam
set property=Net.WIFI_AP.CryptoKey&value=newpassword
```

### Device Info

```
get property=devinfo.fwver
get property=devinfo.macaddr
get property=devinfo.linuxkernelver
```

### File Operations

```
# List files in a directory
dir property=Video&format=all&count=16&from=0
dir property=Photo&format=all&count=16&from=0

# Delete a file ($ replaces / in paths)
del property=$mnt$sdcard$Video$Front$REC20260315-115649-5058.mp4
```

### System Commands

```
set property=reset_to_default&value=1    # Factory reset
set property=reboot                       # Reboot camera
set property=TimeSettings&value=2026%2403%2419%2413%2448%2430%24  # Set time
```

## File Browser (HTML)

The GoAhead server serves directory listings at `http://192.168.1.252/` with standard HTML `<table>` format. This is separate from the CGI file listing API.

### Directory Structure

```
/
├── Video/
│   ├── Front/    — Front camera recordings (MP4, H.265)
│   └── Rear/     — Rear camera recordings (MP4, H.265)
├── Photo/
│   ├── Front/    — Front camera photos (JPEG)
│   └── Rear/     — Rear camera photos (JPEG)
├── Protect/      — G-sensor triggered emergency recordings
└── System Volume Information/
```

### File Naming Convention

Recordings: `REC<YYYYMMDD>-<HHMMSS>-<SEQNUM>.mp4`
Example: `REC20260315-115649-5058.mp4`

Files are typically 260MB each (60-second segments at 30 Mbps H.265).
