#!/usr/bin/env python
import h5py, sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors

runnr = int(sys.argv[1])
filename = '../data/r%04d_ol3.h5' %runnr

with h5py.File(filename, 'r') as f:
    data = f['entry_1/data_1/data'][:]
    mask = (f['entry_1/data_1/mask'][:] != 512)

nframes = data.shape[0]
print "Nr. of frames: ", nframes
average = data.astype(np.float64).sum(axis=0)
average[average<500] = 1.

fig = plt.figure()
ax  = fig.add_subplot(111)
ax.set_title('Run = %04d, Nframes = %d' %(runnr, nframes))
ax.set_xticks([])
ax.set_yticks([])
im = ax.imshow(average*mask, norm=colors.LogNorm(vmin=2e3, vmax=5e5), cmap='magma', interpolation='none')
cb = fig.colorbar(im)
cb.ax.set_ylabel('Intensity [ADU]')
fig.savefig('../plots/r%04d_average.png' %(runnr), dpi=300, bbox_inches='tight')

