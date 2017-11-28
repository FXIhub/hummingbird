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
#runNumber = [16111, 16113]
runNumber = [16115, 16116, 16117, 16118, 16120, 16121, 16122, 16123, 16124, 16125,
             16126, 16127, 16128, 16129, 16130, 16131, 16132, 16133, 16134, 16135,
             16136, 16137]
data_points_1000 = [(16211, -500), (16212, -300), (16213, -100), (16214, 100), (16215, 300),
                    (16216, 500), (16217, 700), (16218, 900), (16219, 1100), (16220, 1300),
                    (16221, 1500)]
runNumber = [d[0] for d in data_points_1000]



all_tof = []
all_idInterval = []
for rn  in runNumber:
    print "reading run {0}".format(rn)
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
        print "Stopping after {0} gmd reads".format(len(all_gmd))
        break


# all_gmd = []
# for id_interval in all_idInterval:
#     bdaEnergy= daq.valuesOfInterval(bda_energy_channel_name, id_interval)
#     gmd_values = bdaEnergy[:, 0]
#     all_gmd.append(gmd_values)


plot_grid = (4, 6)
fig = matplotlib.pyplot.figure(5)
fig.clear()
for i, gmd in enumerate(all_gmd):
    ax = fig.add_subplot(plot_grid[0], plot_grid[1], i+1)
    ax.set_title("Run {0}".format(runNumber[i]))
    ax.hist(gmd, bins=20, range=(25, 140))

fig.canvas.draw()
