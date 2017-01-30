#!/bin/zsh

outfolder=/var/acqu/bl1camp/Chapman_2016/DAQ/
#outfolder=./
bunch=FLASH.FEL/TIMER/EXP1/MACRO_PULSE_NUMBER/VAL
pulse_energy=TTF2.FEL/BKR.FLASH.STATE/BKR.FLASH.STATE/SLOW.INTENSITY/VAL
lambda=TTF2.DAQ/ENERGY.DOGLEG/LAMBDA_MEAN/VAL

while true
do
	datestr=`date +%Y-%m-%d-%H`
	doocsget -d 2 -l 100 -s 0.02 -c "$bunch $lambda $pulse_energy"|awk '{print $1,$2,$3,$4}' >> ${outfolder}/daq-${datestr}.txt
done
