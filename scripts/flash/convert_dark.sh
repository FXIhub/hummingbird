#!/bin/zsh

while true
do
	for f in /gpfs/bl/current/raw/pnCCDs/*/*.darkcal
	#for f in /data/beamline/current/raw/pnccd/block-04/darkcal/*.darkcal
        #for f in /asap3/flash/gpfs/bl1/2017/data/11001733/scratch_cc/pnccd/calib/*.darkcal
	do 
		if [ ! -e /gpfs/bl/current/processed/calib/$(basename ${f}).h5 ]
		then 
			echo Converting $f
			python scripts/flash/convert_darkcal.py $f -o /gpfs/bl/current/processed/calib/$(basename ${f}).h5
			echo Done
		fi
	done
	sleep 10
done
