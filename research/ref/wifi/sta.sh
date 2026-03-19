#!/bin/sh

case "$1" in
	start)
	echo "Launch Wifi module STA Mode..."

	if [ "`lsmod|grep $WIFI_MODULE`" == "" ]; then
		if [ "$WIFI_MODULE" == "bcmdhd" ]; then
			echo "TODO::wifi module is $WIFI_MODULE"
			#HOSTAPD="hostapd_ap6256"
			#insmod /customer/modules/4.9.84/bcmdhd.ko firmware_path=/customer/wifi/fw_bcm43456c5_ag_apsta.bin nvram_path=/customer/wifi/nvram_ap6256.txt
		else
			echo "wifi modu1e is $WIFI_MODULE"
			insmod /customer/wifi/lib/$WIFI_MODULE.ko        
		fi
	fi

	sleep 1
	
	if [ $? -eq 1 ]; then
		exit 1
	fi

	SSID="`nvconf get 1 wireless.sta.ssid`"
	sed -i "s/^.*ssid.*$/    ssid=\"$SSID\"/" /customer/wifi/wpa_supplicant.conf
	PSK="`nvconf get 1 wireless.sta.wpa.psk`"
	sed -i "s/^.*psk.*$/    psk=\"$PSK\"/" /customer/wifi/wpa_supplicant.conf

	ifconfig wlan0 up
	wpa_supplicant -Dnl80211 -iwlan0 -c /customer/wifi/wpa_supplicant.conf -B
	#udhcpc -iwlan0 -b
	#static ip
	#IPADDR="`nvconf get 1 wireless.ap.ipaddr`"
	#SUBNETMASK="`nvconf get 1 wireless.ap.subnetmask`"
	#ifconfig wlan0 $IPADDR netmask $SUBNETMASK
	udhcpc -i wlan0 -T 1 -A 1 -s /etc/init.d/udhcpc.script
	staipaddr="`ifconfig wlan0 | grep 'inet' | sed 's/^.*addr://g' | sed 's/Bcast:.*$//g'`"
	echo $staipaddr
	nvconf set 1 wireless.sta.ipaddr $staipaddr
	run_goahead.sh
    ;;
    stop)
	echo " Kill all process of STA Mode"
	busybox killall udhcpc
	busybox killall wpa_supplicant
	busybox killall goahead
	ifconfig wlan0 down
	#rmmod $WIFI_MODULE
    ;;
    *)
	echo "Usage: $0 {start|stop|restart}"
	exit 1
esac

