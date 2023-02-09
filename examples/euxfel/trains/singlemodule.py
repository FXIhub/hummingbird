"""
For testing the trains-based EuXFEL backend, start the karabo server:

./karabo-bridge-server-sim -d AGIPDModule -r 1234

from the karabo-bridge (https://github.com/European-XFEL/karabo-bridge-py)
and then start the Hummingbird backend:

./hummingbird.py -b examples/euxfel/trains/singlemodule.py
"""
from hummingbird import ananlysis, ipc, plotting
from hummingbird.backend import add_record

state = {}
state['Facility'] = 'EuXFEL'
state['EventIsTrain'] = True
state['EuXFEL/DataSource'] = 'tcp://127.0.0.1:1234'
state['EuXFEL/DataFormat'] = 'Raw'
state['EuXFEL/SlowSource'] = 'tcp://127.0.0.1:1234'
state['EuXFEL/SelModule'] = 0 
state['EuXFEL/MaxTrainAge'] = 4
state['EuXFEL/FirstCell'] = 1
state['EuXFEL/LastCell'] = 100
state['EuXFEL/BadCells'] = [18+i*32 for i in range((state['EuXFEL/LastCell']+18)//32)]

def onEvent(evt):

    #analysis.event.printKeys(evt)
    analysis.event.printNativeKeys(evt)

    print(evt['photonPixelDetectors']['AGIPD'].data.shape)

    # Timestamp
    T = evt["eventID"]["Timestamp"]
    
    # Nr. of pulses per train
    npulses = len(T.timestamp)
    analysis.event.printProcessingRate(pulses_per_event=npulses)
    print("%d pulses per train" %(npulses))
    print("Bad cells: ", T.badCells)

    # Read data/gain from AGIPD source
    agipd_data = evt['photonPixelDetectors']['AGIPD'].data[0]
    agipd_gain = evt['photonPixelDetectors']['AGIPD'].data[1]
    agipd_train = add_record(evt['analysis'], 'analysis', 'AGIPD/train', agipd_data)

    # Do hitfinding on a full train
    analysis.hitfinding.countLitPixels(evt, agipd_train, aduThreshold=0, hitscoreThreshold=0, stack=True)
    hittrain = evt['analysis']['litpixel: isHit'].data

    # Select pulses from the AGIPD train that are hits
    agipd_hits = agipd_train.data[...,hittrain]

    # Hitrate
    analysis.hitfinding.hitrate(evt, hittrain)
    if ipc.mpi.is_main_worker():
        print("The current hit rate is %.2f %%" %evt['analysis']['hitrate'].data)
    
    # Iterate through the hits
    max_hits = 10 # The maximum number of hits to be selected from each train
    for i in range(len(agipd_hits[:max_hits])):
        agipd_pulse = add_record(evt['analysis'], 'analysis', 'AGIPD', agipd_hits[...,i])
        plotting.image.plotImage(agipd_pulse)
    print("")
