# Rove R2-4K-DUAL: Complete API Controls Reference

Quick-reference for every controllable parameter on the camera. All commands use the CGI API unless marked as Novatek XML.

**Base URL**: `http://192.168.1.252`
**CGI endpoint**: `/cgi-bin/Config.cgi`
**Novatek endpoint**: `/?custom=1`

---

## Recording

| Action | CGI URL | FIFO Command |
|--------|---------|--------------|
| Toggle recording | `set property=Video&value=record` | `rec 1` / `rec 0` |
| Force start | `set property=Video&value=recordon` | `rec 1` |
| Force stop | `set property=Video&value=recordoff` | `rec 0` |
| Take photo | `set property=Video&value=capture` | `capture` |

**Novatek XML**:
- Start: `/?custom=1&cmd=2001&str=1`
- Stop: `/?custom=1&cmd=2001&str=0`
- Photo: `/?custom=1&cmd=1001`

---

## Video Resolution

```
set property=Videores&value=<VALUE>
```

| Value | Resolution | FPS | FIFO |
|-------|-----------|-----|------|
| `2160P25fps` | 3840x2160 | 25 | `vidres 3840 2160` |
| `1440P30fps` | 2560x1440 | 30 | `vidres 2560 1440` |
| `1080P30fps` | 1920x1080 | 30 | `vidres 1920 1080` |
| `1080P27.5fpsHDR` | 1920x1080 | 27.5 | `vidres 1920 1080` |
| `720P30fps` | 1280x720 | 30 | `vidres 1280 720` |
| `720P27.5fpsHDR` | 1280x720 | 27.5 | `vidres 1280 720` |
| `720P60fps` | 1280x720 | 60 | `vidres 1280 720` |
| `VGA` | 640x480 | 30 | `vidres 640 480` |

**Novatek XML**: `/?custom=1&cmd=3001&par=0` (set video mode first)

---

## Photo Resolution

```
set property=Imageres&value=<VALUE>
```

| Value | Resolution | FIFO |
|-------|-----------|------|
| `8M` | 3840x2160 | `capres 3840 2160` |
| `3M` | 2304x1296 | `capres 2304 1296` |
| `2M` | 1920x1080 | `capres 1920 1080` |
| `1.2M` | 1280x960 | `capres 1280 960` |
| `VGA` | 640x480 | `capres 640 480` |

---

## Streaming Control

| Action | CGI URL | FIFO |
|--------|---------|------|
| Start MJPEG stream | `set property=streamer&value=start` | `usrstream 0` |
| Stop MJPEG stream | `set property=streamer&value=stop` | — |
| Force I-frame | `set property=forceiframe` | `forceiframe` |
| Set bitrate (bps) | `set property=setbitrate&value=1000000` | `bitrate <ch> <value>` |
| Set frame rate | `set property=setframerate&value=30` | `setFrameRate 30` |
| Set GOP size | `set property=setvideogop&value=30` | — |
| Get streamer status | `get property=streamerstatus` | — |
| Enable RTSP server | — | `rtsp 1` |
| Disable RTSP server | — | `rtsp 0` |

**Stream URLs**:
- MJPEG: `http://192.168.1.252:8192`
- GPS WebSocket: `ws://192.168.1.252:8081`
- RTSP (if enabled): `rtsp://192.168.1.252:554/`

---

## Camera Source Selection

```
set property=Camera.Preview.Source.1.Camid&value=front
set property=Camera.Preview.Source.1.Camid&value=rear
```

RTSP audio+video mode:
```
set property=Camera.Preview.RTSP.av&value=4
```

---

## Image Tuning — Brightness

```
set property=Brightness&value=<0-255>
get property=Brightness
```

| Value | Effect | FIFO |
|-------|--------|------|
| 0 | Minimum | `bri 0` |
| 128 | Default | `bri 50` |
| 255 | Maximum | `bri 100` |

Note: CGI accepts 0-255, FIFO accepts 0-100. CGI_PROCESS.sh clamps to 0-100.

---

## Image Tuning — Contrast

```
set property=Contrast&value=<0-255>
get property=Contrast
```

| Value | Effect | FIFO |
|-------|--------|------|
| 0 | Minimum | `con 0` |
| 128 | Default | `con 50` |
| 255 | Maximum | `con 100` |

---

## Image Tuning — Saturation

```
set property=Saturation&value=<0-255>
get property=Saturation
```

| Value | Effect | FIFO |
|-------|--------|------|
| 0 | Minimum | `sat 0` |
| 128 | Default | `sat 50` |
| 255 | Maximum | `sat 100` |

Note: CGI_PROCESS.sh clamps to 0-127 before converting to 0-100.

---

## Image Tuning — Sharpness

```
set property=Sharpness&value=<0-255>
get property=Sharpness
```

| Value | Effect | FIFO |
|-------|--------|------|
| 0 | Minimum | `sha 0` |
| 128 | Default | `sha 50` |
| 255 | Maximum | `sha 100` |

Note: CGI_PROCESS.sh clamps to 0-1023 before converting to 0-100.

---

## Image Tuning — Hue

```
set property=Hue&value=<-180 to 180>
get property=Hue
```

| Value | Effect | FIFO |
|-------|--------|------|
| -180 | Full shift left | `hue -180` |
| 0 | Default (no shift) | `hue 0` |
| 180 | Full shift right | `hue 180` |

---

## Image Tuning — Gamma

```
set property=Gamma&value=<0-255>
get property=Gamma
```

| Value | Effect | FIFO |
|-------|--------|------|
| 0 | Dark | `gamma 0` |
| 128 | Default | `gamma 0` (128-128=0) |
| 255 | Bright | `gamma 100` |

Note: CGI_PROCESS.sh subtracts 128, then clamps to 0-100.

---

## Image Tuning — Exposure (EV)

```
set property=EV&value=<VALUE>
get property=EV
```

| CGI Value | EV Stops | FIFO |
|-----------|----------|------|
| `EVN200` | -2.0 | `ev -6` |
| `EVN167` | -1.67 | `ev -5` |
| `EVN133` | -1.33 | `ev -4` |
| `EVN100` | -1.0 | `ev -3` |
| `EVN67` | -0.67 | `ev -2` |
| `EVN33` | -0.33 | `ev -1` |
| `EV0` | 0 | `ev 0` |
| `EVP33` | +0.33 | `ev 1` |
| `EVP67` | +0.67 | `ev 2` |
| `EVP100` | +1.0 | `ev 3` |
| `EVP133` | +1.33 | `ev 4` |
| `EVP167` | +1.67 | `ev 5` |
| `EVP200` | +2.0 | `ev 6` |

Also accepts numeric: `set property=Exposure&value=<-5 to 5>`

---

## Image Tuning — Auto Exposure

```
set property=AE&value=<0|1>
get property=AE
```

| Value | Effect | FIFO |
|-------|--------|------|
| 0 | AE off (manual) | `3a 0` |
| 1 | AE on (auto) | `3a 1` |

---

## Image Tuning — Backlight Compensation

```
set property=Backlight&value=<0|1>
get property=Backlight
```

---

## ISO

```
set property=ISO&value=<VALUE>
```

| Value | FIFO |
|-------|------|
| `ISO_AUTO` | `iso 0` |
| `ISO_100` | `iso 1` |
| `ISO_200` | `iso 2` |
| `ISO_400` | `iso 3` |
| `ISO_800` | `iso 4` |
| `ISO_1600` | `iso 5` |
| `ISO_3200` | `iso 6` |

---

## White Balance

```
set property=AWB&value=<VALUE>
get property=AWB
```

| Value | FIFO |
|-------|------|
| `Auto` | `wb 0` |
| `Daylight` | `wb 1` |
| `Cloudy` | `wb 2` |
| `Fluorescent1` / `Fluorescent2` / `Fluorescent3` | `wb 3` |
| `Incandescent` | `wb 4` |

---

## Shutter Speed

```
set property=Shutter&value=<1-14>
get property=Shutter
```

FIFO formula: `shutter = 100 + (value - 1) * 146`

| Value | Computed FIFO |
|-------|---------------|
| 1 | `shutter 100` |
| 2 | `shutter 246` |
| 7 | `shutter 976` |
| 14 | `shutter 1998` |

---

## Image Effects

```
set property=Effect&value=<VALUE>
```

| Value | FIFO |
|-------|------|
| `noraml` (sic) | `effect 0` |
| `sepia` | `effect 1` |
| `blackwhite` | `effect 2` |
| `emboss` / `negative` / `sketch` | `effect 3` |
| `oli` | `effect 4` |
| `crayon` | `effect 5` |
| `beauty` | `effect 6` |

---

## Anti-Flicker

```
set property=Flicker&value=<VALUE>
get property=Flicker
```

| Value | FIFO |
|-------|------|
| `50HZ` | `flicker 50` |
| `60HZ` | `flicker 60` |

---

## Night Mode

```
set property=NightMode&value=<ON|OFF>
get property=NightMode
```

| Value | FIFO |
|-------|------|
| `OFF` | `night 0` |
| `ON` | `night 1` |

---

## HDR / WDR

```
set property=HDR&value=<ON|OFF>
get property=HDR
```

| Value | FIFO |
|-------|------|
| `OFF` | `hdr 0` |
| `ON` | `hdr 1` |

---

## Wind Noise Reduction (WNR)

```
set property=WNR&value=<ON|OFF>
get property=WNR
```

| Value | FIFO |
|-------|------|
| `OFF` | `wnr 0` |
| `ON` | `wnr 1` |

---

## Loop Recording Time

```
set property=VideoClipTime&value=<VALUE>
```
Also: `set property=LoopingVideo&value=<VALUE>`

| Value | Minutes | FIFO |
|-------|---------|------|
| `OFF` | continuous | `loop 1` |
| `1MIN` | 1 | `loop 1` |
| `2MIN` | 2 | `loop 2` |
| `3MIN` | 3 | `loop 3` |
| `5MIN` | 5 | `loop 5` |
| `10MIN` | 10 | `loop 10` |
| `15MIN` | 15 | `loop 15` |

---

## Timelapse

```
set property=Timelapse&value=<VALUE>
get property=Timelapse
```

| Value | Interval | FIFO |
|-------|----------|------|
| `OFF` | disabled | `timelapse 0` |
| `1SEC` | 1 second | `timelapse 1` |
| `5SEC` | 5 seconds | `timelapse 5` |
| `10SEC` | 10 seconds | `timelapse 10` |
| `30SEC` | 30 seconds | `timelapse 30` |
| `60SEC` | 60 seconds | `timelapse 60` |

---

## Slow Motion

```
set property=SlowMotion&value=<VALUE>
get property=SlowMotion
```

| Value | Speed | FIFO |
|-------|-------|------|
| `X1` | Normal | `slowmotion 0` |
| `X2` | 2x slow | `slowmotion 1` |
| `X4` | 4x slow | `slowmotion 2` |
| `X8` | 8x slow | `slowmotion 3` |

---

## G-Sensor Sensitivity

```
set property=GSensor&value=<VALUE>
get property=GSensor
```

| Value | Level | FIFO |
|-------|-------|------|
| `OFF` | Disabled | `gsensor 0` |
| `LEVEL0` | Ultra-low | `gsensor 1` |
| `LEVEL1` | Low | `gsensor 2` |
| `LEVEL2` | Medium | `gsensor 3` |
| `LEVEL3` | High | `gsensor 4` |
| `LEVEL4` | Ultra-high | `gsensor 5` |

---

## Parking Mode

```
set property=ParkingMonitor&value=<DISABLE|ENABLE>
```

| Value | FIFO |
|-------|------|
| `DISABLE` | `park 0` |
| `ENABLE` | `park 1` |

Also: `set property=PowerOnGSensor&value=<OFF|LEVEL0|LEVEL1|LEVEL2>` → `park 0-3`

---

## Motion Detection

```
set property=MotionDetect&value=<VALUE>
get property=MotionDetect
```

| Value | FIFO |
|-------|------|
| `OFF` | `mdt 0` |
| `LOW` | `mdt 1` |
| `MID` | `mdt 2` |
| `HIGH` | `mdt 3` |

---

## Motion Detection Video Duration

```
set property=MotionVideoTime&value=<VALUE>
get property=MotionVideoTime
```

| Value | Seconds | FIFO |
|-------|---------|------|
| `5` | 5 | `vmd 5` |
| `10` | 10 | `vmd 10` |
| `30` | 30 | `vmd 30` |
| `60` | 60 | `vmd 60` |

---

## Audio Recording

```
set property=SoundRecord&value=<ON|OFF>
get property=SoundRecord
```
Also: `set property=MovieAudio&value=<ON|OFF>`

| Value | FIFO |
|-------|------|
| `OFF` | `audiorec 1` |
| `ON` | `audiorec 0` |

Note: Values are inverted (0=on, 1=off).

---

## Microphone Sensitivity

```
set property=MicSensitivity&value=<VALUE>
get property=MicSensitivity
```

| Value | FIFO |
|-------|------|
| `LOW` | `micsen 0` |
| `STANDARD` | `micsen 1` |

---

## Voice Guidance / Beep Sounds

```
set property=VoiceSwitch&value=<ON|OFF>
set property=Beep&value=<ON|OFF>
get property=Beep
```

| Property | Value | FIFO |
|----------|-------|------|
| `VoiceSwitch` | `OFF` / `ON` | `voice 0` / `voice 1` |
| `Beep` | `OFF` / `ON` | `beep 1` / `beep 0` |

Note: Beep values are inverted.

---

## Playback Volume

```
set property=PlaybackVolume&value=<00-10>
get property=PlaybackVolume
```

FIFO: `pbvolume <0-10>`

---

## Video Quality

```
set property=VideoQuality&value=<VALUE>
get property=VideoQuality
```

| Value | FIFO |
|-------|------|
| `SUPER_FINE` | `quality 0` |
| `FINE` | `quality 1` |

---

## Video Codec

```
set property=SmEncodeFormat&value=<VALUE>
```

| Value | FIFO |
|-------|------|
| `H264` | `codec 0 0` + `codec 6 0` |
| `H265` | `codec 0 1` + `codec 6 1` |

Sets codec for both front (ch 0) and rear (ch 6) cameras simultaneously.

---

## Auto Record

```
set property=AutoRec&value=<ON|OFF>
get property=AutoRec
```

| Value | FIFO |
|-------|------|
| `OFF` | `autorec 1` |
| `ON` | `autorec 0` |

Note: Values are inverted.

---

## Pre-Record Buffer

```
set property=VideoPreRecord&value=<ON|OFF>
get property=VideoPreRecord
```

| Value | FIFO |
|-------|------|
| `OFF` | `prerec 1` |
| `ON` | `prerec 0` |

Note: Values are inverted.

---

## Video Auto-Off Timer

```
set property=VideoOffTime&value=<VALUE>
get property=VideoOffTime
```

| Value | Seconds | FIFO |
|-------|---------|------|
| `0MIN` | 0 (never) | `videoofftime 0` |
| `5SEC` | 5 | `videoofftime 5` |
| `10SEC` | 10 | `videoofftime 10` |
| `15SEC` | 15 | `videoofftime 15` |
| `30SEC` | 30 | `videoofftime 30` |
| `1MIN` | 60 | `videoofftime 60` |
| `2MIN` | 120 | `videoofftime 120` |
| `3MIN` | 180 | `videoofftime 180` |
| `5MIN` | 300 | `videoofftime 300` |
| `10MIN` | 600 | `videoofftime 600` |
| `15MIN` | 900 | `videoofftime 900` |
| `30MIN` | 1800 | `videoofftime 1800` |
| `60MIN` | 3600 | `videoofftime 3600` |

---

## Burst Shot

```
set property=StillBurstShot&value=<VALUE>
get property=StillBurstShot
```

| Value | FIFO |
|-------|------|
| `OFF` | `burstshot 0` |
| `LO` | `burstshot 1` |
| `MID` | `burstshot 2` |
| `HI` | `burstshot 3` |

---

## Date/Logo Stamp

```
set property=DateLogoStamp&value=<VALUE>
get property=DateLogoStamp
```

| Value | FIFO |
|-------|------|
| `DATELOGO` | `datelogoStamp 0` |
| `DATE` | `datelogoStamp 1` |
| `LOGO` | `datelogoStamp 2` |
| `OFF` | `datelogoStamp 3` |

---

## Date/Time Format

```
set property=DateTimeFormat&value=<VALUE>
get property=DateTimeFormat
```

| Value | FIFO |
|-------|------|
| `NONE` | `timeformat 0` |
| `YMD` | `timeformat 1` |
| `MDY` | `timeformat 2` |
| `DMY` | `timeformat 3` |

---

## GPS Stamp

```
set property=GpsStamp&value=<ON|OFF>
get property=GpsStamp
```

| Value | FIFO |
|-------|------|
| `ON` | `gpsstamp 0` |
| `OFF` | `gpsstamp 1` |

Note: Values are inverted.

---

## Speed Stamp

```
set property=SpeedStamp&value=<ON|OFF>
```

| Value | FIFO |
|-------|------|
| `ON` | `speedstamp 0` |
| `OFF` | `speedstamp 1` |

---

## Speed Unit

```
set property=SpeedUint&value=<VALUE>
```

| Value | FIFO |
|-------|------|
| `km/h` | `speeduint 0` |
| `mph` | `speeduint 1` |

---

## Speed Limit Alert

```
set property=SpeedLimitAlert&value=<VALUE>
```

| Value | km/h | FIFO |
|-------|------|------|
| `OFF` | — | `SpeedLimitAlert 0` |
| `30mph` / `50km/h` | 50 | `SpeedLimitAlert 50` |
| `40mph` / `70km/h` | 70 | `SpeedLimitAlert 70` |
| `55mph` / `90km/h` | 90 | `SpeedLimitAlert 90` |
| `65mph` / `110km/h` | 110 | `SpeedLimitAlert 110` |
| `75mph` / `120km/h` | 120 | `SpeedLimitAlert 120` |
| `85mph` / `140km/h` | 140 | `SpeedLimitAlert 140` |
| `100mph` / `160km/h` | 160 | `SpeedLimitAlert 160` |
| `123mph` / `200km/h` | 200 | `SpeedLimitAlert 200` |

---

## Speed Camera Alert

```
set property=SpeedCamAlert&value=<ON|OFF>
```

| Value | FIFO |
|-------|------|
| `OFF` | `speedCamAlert 0` |
| `ON` | `speedCamAlert 1` |

---

## ADAS (Advanced Driver Assistance)

```
set property=LDWS&value=<ON|OFF>       # Lane Departure Warning
set property=FCWS&value=<ON|OFF>       # Forward Collision Warning
set property=SAG&value=<ON|OFF>        # Stop-and-Go
```

| Property | ON FIFO | OFF FIFO |
|----------|---------|----------|
| LDWS | `adas ldws 1` | `adas ldws 0` |
| FCWS | `adas fcws 1` | `adas fcws 0` |
| SAG | `adas sag 1` | `adas sag 0` |

---

## LCD Display

```
set property=LCDBrightness&value=<0-100>
set property=LcdPowerSave&value=<VALUE>
```

LCD Brightness FIFO: `lcdbri <0-100>`

| Power Save Value | Timeout | FIFO (stored via nvconf only) |
|-----------------|---------|------|
| `OFF` | Never | — |
| `10SEC` | 10s | — |
| `30SEC` | 30s | — |
| `1MIN` | 60s | — |
| `3MIN` | 180s | — |

---

## Display Control (FIFO-only)

| FIFO Command | Description |
|-------------|-------------|
| `disp switch <value>` | Switch PIP display mode |
| `disp pippos <value>` | Set PIP overlay position |
| `sclrotate 3 0 <value>` | Rotate scaler 3 ch 0 |
| `sclrotate 3 1 <value>` | Rotate scaler 3 ch 1 |
| `lcdbri <0-100>` | LCD brightness |
| `lcdcon <value>` | LCD contrast |
| `lcdhue <value>` | LCD hue |
| `lcdsat <value>` | LCD saturation |

---

## Video Flip / Rotate

```
set property=smRotateDisplay&value=<VALUE>
```

| Value | Front Rotate | Front Flip | Rear Rotate | FIFO Sequence |
|-------|-------------|------------|-------------|---------------|
| `Off` | No | No | No | `RearRotate 0` → `sclrotate 3 0 1` → `sclrotate 3 1 1` → `flip 0` → `disp pippos 0` |
| `On` | Yes | Yes | No | `RearRotate 0` → `sclrotate 3 0 3` → `sclrotate 3 1 3` → `flip 1` → `disp pippos 1` |
| `RearOn` | No | No | Yes | `RearRotate 1` → ... → `flip 0` |
| `AllOn` | Yes | Yes | Yes | `RearRotate 1` → ... → `flip 1` |

---

## Rear Camera Mirror

```
set property=SmMirror&value=<Off|On>
```

FIFO: `RearMirror 0` / `RearMirror 1`

---

## Auto Power Off

```
set property=AutoPowerOff&value=<VALUE>
get property=AutoPowerOff
```

| Value | Timeout |
|-------|---------|
| `NEVER` | Never |
| `15SEC` | 15s |
| `30SEC` | 30s |
| `1MIN` | 60s |
| `2MIN` | 120s |
| `3MIN` | 180s |
| `5MIN` | 300s |

Note: Stored via nvconf only, no FIFO command.

---

## USB Function

```
set property=UsbFunction&value=<VALUE>
get property=UsbFunction
```

| Value | Mode |
|-------|------|
| `MSDC` | Mass storage (SD card reader) |
| `PCAM` | USB webcam (UVC) |

FIFO: `uvc` command handles UVC mode toggle.

---

## Language

```
set property=Language&value=<VALUE>
get property=Language
```

Supported: `English`, `Spanish`, `Portuguese`, `Russian`, `Simplified Chinese`, `Traditional Chinese`, `German`, `Italian`, `Latvian`, `Polish`, `Romanian`, `Slovak`, `UKRomanian`, `French`, `Japanese`, `Korean`, `Czech`

Note: Stored via nvconf only, no FIFO command.

---

## Time Settings

```
set property=TimeSettings&value=<ENCODED_DATETIME>
```

Format: `YYYY%24MM%24DD%24HH%24MM%24SS%24`
Example: `2026%2403%2419%2413%2448%2430%24` = 2026-03-19 13:48:30

The `%24` is URL-encoded `$` used as a delimiter.

---

## Time Zone

```
set property=TimeZone&value=<VALUE>
get property=TimeZone
```

Format: `GMT_M_<hours>` (negative) or `GMT_P_<hours>` (positive) or `GMT00`

Examples: `GMT_M_8` = UTC-8, `GMT_P_5_30` = UTC+5:30, `GMT_P_9` = UTC+9

FIFO: `timezone GMT-08:00`

Full range: GMT-12 through GMT+14, including half-hour offsets (3:30, 4:30, 5:30, 5:45, 6:30, 9:30).

---

## Time Sync

```
set property=SyncTime&value=<ON|OFF>
```

FIFO: `synctime 0` / `synctime 1`

---

## Record Stamp

```
set property=RecStamp&value=<ON|OFF>
get property=RecStamp
```

| Value | FIFO |
|-------|------|
| `OFF` | `recstamp 0` |
| `ON` | `recstamp 1` |

---

## Network Settings

| Action | CGI URL |
|--------|---------|
| Get all network settings | `get property=Net*` |
| Get WiFi SSID | `get property=Net.WIFI_AP.SSID` |
| Get WiFi password | `get property=Net.WIFI_AP.CryptoKey` |
| Set WiFi SSID | `set property=Net.WIFI_AP.SSID&value=<SSID>` |
| Set WiFi password | `set property=Net.WIFI_AP.CryptoKey&value=<PASSWORD>` |
| Get station SSID | `get property=Net.WIFI_STA.AP.2.SSID` |
| Set station SSID | `set property=Net.WIFI_STA.AP.2.SSID&value=<SSID>` |
| Set station password | `set property=Net.WIFI_STA.AP.2.CryptoKey&value=<PASSWORD>` |
| Enable station mode | `set property=Net.WIFI_STA.AP.Switch&value=ENABLE` |
| Restart network | `set property=Net&value=reset` |

---

## Device Info (Read-only)

```
get property=devinfo.fwver          # Firmware version
get property=devinfo.macaddr        # MAC address
get property=devinfo.linuxkernelver # Linux kernel version
get property=FwVer                  # Firmware version (alternate)
```

---

## SD Card

| Action | CGI URL | Novatek |
|--------|---------|---------|
| SD card status | — | `/?custom=1&cmd=3024` → 0=removed, 1=ready, 2=present |
| Free space | — | `/?custom=1&cmd=3017` |
| File count | — | `/?custom=1&cmd=3015` |
| SD card info | `get property=Camera.Menu.CardInfo.*` | — |
| Format SD card | `set property=SD0` | — |

SD card info returns: `LifeTimeTotal`, `RemainLifeTime`, `RemainWrGBNum`, `SizeOfDevSMART`

---

## File Operations

**List files (CGI)**:
```
dir property=Video&format=all&count=16&from=0
dir property=Photo&format=all&count=16&from=0
```

**List files (HTTP directory browsing)**:
```
GET http://192.168.1.252/Video/Front/
GET http://192.168.1.252/Video/Rear/
GET http://192.168.1.252/Photo/Front/
GET http://192.168.1.252/Photo/Rear/
GET http://192.168.1.252/Protect/
```

**Download file**:
```
GET http://192.168.1.252/Video/Front/REC20260315-115649-5058.mp4
```

**Delete file (CGI)**: Use `$` as path separator:
```
del property=$mnt$sdcard$Video$Front$REC20260315-115649-5058.mp4
```

**Delete file (Novatek XML)**:
```
/?custom=1&cmd=4003&str=/Video/Front/REC20260315-115649-5058.mp4
```

---

## System Commands

| Action | CGI URL | FIFO |
|--------|---------|------|
| Factory reset | `set property=reset_to_default&value=1` | `reset` |
| Reboot (WiFi restart) | `set property=reboot` | — |
| Full system reboot | `set property=RebootSystem` | `reboot` |
| Quit cardv | — | `quit` |
| Dump internals | — | `dumpimpl` |
| Dump internals v2 | — | `dumpimpl2` |

---

## Camera Status (Novatek XML, Read-only)

| Cmd | Description | Response |
|-----|-------------|----------|
| `/?custom=1&cmd=2016` | Recording time (seconds) | `<Parameters>seconds</Parameters>` |
| `/?custom=1&cmd=3012` | Firmware version | `<Parameters>0</Parameters>` (unhelpful) |
| `/?custom=1&cmd=3014` | Config string | `<String>...</String>` |
| `/?custom=1&cmd=3015` | File count | `<Parameters>count</Parameters>` |
| `/?custom=1&cmd=3016` | Heartbeat/ping | `<Status>-256</Status>` (still means alive) |
| `/?custom=1&cmd=3017` | Free space | `<Parameters>code</Parameters>` |
| `/?custom=1&cmd=3019` | Battery | `<Status>0</Status>` (no level value) |
| `/?custom=1&cmd=3024` | SD card | `<Parameters>0/1/2</Parameters>` |

---

## Camera Mode (Novatek XML)

```
/?custom=1&cmd=3001&par=<MODE>
```

| Mode | Description |
|------|-------------|
| 0 | Video mode |
| 1 | Photo mode |
| 2 | Playback mode |

---

## MJPEG Status

```
get property=Camera.Preview.MJPEG.status.*
```

Returns:
```
Camera.Preview.MJPEG.status.mode=Videomode
Camera.Preview.MJPEG.status.record=Recording|Standby
```

---

## Settings Enter/Exit (for app settings screens)

```
set property=Setting&value=enter    # Stop recording, enter settings
set property=Setting&value=exit     # Resume recording, exit settings
```
