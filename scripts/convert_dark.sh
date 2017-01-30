#!/bin/zsh

while true
do
	for f in /var/acqu/bl1camp/Chapman_2016/CCD_Calib/*.darkcal
	do 
		if [ ! -e ${f}.h5 ]
		then 
			echo Converting $f
			python src/backend/convert_darkcal.py $f -o ${f}.h5
		fi
	done
	sleep 10
done
