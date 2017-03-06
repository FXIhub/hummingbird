#!/bin/zsh

while true
do
	for f in /data/beamline/current/raw/pnccd/block-04/darkcal/*.darkcal
        #for f in /asap3/flash/gpfs/bl1/2017/data/11001733/scratch_cc/pnccd/calib/*.darkcal
	do 
		if [ ! -e /data/beamline/current/processed/calib/block-04/$(basename ${f}).h5 ]
		then 
			echo Converting $f
			python src/backend/convert_darkcal.py $f -o /data/beamline/current/processed/calib/block-04/$(basename ${f}).h5
		fi
	done
	sleep 10
done
