#!/bin/sh
#export PATH=$PATH:/usr/bin
export PATH=$PATH:/bin
export PATH=$PATH:/etc

# ota_upgrade value 0:Normal 1:start ota upgrade 2:end ota upgrade and remove upgrade file
echo "start ota upgrade..."
fw_setenv ota_upgrade_status 1
reboot


