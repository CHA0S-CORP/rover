echo 86 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio86/direction
echo 1 > /sys/class/gpio/gpio86/value
echo 42 > /sys/class/gpio/export
echo in > /sys/class/gpio/gpio42/direction
echo 52 > /sys/class/gpio/export
echo in > /sys/class/gpio/gpio52/direction
gpio42=`cat /sys/class/gpio/gpio42/value`
gpio52=`cat /sys/class/gpio/gpio52/value`
echo gpio42=$gpio42
echo gpio52=$gpio52
if [ $gpio42 = 0 ] && [ $gpio52 = 0 ]; then
echo "hw ver is 0.0"
else
echo "hw ver not is 0.0"
cp -f /misc/config_rzw.ini /misc/config.ini
fi
echo 78 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio78/direction
echo 1 > /sys/class/gpio/gpio78/value
insmod /bootconfig/modules/4.9.227/mhal.ko
insmod /bootconfig/modules/4.9.227/mmc_core.ko
insmod /bootconfig/modules/4.9.227/mmc_block.ko
insmod /bootconfig/modules/4.9.227/cfg80211.ko
#misc_mod_list
insmod /bootconfig/modules/4.9.227/mi_common.ko
insmod /bootconfig/modules/4.9.227/mi_sys.ko  default_config_path="/bootconfig" cmdQBufSize=3072 logBufSize=256
insmod /bootconfig/modules/4.9.227/mi_sensor.ko
insmod /bootconfig/modules/4.9.227/mi_gfx.ko
insmod /bootconfig/modules/4.9.227/mi_rgn.ko
insmod /bootconfig/modules/4.9.227/mi_fb.ko
insmod /bootconfig/modules/4.9.227/mi_mipitx.ko
insmod /bootconfig/modules/4.9.227/mi_scl.ko
insmod /bootconfig/modules/4.9.227/mi_vdec.ko
insmod /bootconfig/modules/4.9.227/mi_hdmi.ko
insmod /bootconfig/modules/4.9.227/mi_isp.ko
insmod /bootconfig/modules/4.9.227/mi_ipu.ko
insmod /bootconfig/modules/4.9.227/mi_shadow.ko
insmod /bootconfig/modules/4.9.227/mi_jpd.ko
insmod /bootconfig/modules/4.9.227/mi_ao.ko
insmod /bootconfig/modules/4.9.227/mi_ldc.ko
insmod /bootconfig/modules/4.9.227/mi_ai.ko
insmod /bootconfig/modules/4.9.227/mi_panel.ko
insmod /bootconfig/modules/4.9.227/mi_disp.ko
insmod /bootconfig/modules/4.9.227/mi_vif.ko
insmod /bootconfig/modules/4.9.227/mi_venc.ko fw_path="/bootconfig/venc_fw/chagall.bin" max_h26x_width=4608 max_h26x_height=2592
insmod /bootconfig/modules/4.9.227/mi_vdisp.ko
insmod /bootconfig/modules/4.9.227/kdrv_sdmmc.ko
insmod /bootconfig/modules/4.9.227/fat.ko
insmod /bootconfig/modules/4.9.227/vfat.ko
#mi module
major=`cat /proc/devices | busybox awk "\\$2==\""mi_poll"\" {print \\$1}"`
busybox mknod /dev/mi_poll c $major 0
insmod /bootconfig/modules/4.9.227/imx675_MIPI.ko chmap=1 lane_num=4
insmod /bootconfig/modules/4.9.227/tp9950_MIPI.ko chmap=8 lane_num=2
echo 31 > sys/class/mstar/msys/booting_time
mount -t ubifs ubi0:miservice /config

echo 32 > sys/class/mstar/msys/booting_time
source /config/misc_profile.sh
echo 432000000 > /sys/devices/virtual/mstar/isp0/isp_clk
echo 480000000 > /sys/devices/virtual/mstar/mscl/clk
echo 384000000 > /sys/devices/virtual/mstar/venc/ven_clock
echo 384000000 > /sys/devices/virtual/mstar/venc/ven_clock_2nd
echo 384000000 > /sys/devices/virtual/mstar/venc/ven_clock_axi
riu_w 0x1012 0x4c 0x03
riu_w 0x1012 0x40 0x831d
riu_w 0x1012 0x4b 0x3001
riu_w 0x1012 0x5C 0xFFFD
panel_probe.sh
#Turn off WIFI PWR
riu_w 3f 06 7B
echo /bootconfig/iqfile > /sys/devices/virtual/mstar/ispmid0/isproot
echo 1 > /sys/devices/soc0/soc/1f203200.pwm/pwm/pwmchip0/export
echo 100000 > /sys/devices/soc0/soc/1f203200.pwm/pwm/pwmchip0/pwm1/period
echo 0 > /sys/devices/soc0/soc/1f203200.pwm/pwm/pwmchip0/pwm1/duty_cycle
echo 1 > /sys/devices/soc0/soc/1f203200.pwm/pwm/pwmchip0/pwm1/enable
echo 88 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio88/direction
echo 1 > /sys/class/gpio/gpio88/value
echo 111 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio111/direction
echo 0 > /sys/class/gpio/gpio111/value
echo 1 > /proc/sys/kernel/softlockup_panic
echo 0 > /sys/module/mhal/parameters/drv_venc_wrapper.g_tmvpEnable
echo 6 > /sys/class/gpio/export
gpio6=`cat /sys/class/gpio/gpio6/value`
echo gpio6=$gpio6
if [ $gpio6 = 0 ]; then
if [ $gpio42 = 0 ] && [ $gpio52 = 0 ]; then
cardv /bootconfig/bin/default.ini &
else
cardv /bootconfig/bin/default_rzw.ini &
fi
else
if [ $gpio42 = 0 ] && [ $gpio52 = 0 ]; then
cardv /bootconfig/bin/default_norear.ini &
else
cardv /bootconfig/bin/default_norear_rzw.ini &
fi
fi
wait_rec.sh
echo 33 > sys/class/mstar/msys/booting_time
mount -t ubifs ubi0:customer /customer

mount -t ubifs ubi0:serial /serial

echo 34 > sys/class/mstar/msys/booting_time


#misc_mod_list_late
mount -t configfs none /customer/config
insmod /customer/modules/4.9.227/usb-common.ko
insmod /customer/modules/4.9.227/usbcore.ko
insmod /customer/modules/4.9.227/ehci-hcd.ko
insmod /customer/modules/4.9.227/usb-storage.ko
insmod /customer/modules/4.9.227/nls_utf8.ko
insmod /customer/modules/4.9.227/grace.ko
insmod /customer/modules/4.9.227/sunrpc.ko
insmod /customer/modules/4.9.227/lockd.ko
insmod /customer/modules/4.9.227/adc-keys.ko
insmod /customer/modules/4.9.227/media.ko
insmod /customer/modules/4.9.227/videodev.ko
insmod /customer/modules/4.9.227/v4l2-common.ko
insmod /customer/modules/4.9.227/videobuf2-core.ko
insmod /customer/modules/4.9.227/videobuf2-v4l2.ko
insmod /customer/modules/4.9.227/videobuf2-memops.ko
insmod /customer/modules/4.9.227/videobuf2-vmalloc.ko
insmod /customer/modules/4.9.227/udc-core.ko
insmod /customer/modules/4.9.227/libcomposite.ko
insmod /customer/modules/4.9.227/usb_f_uvc.ko
insmod /customer/modules/4.9.227/udc-msb250x.ko
insmod /customer/modules/4.9.227/g_webcam.ko streaming_maxpacket=3072 uac_function_enable=0
#kernel_mod_list
#Do not to auto insmod ko
#kernel_mod_list_late
zkgui &
if [ -e /customer/wifi/rcInsDriver.sh ]; then
/customer/wifi/rcInsDriver.sh
fi;
if [ ! -e /config/cgi_config_bak.bin ]; then
cp /customer/wifi/webserver/www/cgi-bin/cgi_config.bin /config/cgi_config_bak.bin
fi;
