#!/usr/bin/env python
import sys
sys.path.append("/home/tekeberg/Source/pah/")
import numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot
from camp.pah.beamtimedaqaccess import BeamtimeDaqAccess

#root_directory_of_h5_files = "/asap3/flash/gpfs/bl1/2017/data/11001733/raw/hdf/block-03"
root_directory_of_h5_files = "/data/beamline/current/raw/hdf/block-03"
daq= BeamtimeDaqAccess.create(root_directory_of_h5_files)

# Define DAQ channel names
#tunnelEnergyChannelName= "/Photon Diagnostic/GMD/Average energy/energy tunnel (raw)"
bda_energy_channel_name = "/Photon Diagnostic/GMD/Pulse resolved energy/energy BDA"

# All TOF values of a run
tofChannelName= "/Experiment/BL1/ADQ412 GHz ADC/CH00/TD"

#runNumber = [16174,16175,16176,16177,16178,16179,16180,16181,16182]
runNumber = [16197,16196,16195,16199,16194,16198,16192,16191,16190] + range(16183,16190)
scan_distance = [-1900,-1700,-1500,-1400,-1300,-1200,-1100,-900,-700,-500,-300,-100,0,100,300,500]

gmd_gate = [(80, 85)] * len(runNumber)
#gmd_gate = [(90, 95)] * len(runNumber)
#gmd_gate = [(88.5, 92.5)] * len(runNumber)

#position_gate = [(2.26, 2.31), (2.32, 2.39), (2.73, 2.84)]
#position_gate = [(2.04, 2.06), (2.08, 2.10), (2.12, 2.14),
#                 (2.16, 2.19), (2.199, 2.25), (2.26, 2.31), (2.32, 2.379), (2.393, 2.455),
#                 (2.482, 2.545), (2.597, 2.667), (2.73, 2.84)]
position_gate = [(1.94,1.962), (1.90, 1.925), (1.86, 1.887), (1.835,1.854), (1.81,1.825)]

all_tof = []
all_idInterval = []
for rn  in runNumber:
    print("read run {0}".format(rn))
    tofSpectra0, idInterval0 = daq.allValuesOfRun(tofChannelName, rn)
    all_tof.append(tofSpectra0 * 0.8 / 2048.) # convert to V
    all_idInterval.append(idInterval0)


all_gmd = []
for id_interval in all_idInterval:
    try:
        bdaEnergy= daq.valuesOfInterval(bda_energy_channel_name, id_interval)
        gmd_values = bdaEnergy[:, 0]
        all_gmd.append(gmd_values)
    except:
        all_tof = all_tof[:len(all_gmd)]
        scan_distance = scan_distance[:len(all_gmd)]
        print "Stopping after {0} gmd reads at run {1}".format(len(all_gmd), runNumber[len(all_gmd)])
        break

average_tof = []
tof_x = numpy.arange(20000) * 10. / 20000.
integral_plots = [[] for _ in range(len(position_gate))]
for index in range(len(all_tof)):
    print index, ((all_gmd[index] > gmd_gate[index][0]) * (all_gmd[index] < gmd_gate[index][1])).sum()
    average_tof.append(all_tof[index][(all_gmd[index] > gmd_gate[index][0]) * (all_gmd[index] < gmd_gate[index][1]), :].mean(axis=0))
    for window_index, g in enumerate(position_gate[:len(all_tof)]):
        #print window_index, g[0], g[1]
        integral_plots[window_index].append(average_tof[-1][(tof_x > g[0]) * (tof_x < g[1])].sum())


fig = matplotlib.pyplot.figure(1)
fig.clear()
ax = fig.add_subplot(111)
for i, p in enumerate(integral_plots):
    #print scan_distance[:-1], p[:-1]
    #try:
    ax.plot(scan_distance[:-1], p[:-1], label="{0} - {1}".format(position_gate[i][0], position_gate[i][1]))
    #except:
    #    pass
#for i, p in enumerate(integral_plots):
    #try:
#    ax.plot([scan_distance[19]], [p[-1]], "o", color=ax.lines[i].get_color())
    #except:
    #    pass
fig.savefig('../plots/figure1.png', bbox_inches='tight')


fig2 = matplotlib.pyplot.figure(2)
fig2.clear()
ax2 = fig2.add_subplot(111)
for i, this_average_tof in enumerate(average_tof):
    ax2.plot(tof_x, this_average_tof + 0.04*i, color="black")
    ax2.set_xlim((1.5, 3.5))
    ax2.text(3.5, 0.04*i, '%d' %scan_distance[i], ha='right')
ylim = ax2.get_ylim()
ax2.set_yticks([])
ax2.spines['right'].set_visible(False)
ax2.spines['top'].set_visible(False)
ax2.xaxis.set_ticks_position('bottom')
ax2.set_xlabel('Time')
for i, g in enumerate(position_gate):
    ax2.add_patch(matplotlib.patches.Rectangle((g[0], ylim[0]), g[1]-g[0], ylim[1] - ylim[0], color="lightgray"))
ax2.set_ylim(ylim)
fig2.savefig('../plots/tof_%d_%d_%d_%d.pdf' %(runNumber[0], runNumber[-1], gmd_gate[0][0], gmd_gate[0][1]), bbox_inches='tight')
matplotlib.pyplot.show()

