#!/usr/bin/env python
import sys, os, time

start_cmd = 'rsync -auve "ssh -p 2222" localhost:/home/daurerbe/holography/plots/ ~/phd-project/experiments/flash-holography-2017/plots/'
run_cmd_plots = 'rsync -auve "ssh -p 2222" daurerbe@localhost:/home/daurerbe/holography/plots/ ../plots/'
run_cmd_data  = 'rsync -auve "ssh -p 2222" daurerbe@localhost:/home/daurerbe/data/hummingbird/*_ol[1,3].h5 ../data/'

if 'start' in sys.argv:
    os.system(start_cmd)
if 'forever' in sys.argv:
    while True:
        print "Checking for new plots..."
        os.system(run_cmd_plots)
        print "Checking for new data..."
        os.system(run_cmd_data)
        print "Waiting 10 seconds ..."
        time.sleep(10)

