#!/bin/sh
#export PATH=$PATH:/usr/bin
export PATH=$PATH:/bin
export PATH=$PATH:/etc

# inti ota_upgrade_status = 0 when system start
# ota_upgarde_statsu=1 means ota-upgrade finished, remove upgrade bin
# sleep(2000) wait for mmc ready
if [ `fw_printenv ota_upgrade_status` != "ota_upgrade_status=1" ]; then
           echo "init ota status..."
           fw_setenv ota_upgrade_status 0        
else
   if [ `fw_printenv ota_upgrade_status` = "ota_upgrade_status=1" ]; then  
           sleep 2
           echo "end ota upgrade..."
           cd /mnt/mmc/
           #ls | grep -E "IPL*|kernel|UBOOT|initramfs.gz|customer.jffs2|auto_update.txt|boot|scripts" | xargs rm -rf {SigmastarUpgradeSD.bin}
           rm -rf SigmastarUpgradeSD.bin
           fw_setenv ota_upgrade_status 0
           cd -
    fi
fi

