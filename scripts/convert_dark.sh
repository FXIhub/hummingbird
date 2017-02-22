#!/bin/zsh

while true
do
	for f in /asap3/flash/gpfs/bl1/2017/data/11001733/raw/pnccd/calib/*.darkcal
        #for f in /asap3/flash/gpfs/bl1/2017/data/11001733/scratch_cc/pnccd/calib/*.darkcal
	do 
		if [ ! -e /asap3/flash/gpfs/bl1/2017/data/11001733/processed/calib/$(basename ${f}).h5 ]
		then 
			echo Converting $f
			python src/backend/convert_darkcal.py $f -o /asap3/flash/gpfs/bl1/2017/data/11001733/processed/calib/$(basename ${f}).h5
		fi
	done
	sleep 10
done
