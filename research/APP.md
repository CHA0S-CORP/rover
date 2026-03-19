# Rove Android App Analysis

## App Identity

| Field | Value |
|-------|-------|
| Package | `com.rovedashcam` |
| APK size | 155 MB (base) + 255 MB (firmware split) |
| Min SDK | Android 7.0+ |
| Architecture | Multi-arch (arm64-v8a, armeabi-v7a) |
| Framework | Android Jetpack + Kotlin + Java |
| Decompiler | jadx |

## Supported Camera Models

The app supports 10+ camera models, each with its own fragment class for live video:

| Model | Class | IP | Stream Method | Port |
|-------|-------|----|---------------|------|
| R2-4K | Rove2LiveVideoFragment | 192.168.1.254 | WebView MJPEG `<img>` | 8192 |
| R2-4K-Pro | Rove2LiveVideoFragment | 192.168.1.250 | WebView MJPEG `<img>` | 8192 |
| R2-4K-8MP | Rove2LiveVideoFragment | 192.168.1.247 | WebView MJPEG `<img>` | 8192 |
| R2-4K-NTK | Rove2LiveVideoFragment | 192.168.1.251 | WebView MJPEG `<img>` | 8192 |
| **R2-4K-DUAL** | **RoveR24kDualLiveVideoFragment** | **192.168.1.252** | **WebView MJPEG `<img>`** | **8192** |
| R2-4K-DUAL-PRO | Rove2LiveVideoFragment | 192.168.1.253 | WebView MJPEG `<img>` | 8192 |
| R3 | Rove3LiveVideoFragment | 192.168.0.1 | GSYVideoPlayer (IJK) | 554 (RTSP) |
| R3-Sigma | RoveR3SigmaLiveVideoFragment | 192.168.1.248 | WebView MJPEG `<img>` | 8192 |
| R3-NTK | Rove3NtkLiveVideoFragment | 192.168.1.249 | WebView MJPEG `<img>` | 8192 |
| R4 | RoveR4ChannelLiveVideoFragment | 10.179.121.24 | WebView loadUrl | 8888 |

## R2-4K-DUAL Streaming Implementation

**Source**: `com.rovedashcam.newmodeule.rover24kdual.livevideo.view.RoveR24kDualLiveVideoFragment`

### Stream URL (Hardcoded)

```java
// Line 95
private String mFilePath = "http://192.168.1.252:8192";
```

### Connection Sequence

1. Check camera connected: `GET /?custom=1&cmd=2016`
2. Get settings: `GET /?custom=1&cmd=3014`
3. Set video mode: `GET /?custom=1&cmd=3001&par=1`
4. Start recording: `GET /?custom=1&cmd=2001&par=1`
5. Create WebView with MJPEG `<img>` tag

### HTML Template (Line 511)

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

The `object-fit: contain` CSS makes the 640x360 stream fill the phone screen while maintaining aspect ratio. On phone displays (typically 1080x2400), this results in smooth CSS upscaling that masks the low native resolution.

### No Quality Negotiation

The app does NOT:
- Send any resolution/bitrate commands before streaming
- Use cmd=2010 (set liveview size)
- Use cmd=2014 (set liveview bitrate)
- Access port 8081 for video
- Use any native video player (ExoPlayer, ijkplayer) for R2 models
- Offer quality settings for the live stream

## R3 Streaming (For Comparison)

The R3 model uses actual RTSP streaming with the ijkplayer native library:

```java
// Rove3LiveVideoFragment.java line 84
private String mFilePath = "rtsp://192.168.0.1:554/livestream/1";

// Line 530-593: GSYVideoPlayer setup
StandardGSYVideoPlayer player = new StandardGSYVideoPlayer(context);
player.setUp(mFilePath, true, "Live RTSP Stream");
player.startPlayLogic();
```

This delivers H.264 video at native resolution via RTP, which is why the R3 has noticeably better live preview quality.

## Native Libraries

| Library | Used By | Purpose |
|---------|---------|---------|
| `libijkffmpeg.so` | R3 only | FFmpeg for RTSP decoding |
| `libijkplayer.so` | R3 only | IJKPlayer media engine |
| `libijksdl.so` | R3 only | SDL rendering for video |
| `libjingle_peerconnection_so.so` | R4 / TestVideo | WebRTC peer connection |
| `libsammp4v2.so` | File playback | MP4 parsing |
| `libmp4v2.so` | File playback | MP4 parsing |

## Firmware Distribution

The firmware split APK contains firmware tarballs in `assets/`:
- `R2D.tar` — R2-4K-DUAL firmware (29 MB)
- Other models have their own tarballs

The app handles OTA firmware updates by extracting the tarball to the SD card and triggering a reboot. The camera's bootloader detects the firmware file and flashes it.

## API Client

The app uses Retrofit (OkHttp) for the `/?custom=1` XML API:
- `R2RetrofitService.java` — Defines all API endpoints
- Uses standard GET requests
- Parses XML responses
- Short timeouts for camera responsiveness
