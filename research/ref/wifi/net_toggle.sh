#!/bin/sh

NETEN=`nvconf get 0 Camera.Menu.WiFi`
APSTA=`nvconf get 1 wireless.apstaswitch`

if [ $NETEN = "OFF" ]; then
	echo "wait for NET $APSTA ON."
	echo rtsp 1 > tmp/cardv_fifo
	usleep 300000
	nvconf set 0 Camera.Menu.WiFi ON
	if [ $APSTA = "STA" ]; then
		sta.sh start &
	else
		ap.sh start &
	fi
elif [ $NETEN = "ON" ]; then
	echo "wait for NET $APSTA OFF."
	echo rtsp 0 > tmp/cardv_fifo
	usleep 200000
	nvconf set 0 Camera.Menu.WiFi OFF
	if [ $APSTA = "STA" ]; then
		sta.sh stop
	else
		ap.sh stop
	fi
	busybox killall goahead
fi

