# `cardv` Binary: Advanced Analysis

Deep analysis of the main camera application using radare2 disassembly, symbol extraction, and cross-reference analysis. The binary is a 629 KB stripped ARM ELF (Thumb-2, GCC 9.1.0, C++).

## Binary Overview

| Property | Value |
|----------|-------|
| Size | 644,140 bytes |
| Arch | ARM 32-bit, EABI5, Thumb-2 |
| Compiler | GCC 9.1.0 |
| Linking | Dynamic (42 shared libraries) |
| Symbols | 3,173 total, 2,597 functions |
| Code size | 329 KB (.text) |
| BSS | 113 KB (uninitialized data) |
| Security | NX enabled, no canary, partial RELRO |

### Key Linked Libraries

| Library | Purpose |
|---------|---------|
| `libmi_venc.so` | SigmaStar video encoder API |
| `libmi_isp.so` | Image signal processor |
| `libmi_scl.so` | Hardware scaler |
| `libmi_vif.so` | Video input frontend |
| `libmi_ai.so` / `libmi_ao.so` | Audio input/output |
| `libsamJPGWeb.so` | MJPEG streaming + GPS WebSocket |
| `libavformat.so.58` | FFmpeg format layer |
| `libavcodec.so.58` | FFmpeg codec layer |
| `libfdk-aac.so.2` | AAC audio codec |
| `libIPC_msg.so` | Inter-process communication |

---

## FIFO Command Dispatch System

Commands are registered at startup via `CarDVAddCmdHandler(name, argCount, callback)` at `0x000654d4`. Each handler is a linked list node (0x14 bytes). `CarDVExecCmdHandler` at `0x000655a0` walks the list, matches by `strcmp`, and invokes the callback.

### Complete Command Table

| Command | Handler | Args | Description |
|---------|---------|------|-------------|
| `rec` | system_process_cmd | 1 | Start/stop recording (`rec 1`/`rec 0`) |
| `capture` | system_process_cmd | 0 | Take photo |
| **`rtsp`** | **system_process_cmd** | **1** | **Enable/disable live555 (`rtsp 1`/`rtsp 0`)** |
| **`usrstream`** | **system_process_cmd** | **1** | **Start user-stream MJPEG encoders** |
| `bitrate` | video_process_cmd | 2 | Set encoder bitrate (`bitrate <ch> <value>`) |
| `vidres` | video_process_cmd | 3 | Set video resolution (`vidres <id> <w> <h>`) |
| `capres` | video_process_cmd | 3 | Set capture resolution |
| `codec` | video_process_cmd | — | Change codec (H.264/H.265) at runtime |
| `setFrameRate` | video_process_cmd | 1 | Set frame rate |
| `seamless` | video_process_cmd | — | Seamless recording restart |
| `loop` | video_process_cmd | — | Loop recording time |
| `timelapse` | video_process_cmd | — | Timelapse recording |
| `slowmotion` | video_process_cmd | — | Slow motion mode |
| `lock` | video_process_cmd | — | Lock current recording file |
| `thumb` | video_process_cmd | — | Video thumbnail |
| `capraw` | video_process_cmd | — | Raw sensor capture (not JPEG) |
| `sdrename` | video_process_cmd | — | Rename SD card files |
| `park` | system_process_cmd | 1 | Parking mode (0-3) |
| `gsensor` | system_process_cmd | 1 | G-sensor sensitivity (0-3) |
| `parkingGsensor` | system_process_cmd | — | Parking g-sensor (separate) |
| `zoom` | system_process_cmd | — | Digital zoom |
| `video` | system_process_cmd | — | Video mode |
| `voice` | system_process_cmd | — | Voice recording on/off |
| `srcchg` | system_process_cmd | — | Switch camera source |
| `timezone` | system_process_cmd | — | Set timezone |
| `quality` | system_process_cmd | — | JPEG quality |
| `micsen` | system_process_cmd | — | Microphone sensitivity |
| `prerec` | system_process_cmd | — | Pre-record toggle |
| `vmdrectime` | system_process_cmd | — | VMD record time |
| `autorec` | system_process_cmd | — | Auto record toggle |
| `anadec` | system_process_cmd | — | Analog decoder control (rear cam) |
| `burstshot` | system_process_cmd | — | Burst shot mode |
| `datelogoStamp` | system_process_cmd | — | Date/logo stamp mode |
| `flip` | system_process_cmd | — | Video flip/rotate |
| `reset` | system_process_cmd | — | Factory reset |
| `reboot` | system_process_cmd | — | System reboot |
| `quit` | system_process_cmd | — | Exit cardv |
| `help` | system_process_cmd | — | Show help text |
| **`dumpimpl`** | **system_process_cmd** | — | **Undocumented: dump internals** |
| **`dumpimpl2`** | **system_process_cmd** | — | **Undocumented: dump internals v2** |
| `scene` | isp_process_cmd | — | Scene mode |
| `flicker` | isp_process_cmd | — | Anti-flicker (50/60Hz) |
| `shutter` | isp_process_cmd | — | Shutter speed |
| `gamma` | isp_process_cmd | — | Gamma correction |
| `effect` | isp_process_cmd | — | Image effect |
| `night` | isp_process_cmd | — | Night mode |
| `bri` / `sat` / `iso` / `wdr` / `hdr` | isp_process_cmd | — | ISP image adjustments |
| `audioplay` | audio_process_cmd | — | Play audio file |
| `aplaystop` | audio_process_cmd | — | Stop audio playback |
| `audiorec` | audio_process_cmd | — | Audio record & RTSP mute |
| `pbvolume` | audio_process_cmd | — | Playback volume |
| `audio` | audio_process_cmd | — | Audio on/off |
| `recvol` | audio_process_cmd | — | Record volume |
| `audioout` | audio_process_cmd | — | Audio output |
| `disp` | display_process_cmd | — | Display control |
| `sclrotate` | display_process_cmd | — | SCL rotation |
| `lcdbri` / `lcdcon` / `lcdhue` / `lcdsat` | display_process_cmd | — | LCD adjustments |
| `wbcMode` | display_process_cmd | — | Write-back capture mode |
| `uvc` | uvc_process_cmd | — | USB webcam mode |
| `muxdebug` | mux_process_cmd | — | Muxer debug logging |

---

## live555 RTSP Server Implementation

The binary contains a complete, statically-linked live555 RTSP library with custom subclasses for the SigmaStar video pipeline.

### Class Hierarchy

```
RTSPServer (live555 stock)
  └─ Created by live555::createNew()

live555 (custom wrapper, 0x28 bytes)
  ├─ [+0x00] state (0=uninit, 1=created, 2=stopped, 3=stopping)
  ├─ [+0x04] stop flag
  ├─ [+0x08] TaskScheduler*
  ├─ [+0x0C] UsageEnvironment*
  ├─ [+0x10] unused
  ├─ [+0x14] RTSPServer*
  ├─ [+0x18] ServerMediaSession* [0]
  ├─ [+0x1C] ServerMediaSession* [1]
  ├─ [+0x20] (reserved for session [2])
  └─ [+0x24] session count (max 2)

LiveVideoServerMediaSubsession (custom, extends OnDemandServerMediaSubsession)
  └─ createNewStreamSource() → LiveVideoSource or LiveJPEGVideoStreamSource
  └─ createNewRTPSink() → H264VideoRTPSink or H265VideoRTPSink
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

LiveAudioSource (custom, extends FramedSource)
  └─ Reads from MI audio encoder
```

### Key Addresses

| Symbol | Address | Description |
|--------|---------|-------------|
| `live555::live555()` | `0x00065ba0` | Constructor |
| `live555::createNew()` | `0x00065c98` | Full server setup |
| `live555::createServerMediaSession()` | `0x00065d7c` | Create stream session |
| `live555::startLive555Server()` | `0x00065e2c` | Start serving |
| `live555::stopLive555Server()` | `0x00065e8c` | Stop serving |
| `live555::closeServerMediaSession()` | `0x00065e10` | Close one session |
| `live555::fRtspServerPortNum` | `0x000bc89c` | Port number (554) |
| `live555::fIsRunning` | `0x000c8064` | Running flag |
| `live555_Task` | `0x00065af4` | Event loop thread |
| `LiveVideoSource::createNew()` | `0x00066cd0` | Video source factory |
| `LiveVideoSource::incomingDataHandler1()` | `0x00066eac` | Frame processing |
| `LiveVideoSource::findH264NalUnit()` | `0x00066d0c` | H.264 NAL parser |
| `LiveVideoSource::findH265NalUnit()` | `0x00066dc4` | H.265 NAL parser |

### RTSP Initialization Flow (Disassembled)

When `echo "rtsp 1" > /tmp/cardv_fifo` is received:

```
system_process_cmd (0x000633dc)
  │
  ├─ Check if live555 instance exists (global pointer)
  │   If NULL:
  │     └─ live555::createNew() (0x00065c98)
  │          ├─ BasicTaskScheduler::createNew(10000)  // 10s timeout
  │          ├─ fRtspServerPortNum = 554
  │          ├─ BasicUsageEnvironment::createNew()
  │          └─ RTSPServer::createNew(env, Port(554), NULL, 6)
  │
  ├─ Iterate all VENC channels (0..31, stride 0x7C):
  │     For each channel:
  │       ldrb r3, [encoder+0x68]  // load VencType
  │       cmp r3, #3               // is it RTSP type?
  │       bne skip                 // no → skip
  │       │
  │       └─ live555::createServerMediaSession(videoEnc, audioEnc, name, flag)
  │            ├─ Check session count <= 2 (HARDCODED MAX)
  │            ├─ ServerMediaSession::createNew(env, name)
  │            ├─ If audio: LivePCMAAudioServerMediaSubsession::createNew()
  │            ├─ LiveVideoServerMediaSubsession::createNew(env, flag, videoEnc)
  │            └─ session->addSubsession(...)
  │
  └─ live555::startLive555Server() (0x00065e2c)
       ├─ For each session: addServerMediaSession(), print rtspURL()
       ├─ fIsRunning = 1
       └─ doEventLoop() (blocks in live555_Task thread)
```

### Critical Finding: The VencType=3 Gate

The RTSP server **does start** when `rtsp 1` is sent (this happens every time WiFi is enabled, via `net_toggle.sh`). But it creates **zero media sessions** because no VENC channels have `Type=3` in the current `default.ini`. The channel scan loop at `0x000633dc`:

```arm
ldrb r3, [r3, #0x68]    ; Load VencType from encoder object
cmp  r3, #3              ; Compare with RTSP type
bne  .skip_channel       ; Skip if not RTSP
```

This means the live555 server is running right now on port 554 but has nothing to serve. Adding `VencType=3` channels to `default.ini` would give it encoder sources.

---

## MI_VideoEncoder Class Structure

Reconstructed from disassembly (0x100+ bytes per instance):

| Offset | Type | Field | Notes |
|--------|------|-------|-------|
| +0x00 | int | channel index | VENC channel number |
| +0x04 | int | MI_VENC device | Device ID |
| +0x08 | int | state | -1 = uninitialized |
| +0x20 | struct | CarDV_VencAttr_s start | 0x78 bytes, copied from ini |
| +0x48 | byte | VencType (copy 1) | From struct at +0x20 |
| +0x68 | byte | VencType (copy 2) | Accessed for RTSP check |
| +0x78 | struct | MI_SYS_ChnPort_s | Source channel port binding |
| +0xF0 | byte | rtspAudioActive | Set by start/stopAudioRtsp |
| +0xF8 | byte | streamActive | Checked in Stream_Task |

### CarDV_VencAttr_s (0x78 bytes, from INI parser)

| Offset | Type | Field |
|--------|------|-------|
| +0x00 | byte | enabled |
| +0x02 | byte | cameraIndex |
| +0x0C | int | MaxW |
| +0x10 | int | MaxH |
| +0x14 | int | BufSize |
| +0x18 | int | BitRate |
| +0x1C | byte | codec (0=H264, 1=H265) |
| +0x20 | int | GOP (default 0x50 = 80) |
| +0x24 | int | VencChn |
| +0x28 | byte | **VencType (0=rec, 1=rec, 2=cap, 3=rtsp, 4=uvc, 5=thumb, 7=user)** |
| +0x2C | int | actual channel from ini |
| +0x44 | int | FPS numerator |
| +0x4C | int | BufSize (computed: bitrate/8*4) |

### Encoder Codec Values

From `setBitrate()` and `initVideoEncoder()` analysis:

| Value | Codec | Used By |
|-------|-------|---------|
| 0 | H.264 | Record, RTSP, UVC |
| 1 | H.265 | Record |
| 2 | JPEG | Capture |
| 6 | Special | UVC (type 4) |
| 8 | H.264 | RTSP type 3 (setBitrate path) |
| 9 | H.265 | RTSP type 3 (setBitrate path) |

---

## Stream_Task Thread (per-encoder)

Address: `0x0005777c`

Each active encoder channel runs a `Stream_Task` thread:

```
Stream_Task:
  loop:
    MI_VideoEncoder::pollingStream()    // Wait for frame from hardware
    MI_VENC_GetStream()                 // Get encoded frame buffer

    if VencType > 2:                    // Type 3 (RTSP), 4 (UVC), etc.
      MI_VideoEncoder::handlerStreamPost()  // Feed to live555/UVC
    else:                               // Type 0, 1 (recording)
      [muxer/file write path]

    MI_VENC_ReleaseStream()             // Release frame buffer
    goto loop
```

This means RTSP-type encoders have a complete data path: hardware encoder → Stream_Task → handlerStreamPost → live555 FramedSource → RTP packets.

---

## Key Findings

### 1. RTSP is fully functional in the binary

The code path is complete: ini parser → encoder creation → RTSP server → media session → video source → RTP sink. No dead code, no stubs. The only reason it's inactive is the missing `VencType=3` config.

### 2. Maximum 2 simultaneous RTSP streams

Hardcoded check in `createServerMediaSession`: `cmp r0, 2; bgt return_error`. This would allow one front + one rear camera stream.

### 3. Adaptive bitrate for RTSP

`LiveVideoServerMediaSubsession::adjustBitRateByRtd()` at `0x000664e8` adjusts bitrate based on round-trip delay — a quality-of-service feature for unstable WiFi.

### 4. Audio over RTSP is supported

G.711 A-law audio via `LivePCMAAudioServerMediaSubsession`. Controlled by `Camera.Preview.RTSP.av` nvconf key and the `audiorec` FIFO command.

### 5. The `rtsp 1` command is already sent at every WiFi enable

`net_toggle.sh` sends `echo rtsp 1 > tmp/cardv_fifo` when WiFi turns on. The RTSP server is **already running** — it just has no streams because no VencType=3 channels exist.

### 6. Undocumented debug commands

`dumpimpl` and `dumpimpl2` may dump internal encoder state, pipeline configuration, or memory maps. These could be extremely useful for understanding the runtime state without modifying firmware.

### 7. The port 554 is writable at runtime

`live555::fRtspServerPortNum` at `0x000bc89c` is in the `.data` section (not `.rodata`). It's loaded during `createNew()` — if it could be modified before that call (e.g., via nvconf), the port could be changed.

### 8. VencType=3 initialization falls through to generic path

In `initVideoEncoder()`, type=3 doesn't have a dedicated branch — it falls through to a generic VENC channel creation path. This means the encoder channel WILL be created; it just won't have type-specific optimizations. The `setBitrate()` function does handle type=3 explicitly for H.264 (codec=8) and H.265 (codec=9).
