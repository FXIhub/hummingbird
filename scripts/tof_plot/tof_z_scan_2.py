import numpy
import matplotlib
import matplotlib.pyplot
from camp.pah.beamtimedaqaccess import BeamtimeDaqAccess


root_directory_of_h5_files = "/data/beamline/current/raw/hdf/block-03"
daq= BeamtimeDaqAccess.create(root_directory_of_h5_files)

# Define DAQ channel names
#tunnelEnergyChannelName= "/Photon Diagnostic/GMD/Average energy/energy tunnel (raw)"
bda_energy_channel_name = "/Photon Diagnostic/GMD/Pulse resolved energy/energy BDA"


# All TOF values of a run
tofChannelName= "/Experiment/BL1/ADQ412 GHz ADC/CH00/TD"

#data_points = [(16197, -600), (16198, -500), (16199, -700)]
# data_points = [(16174, -500), (16175, -300), (16176, -200), (16177, -100), (16178, -000),
#                (16179, 100), (16180, 200), (16181, 300), (16182, 500), (16183, -500)]

#run_number = [(16198), 16113]
#run_number = [16200, 16200]

name_700="700"
name_750="750"
name_1000="1000"
name_new_750="new 750"

data_points_new_750 = [(16231, 900), (16232, 000)]

data_points_700 = [(16222, -500), (16223, -300), (16224, -100), (16225, 100), (16226, 300),
                   (16227, 300), (16228, 500), (16229, 700), (16230, 900)]
data_points_750 = [(16201, -2000), (16202, -1500), (16203, -1000), (16204, -500), (16205, 0),
                   (16206, 500), (16207, 1000), (16209, 2000), (16210, 1500)]
data_points_1000 = [(16211, -500), (16212, -300), (16213, -100), (16214, 100), (16215, 300),
                    (16216, 500), (16217, 700), (16218, 900), (16219, 1100), (16220, 1300),
                    (16221, 1500)]

# name = name_700
# data_points = data_points_700[:-2]
# name = name_750
# data_points = data_points_750[:]
# name = name_1000
# data_points = data_points_1000[:]
name = name_new_750
data_points = data_points_new_750[:]


position_gate_750 = [(2.325, 2.394), (2.260, 2.311), (2.209, 2.250), (2.162, 2.200), (2.117, 2.148), (2.080, 2.105)]
position_gate_1000 = [(2.171, 2.219), (2.122, 2.152), (2.085, 2.115), (2.040, 2.067), (2.005, 2.025), (1.969, 1.991)]
position_gate = position_gate_1000

#scan_distance = -500. + 100.*numpy.arange(len(run_number))

run_number, scan_distance = zip(*data_points)

#gmd_gate = [(80, 85), (80, 85), (80, 85), (80, 85), (80, 85), (80, 85), (80, 85)]
#gmd_gate = [(80, 85)] * len(run_number)
gmd_gate = [(80, 85)] * len(run_number)
#gmd_gate = [(20, 150)] * len(run_number)

#position_gate = [(2.26, 2.31), (2.32, 2.39), (2.73, 2.84)]
# position_gate = [(2.04, 2.06), (2.08, 2.10), (2.12, 2.14),
#                  (2.16, 2.19), (2.199, 2.25), (2.26, 2.31), (2.32, 2.379), (2.393, 2.455),
#                  (2.482, 2.545), (2.597, 2.667), (2.73, 2.84)]

#position_gate = [(1.271, 1.390), (1.65, 6.0)]

tof_offset = 1750.
#tof_offset = 0.

all_tof = []
all_id_interval = []
for rn  in run_number:
    print("read run {0}".format(rn))
    tof_spectra0, id_interval0 = daq.allValuesOfRun(tofChannelName, rn)
    all_tof.append((tof_spectra0 - tof_offset) * 0.8 / 2048.) # convert to V
    all_id_interval.append(id_interval0)

all_gmd = []
for id_interval in all_id_interval:
    try:
        bdaEnergy= daq.valuesOfInterval(bda_energy_channel_name, id_interval)
        gmd_values = bdaEnergy[:, 0]
        all_gmd.append(gmd_values)
    except:
        all_tof = all_tof[:len(all_gmd)]
        scan_distance = scan_distance[:len(all_gmd)]
        print "Stopping after {0} gmd reads at run {1}".format(len(all_gmd), run_number[len(all_gmd)]-1)
        break

scan_distance, run_number, all_tof, all_gmd = zip(*sorted(zip(scan_distance, run_number, all_tof, all_gmd)))


average_tof = []
tof_x = numpy.arange(20000) * 10. / 20000.
integral_plots = [[] for _ in range(len(position_gate))]
for index in range(len(all_tof)):
    weak = (all_gmd[index] > gmd_gate[index][0]) * (all_gmd[index] < gmd_gate[index][1])
    ok_tof = all_tof[index].sum(axis=1) > - 10000.
    average_tof.append(all_tof[index][weak*ok_tof, :].mean(axis=0))
    for window_index, g in enumerate(position_gate):
        integral_plots[window_index].append(average_tof[-1][(tof_x > g[0]) * (tof_x < g[1])].sum())


# Plot window integrals
fig1 = matplotlib.pyplot.figure(name+" waterfal")
fig1.clear()
ax = fig1.add_subplot(111)
for i, p in enumerate(integral_plots):
    ax.plot(scan_distance, p, label="{0} - {1}".format(position_gate[i][0], position_gate[i][1]))
#ax1 = fig1.add_subplot(211)
# ax1.plot(scan_distance, integral_plots[0], 'o', color="black", markersize=10)
# # ax1.set_title("Photon peak")
# ax2 = fig1.add_subplot(212)
# ax2.plot(scan_distance, integral_plots[1], 'o', color="black", markersize=10)
# # ax2.set_title("The rest")
#ax.legend()
fig1.canvas.draw()
    
# Plot waterfall
xlimits = (0, 6.)
waterfall_offset = 0.05
#waterfall_offset = 0.0
#fig2 = matplotlib.pyplot.figure(2)
fig2 = matplotlib.pyplot.figure(name+" window integral")
fig2.clear()
ax2 = fig2.add_subplot(111)
for i, this_average_tof in enumerate(average_tof):
    color = "black"
    # if run_number[i] == 16227:
    #     color = "blue"
    ax2.plot(tof_x, this_average_tof + waterfall_offset*i, color=color)
    #print("add text at {
    ax2.text(1.9, this_average_tof[-1] + waterfall_offset*i, str(scan_distance[i]), verticalalignment="bottom", horizontalalignment="right")
ax2.set_xlim(xlimits)
ylim = ax2.get_ylim()
for i, g in enumerate(position_gate):
    ax2.add_patch(matplotlib.patches.Rectangle((g[0], ylim[0]), g[1]-g[0], ylim[1] - ylim[0], color="whitesmoke"))

ax2.set_ylim(ylim)

fig2.canvas.draw()
