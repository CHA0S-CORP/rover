# Custom Firmware Feasibility Analysis

## Executive Summary

Building custom firmware for the Rove R2-4K-DUAL is **feasible but high-effort**. The most practical approach is modifying the existing firmware's `default.ini` to enable the dormant RTSP encoder channels, which could yield an H.264 live stream without touching any binaries. A full custom firmware (replacing `cardv` or adding new services) is significantly harder due to the proprietary SigmaStar SDK dependency.

## Approach 1: Configuration-Only Mod (Low Risk, Medium Reward)

### What
Modify `default.ini` on the camera's flash to uncomment the H.264 sub-stream encoder channels and configure them to feed the live555 RTSP server.

### How

1. **Extract firmware**: Unpack `R2D.tar` → extract `R2D.bin` → extract UBIFS/cpio
2. **Modify `default.ini`**: Uncomment the subrec encoder channels:
   ```ini
   Venc3Chn = 3
   Venc3Type = 3          # Change from 1 (subrec) to 3 (rtsp)
   Venc3Codec = 0          # H.264
   Venc3BitRate = 2000000   # 2 Mbps (increase from 800K)
   Venc3InBindMod = 34
   Venc3InBindDev = 0
   Venc3InBindChn = 0
   Venc3InBindPort = 1     # Scl0/HWScl1 (640x360)
   ```
3. **Repack firmware**: Rebuild cpio → rebuild R2D.bin → repack R2D.tar
4. **Flash**: Place on SD card, trigger OTA update

### Expected Result
- RTSP stream at `rtsp://192.168.1.252:554/` with H.264 640x360
- Much better video quality than MJPEG at same resolution (H.264 temporal compression vs independent JPEG frames)
- ~2-5 second latency via RTSP

### Risks
- **Brick risk**: Incorrect firmware format could leave camera unbootable. The bootloader likely has recovery mode, but it's undocumented.
- **Encoder resource conflict**: The SoC has limited encoder instances. Adding a channel might exceed the hardware encoder's capacity, causing instability.
- **Memory pressure**: Each encoder channel requires DMA buffers. The subrec channels were likely commented out to save memory on this dual-camera model.
- **`cardv` may reject unknown VencType**: If the `cardv` binary doesn't handle type=3 (rtsp) in its config parser, it will fail to start.

### Difficulty: Medium
Requires firmware extraction/repacking toolchain and comfort with embedded Linux. No binary modification needed.

## Approach 2: Higher Resolution MJPEG (Low Risk, Low Reward)

### What
Change the user-stream scaler resolution from 640x360 to 1280x720 or 1920x1080 in `default.ini`.

### How

Modify the Scl4 scaler that feeds the MJPEG encoder:
```ini
# Change from:
Scl4HWScl5W = 640
Scl4HWScl5H = 360

# To:
Scl4HWScl5W = 1280
Scl4HWScl5H = 720
```

And increase the JPEG bitrate:
```ini
Venc4BitRate = 8000000    # 8 Mbps (from 2 Mbps)
```

### Expected Result
- 720p MJPEG stream on port 8192
- Higher bandwidth usage (~8-10 Mbps for decent JPEG quality at 720p)
- May hit WiFi throughput ceiling on 2.4GHz

### Risks
- **WiFi bandwidth**: 720p MJPEG at 25fps requires ~8 Mbps sustained. The 5GHz AP can handle this; 2.4GHz cannot.
- **Scaler hardware limits**: The HWScl5 scaler may have a maximum resolution. Exceeding it would crash the pipeline.
- **Encoder throughput**: JPEG encoding at 720p@25fps requires significant silicon bandwidth, potentially starving the H.265 recording encoder.
- **1080p may be impossible**: The user-type encoder probably can't handle 1080p — the scaler feeding it is a lower-priority instance (Scl4, shared RDMA bus).

### Difficulty: Low
Same modification technique as Approach 1, just different values.

## Approach 3: Runtime RTSP Activation (No Flash Modification)

### What
Attempt to enable RTSP and reconfigure encoders at runtime via the FIFO command interface, without modifying flash.

### How

Send commands to the camera via the CGI API:
```bash
# Try enabling RTSP
curl "http://192.168.1.252/cgi-bin/Config.cgi?action=set&property=Camera.Preview.RTSP.av&value=4"

# Try changing resolution via FIFO
curl "http://192.168.1.252/cgi-bin/Config.cgi?action=set&property=setbitrate&value=4000000"

# Check if RTSP port opens
nc -z 192.168.1.252 554
```

The `cardv` binary accepts `res <id> <w> <h>` and `bitrate <ch> <value>` commands via the FIFO. If the RTSP server is already started (net_toggle.sh sends `rtsp 1`), it might be possible to create a media session by reconfiguring an existing encoder channel at runtime.

### Expected Result
- Possibly an RTSP stream if `cardv` can dynamically rebind an encoder to the RTSP server
- More likely: commands will be accepted but have no visible effect because the encoder channels aren't allocated for RTSP in the static config

### Risks
- Very low risk — commands that fail are simply ignored
- Camera may need a reboot after changes

### Difficulty: Low
Just HTTP requests. Worth trying before any firmware modification.

## Approach 4: Replace `cardv` Binary (High Risk, High Reward)

### What
Replace the `cardv` application with a custom binary that configures the video pipeline differently, enabling proper RTSP or even HLS streaming at native resolution.

### How
1. Cross-compile a custom application using the SigmaStar MI SDK
2. Configure the video pipeline to include:
   - Front camera: 3840x2160 H.265 recording + 1920x1080 H.264 RTSP + 640x360 MJPEG
   - Rear camera: 1920x1080 H.265 recording + 1920x1080 H.264 RTSP
3. Integrate live555 or a simpler RTSP server
4. Optionally add go2rtc or mediamtx for WebRTC

### Challenges
- **SigmaStar SDK is NDA-only**: The MI (Media Interface) SDK is not publicly available. Header files can be partially reconstructed from the kernel modules and string extraction, but proper SDK documentation is needed.
- **CarDV framework**: The `cardv` binary implements recording, G-sensor event detection, file management, display, audio, GPS, and OSD — replacing it means reimplementing all of that or forking the CarDV source (which is also NDA).
- **Boot dependency**: `demo.sh` expects `cardv` to be the main application. A replacement must handle the same FIFO protocol for CGI compatibility.
- **Testing**: No JTAG/serial debug access documented. Firmware flash failures mean a potentially bricked camera.

### SDK Sources (Partial)

The SigmaStar "Ikayaki" SDK has been partially leaked/open-sourced:
- GitHub: `AIT8428_CarDV_SDK_Ver1.0.0x000_r5412` (ancestor platform)
- Various SigmaStar SSC335/SSC337 camera SDK leaks on Chinese electronics forums
- The MI API (`MI_VENC_*`, `MI_ISP_*`, `MI_SCL_*`) is consistent across SigmaStar platforms

The `cardv-strings.txt` reference file contains all exported MI function names, which can be used to reconstruct API headers.

### Difficulty: Very High
Requires embedded Linux cross-compilation experience, SigmaStar MI SDK (NDA), and willingness to risk bricking the camera.

## Approach 5: Add a Sidecar Service (Medium Risk, Medium Reward)

### What
Add a lightweight streaming service (like `mediamtx` or `go2rtc`) to the camera's UBIFS partition that reads from the existing MJPEG stream and transcodes/restreams it.

### How
1. Cross-compile `mediamtx` or `ffmpeg` for ARM (the camera runs Linux, so standard ARM binaries work)
2. Add to `/customer/` partition
3. Modify `ap_delay.sh` to start the sidecar after WiFi is up
4. The sidecar reads `http://127.0.0.1:8192` and provides HLS/WebRTC/RTSP

### Limitations
- **CPU**: The ARM core is likely a Cortex-A7 at ~1GHz. Transcoding MJPEG→H.264 in software at 640x360@25fps is possible but will consume significant CPU, potentially affecting recording stability.
- **Memory**: Limited RAM on embedded SoC. A Go binary (mediamtx) may be too large.
- **No resolution improvement**: The source is still 640x360 MJPEG. The sidecar only changes the delivery protocol, not the quality.
- **Storage**: UBIFS partition has limited free space.

### Better Alternative
Do this transcoding on the Raspberry Pi instead (which is what Rover already does with ffmpeg MJPEG→HLS). The Pi has far more CPU/RAM headroom.

### Difficulty: Medium
Cross-compilation is straightforward, but space/CPU constraints on the camera make it impractical.

## Recommendation

**Try Approach 3 first** (runtime commands) — it's zero-risk and takes 5 minutes. If that doesn't yield an RTSP stream, proceed to **Approach 1** (config mod) to uncomment the encoder channels. Approach 2 (higher-res MJPEG) is also worth trying alongside Approach 1.

Approaches 4 and 5 are not recommended unless you have experience with SigmaStar platforms and a spare camera to experiment with.

## Tools Required

| Tool | Purpose |
|------|---------|
| `binwalk` | Firmware extraction |
| `ubireader` / `ubi_reader` | UBIFS filesystem extraction |
| `mkfs.ubifs` + `ubinize` | UBIFS repacking |
| `cpio` | Root filesystem packing |
| `mkimage` | U-Boot image creation |
| ARM cross-compiler | Any custom binary compilation |
| `strings`, `readelf`, `objdump` | Binary analysis |

## Flash Layout (for repacking)

```
R2D.bin:
  0x00000000 - 0x00017FFF : Header/padding
  0x00018000 - 0x002BEFFF : uImage (kernel, LZMA)
  0x002BF000 - 0x00B58FFF : cpio rootfs (gzip)
  0x00B59000 - END        : UBIFS image
```

The exact offsets must be verified with `binwalk` before repacking, as they may shift with content size changes.
