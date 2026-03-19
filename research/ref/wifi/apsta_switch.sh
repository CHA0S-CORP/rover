#!/bin/sh

APSTA=`nvconf get 1 wireless.apstaswitch`

if [ $APSTA = "STA" ]; then
	echo "STA switch AP mode."
	nvconf set 1 wireless.apstaswitch AP
	sta.sh stop
	busybox killall goahead
	sleep 1
	ap.sh start &
else
	echo "AP switch STA mode."
	nvconf set 1 wireless.apstaswitch STA
	ap.sh stop
	busybox killall goahead
	sleep 1
	sta.sh start &
fi

