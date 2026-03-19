#!/bin/sh
#IPADDR=`ifconfig wlan0 | head -n 2 |tail -n 1 |cut -d':' -f 2 | cut -d ' ' -f 1`
APSTA=`nvconf get 1 wireless.apstaswitch`
if [ $APSTA = "STA" ]; then
	IPADDR="`nvconf get 1 wireless.sta.ipaddr`"
else
	IPADDR="`nvconf get 1 wireless.ap.ipaddr`"
fi

sync
echo 1 > /proc/sys/vm/drop_caches


if [ "`pidof goahead`" = "" ]; then
echo "Start Goahead ..."
#goahead -v  --home /var/webserver/conf/ /var/webserver/www $IPADDR:80 &
#DIR PATH sync to route.txt
goahead -v  --home /customer/wifi/webserver/conf/ /customer/wifi/webserver/www $IPADDR:80&
fi

#sync
#echo 1 > /proc/sys/vm/drop_caches

sleep 1

