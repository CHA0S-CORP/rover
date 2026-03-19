#!/bin/sh
echo "Launch device driver in rcInsDriver.sh..."
#sleep 2

#NETEN=`nvconf get 0 Camera.Menu.smWiFi`
#APSTA=`nvconf get 1 wireless.apstaswitch`

insmod /customer/wifi/lib/aic_load_fw.ko aic_fw_path=/vendor/etc/firmware/aic8800D80
sleep 0.5
insmod /customer/wifi/lib/aic8800_fdrv.ko aicwf_dbg_level=1
