# Firmware Structure

## Packaging

The firmware is distributed inside the Android companion app APK:
- **APK**: `rove_split_firmware_pack.apk` (255 MB)
- **Inside APK**: `assets/R2D.tar` (29 MB) — the R2-4K-DUAL firmware
- Other camera models have their own tarballs (R2.tar, R3.tar, etc.)

## R2D.tar Contents

```
R2D.tar
├── IPL           — Initial Program Loader (SigmaStar bootROM payload)
├── IPL_CUST      — Customer-specific IPL configuration
├── UBOOT         — U-Boot bootloader
└── R2D.bin       — Combined kernel + rootfs + UBIFS image
```

## R2D.bin Layout

Analyzed with `binwalk`:

| Offset | Content | Size | Description |
|--------|---------|------|-------------|
| 0x18000 | uImage | ~2.6 MB | ARM Linux 4.9.227, LZMA compressed |
| 0x2BF000 | cpio rootfs | ~8.7 MB | gzip compressed, main root filesystem |
| 0xB59000 | UBIFS | ~17 MB | Flash filesystem, mounts at /config and /customer |

## Root Filesystem (`/`)

Extracted from the cpio archive:

```
/
├── bin/              — BusyBox symlinks
├── bootconfig/
│   ├── bin/
│   │   ├── cardv            — MAIN APPLICATION (629 KB ARM ELF)
│   │   ├── default.ini      — Video pipeline configuration
│   │   ├── default_norear.ini
│   │   ├── default_rzw.ini
│   │   └── default_norear_rzw.ini
│   ├── demo.sh              — Boot script (loads modules, starts cardv)
│   ├── iqfile/              — ISP image quality tuning files
│   │   └── isp_api.bin
│   ├── modules/4.9.227/     — Kernel modules (.ko)
│   │   ├── mi_venc.ko       — Video encoder
│   │   ├── mi_isp.ko        — Image signal processor
│   │   ├── mi_scl.ko        — Hardware scaler
│   │   ├── imx675_MIPI.ko   — Front camera sensor driver
│   │   ├── tp9950_MIPI.ko   — Rear camera analog decoder
│   │   ├── cfg80211.ko      — WiFi configuration
│   │   └── ... (30+ modules)
│   └── venc_fw/
│       └── chagall.bin      — Video encoder firmware blob
├── config/           — Mount point for UBIFS partition 1
├── customer/         — Mount point for UBIFS partition 2
├── dev/
├── etc/
├── lib/
│   ├── libsamJPGWeb.so      — MJPEG server + GPS WebSocket (CivetWeb-based)
│   ├── libmi_*.so           — SigmaStar multimedia framework libraries
│   └── ...
├── sbin/
├── usr/
└── vendor/
```

## UBIFS Partition (`/customer`)

Mounted from the UBIFS image, contains WiFi and web server files:

```
/customer/
├── wifi/
│   ├── goahead              — GoAhead embedded web server binary
│   ├── lib/
│   │   ├── libgo.so         — GoAhead shared library
│   │   ├── bcmdhd.ko        — Broadcom WiFi driver (AP6256)
│   │   ├── fw_bcm43456c5_ag_apsta.bin  — WiFi firmware
│   │   └── nvram_ap6256.txt — WiFi calibration data
│   ├── net_toggle.sh        — WiFi enable/disable + RTSP toggle
│   ├── ap_delay.sh          — AP mode startup (triggers stream)
│   ├── ap.sh                — Access point configuration
│   ├── sta.sh               — Station mode configuration
│   ├── run_goahead.sh       — Starts GoAhead web server
│   ├── hostapd.conf         — 5GHz AP config
│   ├── hostapd_2_4g.conf    — 2.4GHz AP config
│   ├── udhcpd-ap.conf       — DHCP server config
│   ├── net_config.bin        — Default network settings (text format)
│   ├── webserver/
│   │   ├── conf/
│   │   │   ├── route.txt    — GoAhead URL routing
│   │   │   └── auth.txt     — Authentication config (no auth configured)
│   │   └── www/
│   │       ├── CGI_PROCESS.sh    — CGI command handler (50 KB shell script)
│   │       └── cgi-bin/
│   │           ├── Config.cgi    — CGI entry point
│   │           ├── CGI_COMMAND.txt — API documentation
│   │           ├── net_config.bin
│   │           └── cgi_config.bin
│   └── rcInsDriver.sh       — WiFi driver init
├── modules/4.9.227/
│   ├── usb-common.ko
│   ├── g_webcam.ko           — USB webcam gadget driver
│   ├── videodev.ko           — V4L2
│   └── ... (USB, NFS, media modules)
├── config/           — ConfigFS mount point
├── gadget/           — USB gadget configuration
└── UI/               — Display/GUI resources
```

## Boot Sequence

From `demo.sh`, the boot process:

1. **GPIO init**: Export GPIOs for power, camera detection, hardware version
2. **Hardware version check**: GPIO 42+52 determine board revision
3. **Kernel module loading**: 25+ modules in specific order
   - Core: `mhal.ko`, `mi_common.ko`, `mi_sys.ko`
   - Video: `mi_sensor.ko`, `mi_isp.ko`, `mi_scl.ko`, `mi_venc.ko`
   - Display: `mi_fb.ko`, `mi_mipitx.ko`, `mi_disp.ko`, `mi_panel.ko`
   - Camera sensors: `imx675_MIPI.ko`, `tp9950_MIPI.ko`
   - Storage: `kdrv_sdmmc.ko`, `fat.ko`, `vfat.ko`
4. **Mount UBIFS**: `/config` partition
5. **Clock configuration**: ISP 432MHz, Scaler 480MHz, VENC 384MHz
6. **Panel probe**: Display initialization
7. **Start cardv**: `cardv /bootconfig/bin/default.ini &`
   - GPIO 6 selects dual/single camera config
   - GPIO 42+52 select hardware revision variant
8. **Wait for recording**: `wait_rec.sh`
9. **Mount customer partition**: `/customer`
10. **USB gadget**: Load UVC webcam driver (`g_webcam.ko streaming_maxpacket=3072`)
11. **GUI**: Start `zkgui` (display UI application)
12. **WiFi driver**: Execute `rcInsDriver.sh`

## Key Binary: `cardv`

The `cardv` binary (629 KB) is the main camera application. It:
- Reads `default.ini` for video pipeline configuration
- Initializes all SigmaStar MI (Media Interface) modules
- Manages recording to SD card
- Hosts the live555 RTSP server (statically linked)
- Loads `libsamJPGWeb.so` dynamically for MJPEG/GPS servers
- Listens on `/tmp/cardv_fifo` for commands from CGI and shell scripts
- Handles photo capture, recording start/stop, resolution changes

### FIFO Command Interface

`cardv` reads commands from `/tmp/cardv_fifo`:

| Command | Description | Source |
|---------|-------------|--------|
| `rec 1` / `rec 0` | Start/stop recording | CGI_PROCESS.sh |
| `capture` | Take photo | CGI_PROCESS.sh |
| `rtsp 1` / `rtsp 0` | Enable/disable RTSP server | net_toggle.sh |
| `usrstream 0` | Start user-stream (MJPEG) encoders | ap_delay.sh |
| `vidres W H` | Set video recording resolution | CGI_PROCESS.sh |
| `capres W H` | Set capture resolution | CGI_PROCESS.sh |
| `bitrate CH VALUE` | Set encoder bitrate | CGI_PROCESS.sh |
| `res ID W H` | Set stream resolution | CLI |
| `setframerate VALUE` | Set frame rate | CGI |
| `setvideogop VALUE` | Set GOP size | CGI |
| `forceiframe` | Force I-frame | CGI |

### CLI Commands (from string extraction)

```
'res <stream id> <width> <height>'    — e.g., 'res 0 1920 1080' for full HD
'bitrate <channel id> <value>'        — e.g., 'bitrate 0 10000000' for 10M bps
'rtsp'                                — 'rtsp 1' enable live555
'audioplay 0/1 dev_id <live/name>'    — audio live streaming
'audiorec <value[0, 1]>'              — audio record & rtsp mute
```
