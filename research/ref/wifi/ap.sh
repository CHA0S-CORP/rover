#!/bin/sh

WIFI_MODE=`nvconf get 0 Camera.Menu.smWiFiMode`
case "$1" in
  start)
  	echo "Launch Wifi module AP Mode ..."



	if [ "`lsmod|grep $WIFI_MODULE`" == "" ]; then
		if [ "$WIFI_MODULE" == "bcmdhd" ]; then
			echo "wifi module is ap6256"
			HOSTAPD="hostapd_ap6256"
			insmod /customer/wifi/lib/bcmdhd.ko firmware_path=/customer/wifi/lib/fw_bcm43456c5_ag_apsta.bin nvram_path=/customer/wifi/lib/nvram_ap6256.txt
		else
			#echo "wifi modu1e is $WIFI_MODULE.ko"
			#HOSTAPD="hostapd"
			#insmod /customer/wifi/lib/$WIFI_MODULE.ko
			#insmod /customer/wifi/lib/aic_load_fw.ko aic_fw_path=/vendor/etc/firmware/aic8800D80
			#insmod /customer/wifi/lib/aic8800_bsp.ko
			#insmod /customer/wifi/lib/aic8800_fdrv.ko
			if [ "$WIFI_MODE" == "2_4G" ]; then
				HOSTAPD="hostapd_2_4g"
				echo "2.4G ... hostapd_config"
				cp /customer/wifi/hostapd_backup_2_4g.conf /customer/wifi/hostapd_2_4g.conf
				sync
			else
				HOSTAPD="hostapd"
				echo "5G ... hostapd_config"
				cp /customer/wifi/hostapd_backup.conf /customer/wifi/hostapd.conf
				sync
			fi
		fi
	fi

	sleep 1

	if [ $? -eq 1 ]; then
		exit 1
	fi

	IPADDR="`nvconf get 1 wireless.ap.ipaddr`"
	SUBNETMASK="`nvconf get 1 wireless.ap.subnetmask`"
	#sleep 1
	ifconfig wlan0 up
	ifconfig wlan0 $IPADDR netmask $SUBNETMASK
	sleep 1
	/usr/sbin/udhcpd -S /customer/wifi/udhcpd-ap.conf &

	if [ -f "/config/net_config.bin" ]; then
		diff /config/net_config.bin /customer/wifi/net_config.bin > /dev/null
		if [ $? -eq 0 ]; then
    		echo "The files are the same"
		else
			echo "The files are different"
			cp /config/net_config.bin /customer/wifi/net_config.bin
			sync
		fi
	fi

	WIFIMAC="`cat /sys/class/net/wlan0/address | /usr/bin/awk -F ":" '{print $4$5$6}`"
	bSSID=`cat /customer/wifi/webserver/www/cgi-bin/net_config.bin|grep wireless.ap.ssid|sed 's/^[[:print:]]\{17\}//'|sed 's/[[:print:]]\{2\}$//' `
	SSID=`nvconf get 1 wireless.ap.ssid`
	echo "bSSID = $bSSID"
	echo "SSID = $SSID"
	if [ "$bSSID" = "$SSID" ]; then
		NSSID=${SSID}${WIFIMAC}
		sed -i "s/^ssid.*$/ssid=$NSSID/" /customer/wifi/$HOSTAPD.conf
		nvconf set 1 wireless.ap.ssid $NSSID
		nvconf set 1 devinfo.macaddr `cat /sys/class/net/wlan0/address`
	else
		sed -i "s/^ssid.*$/ssid=$SSID/" /customer/wifi/$HOSTAPD.conf
	fi
	PSK="`nvconf get 1 wireless.ap.wpa.psk`"
	sed -i "s/^wpa_passphrase.*$/wpa_passphrase=$PSK/" /customer/wifi/$HOSTAPD.conf
	hostapd /customer/wifi/$HOSTAPD.conf -B
	#run_goahead.sh
;;
  stop)
	echo " Kill all process of AP Mode"
	busybox killall udhcpd
	busybox killall hostapd
	#busybox killall goahead
	ifconfig wlan0 down
	#rmmod $WIFI_MODULE
;;
  restart)
	echo " restart AP Mode"
	busybox killall udhcpd
	busybox killall hostapd
	#busybox killall goahead
	ifconfig wlan0 down
	sleep 1

	IPADDR="`nvconf get 1 wireless.ap.ipaddr`"
	SUBNETMASK="`nvconf get 1 wireless.ap.subnetmask`"
	sleep 1
	ifconfig wlan0 up
	ifconfig wlan0 $IPADDR netmask $SUBNETMASK
	sleep 1
	/usr/sbin/udhcpd -S /customer/wifi/udhcpd-ap.conf &

	WIFIMAC="`cat /sys/class/net/wlan0/address | /usr/bin/awk -F ":" '{print $4$5$6}`"
	bSSID=`cat /customer/wifi/net_config.bin|grep wireless.ap.ssid|sed 's/^[[:print:]]\{17\}//'|sed 's/[[:print:]]\{2\}$//' `
	SSID=`nvconf get 1 wireless.ap.ssid`
	if [ "$bSSID" = "$SSID" ]; then
		NSSID=${SSID}${WIFIMAC}
		sed -i "s/^ssid.*$/ssid=$NSSID/" /customer/wifi/$HOSTAPD.conf
		nvconf set 1 wireless.ap.ssid $NSSID
		nvconf set 1 devinfo.macaddr `cat /sys/class/net/wlan0/address`
	else
		sed -i "s/^ssid.*$/ssid=$SSID/" /customer/wifi/$HOSTAPD.conf
	fi
	PSK="`nvconf get 1 wireless.ap.wpa.psk`"
	sed -i "s/^wpa_passphrase.*$/wpa_passphrase=$PSK/" /customer/wifi/$HOSTAPD.conf
	hostapd /customer/wifi/$HOSTAPD.conf -B
	#run_goahead.sh

;;
  *)
	echo "Usage: $0 {start|stop|restart}"
	exit 1
esac

exit $?

