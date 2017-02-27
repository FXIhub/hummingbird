#!/usr/bin/env python
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys

runnr = int(sys.argv[1])
filename = '/asap3/flash/gpfs/bl1/2017/data/11001733/processed/hummingbird/r%04d_ol1.h5' %runnr
with h5py.File(filename, 'r') as f:
    hitscore = f['entry_1/result_1/hitscore_litpixel'][:]

fig = plt.figure()
ax  = fig.add_subplot(111)
ax.plot(hitscore, 'k.')
ax.axhline(int(sys.argv[2]))
fig.savefig('../plots/r%04d_hitscore.png' %runnr, dpi=100, bbox_inches='tight')
