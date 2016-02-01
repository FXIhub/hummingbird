#!/bin/env python
import os

cmd = "export RUN=151; bsub -q psnehq -o ~/programs/hummingbird/bsub$RUN.out /reg/neh/home/hantke/programs/hummingbird/examples/save_camera/brun.py $RUN"

print cmd
os.system(cmd)
