# Flashing Custom Firmware — Rove R2-4K-DUAL

Enables the dormant live555 RTSP server on port 554 by adding a `VencType=3`
encoder channel to the camera's `default.ini`. The stock recording, MJPEG
stream, and rear camera all continue to work normally.

## Prerequisites

- macOS (tested) or Linux with `python3`, `cpio`, `gzip`, `tar`
- `ffmpeg` / `ffprobe` for post-flash verification
- The Rove firmware APK at `rove_split_firmware_pack.apk` in the repo root
- A FAT32-formatted SD card

## What Changes

One file is modified inside the rootfs cpio: `bootconfig/bin/default.ini`.

| Setting | Stock | Modified |
|---------|-------|----------|
| `VencNum` (Cam0) | 5 | 6 |
| Commented-out Venc3 subrec block | `#Venc3Type = 1` | Activated as `Venc3Type = 3` (RTSP) |
| Venc3 (thumbnail) | index 3 | Renumbered to Venc4 |
| Venc4 (user stream) | index 4 | Renumbered to Venc5 |

The new **Venc3** is a 640x360 H.264 RTSP stream at 2 Mbps, bound to scaler
port 1 (the existing 640x360 output). This is the validation tier — proving
the RTSP pipeline works before attempting 4K.

Everything else is untouched: Venc0 (4K H.265 recording), Venc1 (UVC),
Venc2 (capture), Mux0/Mux1 (file muxers), rear camera (Cam1), OSD, display.

## Build

All commands run from the `firmware/` directory:

```bash
cd firmware
```

### 1. Extract firmware from the APK

```bash
make setup
```

This extracts `R2D.tar` from the APK, unpacks `R2D.bin`, and decompresses
the rootfs cpio into `work/rootfs/`. The original `R2D.bin` is backed up to
`work/R2D.bin.orig` automatically.

### 2. Back up the stock config

```bash
make backup
```

Copies `default.ini` to `default.ini.bak` so `make diff` can show changes.

### 3. Edit the config

The RTSP changes are already applied if you're working from this branch.
To review them:

```bash
make diff
```

To make further edits:

```bash
make edit
```

### 4. Build the firmware image

```bash
make build
```

This repacks the rootfs cpio, patches the U-Boot header script with the new
rootfs size (and shifts the UBIFS partition if needed), reassembles `R2D.bin`,
and verifies gzip/UBIFS magic bytes at the expected offsets.

### 5. Package for flashing

```bash
make tar
```

Creates `work/R2D.tar` containing `IPL`, `IPL_CUST`, `UBOOT`, and the
modified `R2D.bin`.

### 6. Copy to SD card

```bash
make flash-sd SD=/Volumes/YOUR_SD
```

Copies `R2D.tar` to the SD card as `SigmastarUpgradeSD.bin`, the filename
the camera's bootloader looks for during OTA updates.

Or do steps 4-6 in one shot:

```bash
make flash SD=/Volumes/YOUR_SD
```

## Flash the Camera

1. **Eject** the SD card from your computer.
2. Insert it into the camera's SD slot.
3. Power on the camera.
4. The LED will blink during the update. **Do not power off.**
5. The camera reboots automatically when done.

The update writes to NAND flash and typically takes 30-60 seconds.

## Verify

Connect to the camera's WiFi network, then:

```bash
make verify
```

This checks:
- Ping reachability
- HTTP port 80 (GoAhead web server)
- MJPEG port 8192 (stock stream — should still work)
- **RTSP port 554** (new — should now be open)
- RTSP stream probe via `ffprobe` (codec, resolution, framerate)
- 3-second RTSP capture via `ffmpeg`

Manual check:

```bash
ffprobe -rtsp_transport tcp rtsp://192.168.1.252:554/
ffplay -rtsp_transport tcp rtsp://192.168.1.252:554/
```

Expected output for the validation tier:

```
Stream #0:0: Video: h264, 640x360, 25 fps
```

## Using RTSP in the Rover App

The app has RTSP-sourced HLS streaming alongside the existing MJPEG mode.

- **Start**: Click "RTSP HLS" in the dashboard, or `POST /api/stream/rtsp/start`
- **Stop**: Click "Stop RTSP", or `POST /api/stream/rtsp/stop`
- **Watch**: The HLS playlist is served at `/hls/live.m3u8` (same as MJPEG HLS)

The RTSP path uses `ffmpeg -c:v copy` — no transcoding. The camera's hardware
encoder output is muxed directly into HLS segments.

## Recovery

If the camera doesn't boot or behaves incorrectly after flashing:

### Option A: Reflash stock firmware

```bash
make restore   # reverts R2D.bin to the backed-up original
make tar
make flash-sd SD=/Volumes/YOUR_SD
```

Then flash the camera again using the same SD card procedure.

### Option B: SD card recovery

If you can't run `make restore` (e.g. the work directory is gone):

1. Extract the stock `R2D.tar` from the APK:
   ```bash
   unzip rove_split_firmware_pack.apk assets/R2D.tar
   ```
2. Copy it to the SD card:
   ```bash
   cp assets/R2D.tar /Volumes/YOUR_SD/SigmastarUpgradeSD.bin
   ```
3. Insert the SD card and power on the camera.

The U-Boot bootloader is on a separate NAND partition and is not modified by
this process. As long as U-Boot is intact, the camera can always be recovered
via SD card.

## Next Steps (4K RTSP)

Once the 640x360 validation tier is confirmed working:

**Repurpose the recording encoder** — change `Venc0Type` from `0` (recording)
to `3` (RTSP). This sends the existing 4K H.265 30 Mbps encoder output to
the RTSP server instead of the file muxer. Comment out the Mux0 and Mux1
blocks since there's nothing to mux.

```ini
Venc0Type = 3

#Mux0Chn = 0
#Mux0TrakNum = 1
#Mux0Trak0Venc = 0
#Mux0Type = 0
#Mux0File = 0
#Mux0Thumb = 1

#Mux1Chn = 1
#Mux1TrakNum = 1
#Mux1Trak0Venc = 0
#Mux1Type = 1
#Mux1File = 0
#Mux1Thumb = 1
```

Then `make build && make flash SD=/Volumes/YOUR_SD` and verify:

```
Stream #0:0: Video: hevc, 3840x2160, 30 fps
```

## Binary Layout

The `R2D.bin` upgrade image contains an embedded U-Boot script that tells the
bootloader where each partition lives:

| Partition | Offset | Size | Description |
|-----------|--------|------|-------------|
| Header script | 0x000000 | 96 KB | U-Boot `fatload`/`nand write` commands |
| IPL | 0x00B000 | 26 KB | Initial program loader |
| IPL_CUST | 0x012000 | 21 KB | Customer IPL |
| UBOOT | 0x018000 | 284 KB | U-Boot bootloader |
| Kernel | 0x060000 | 2.4 MB | Linux kernel (uImage, LZMA) |
| Rootfs | 0x2BF000 | 8.6 MB | Root filesystem (cpio.gz) |
| Customer | 0xB59000 | 16.6 MB | UBIFS (WiFi webserver config, etc.) |
| MISC | 0x1BF0000 | 896 KB | Miscellaneous |

The build tool (`scripts/fwtool.py`) patches the header script automatically
when the rootfs size changes, and shifts the UBIFS partition forward if the
rootfs grows beyond its original boundary.

## Make Targets

```
  setup           Extract R2D.tar from APK and unpack R2D.bin + rootfs
  backup          Back up original default.ini (before any edits)
  edit            Open default.ini in $EDITOR
  diff            Show config changes from stock default.ini
  build           Repack rootfs and rebuild R2D.bin
  tar             Create R2D.tar from R2D.bin + bootloader components
  flash-sd        Copy R2D.tar to SD card as SigmastarUpgradeSD.bin (set SD=/path)
  info            Show firmware layout, partition sizes, and integrity checks
  verify          Run post-flash verification (ping, RTSP, MJPEG)
  restore         Restore R2D.bin to stock from backup
  clean           Remove build artifacts (keeps rootfs/ and backups)
  clean-all       Remove entire work directory (full reset)
  all             Build and package (shortcut)
  flash           Build, package, and copy to SD card
```
