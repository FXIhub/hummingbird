#!/bin/env python
import os, sys

run = sys.argv[1]

hummingbird_dir = "/reg/neh/home/hantke/programs/hummingbird"
this_dir = os.path.dirname(os.path.realpath(__file__))

os.system("source /reg/neh/home/hantke/.bashrc; export HUMMINGBIRD_RUN=%s; cd %s; ./hummingbird.py -b %s/conf.py" % (run, hummingbird_dir, this_dir))
