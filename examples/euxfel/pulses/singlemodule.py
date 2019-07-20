"""
For testing the EuXFEL backend, start the karabo server:

./karabo-bridge-server-sim -d AGIPDModule -r 1234

from the karabo-bridge (https://github.com/European-XFEL/karabo-bridge-py)
and then start the Hummingbird backend:

./hummingbird.py -b examples/euxfel/pulses/singlemodule.py
"""
import plotting.image
import analysis.agipd
import analysis.event
from backend import add_record

state = {}
state['Facility'] = 'EuXFEL'
state['EventIsTrain'] = False
state['EuXFEL/DataSource'] = 'tcp://127.0.0.1:1234'
state['EuXFEL/DataFormat'] = 'Raw'
state['EuXFEL/SlowSource'] = 'tcp://127.0.0.1:1234'
state['EuXFEL/SelModule'] = 0 
state['EuXFEL/MaxTrainAge'] = 4
state['EuXFEL/FirstCell'] = 1
state['EuXFEL/LastCell'] = 100
state['EuXFEL/BadCells'] = [18+i*32 for i in range((state['EuXFEL/LastCell']+18)//32)]
state['EuXFEL/SkipNrPulses'] = 0

def onEvent(evt):

    #analysis.event.printKeys(evt)
    #analysis.event.printNativeKeys(evt)
    analysis.event.printProcessingRate()
    print(evt['photonPixelDetectors']['AGIPD'].data.shape)

    # Timestamp
    T = evt["eventID"]["Timestamp"]
    print(T.cellId)

    # Read data/gain from AGIPD source
    agipd_pulse = evt['photonPixelDetectors']['AGIPD'].data[0]
    agipd_gain   = evt['photonPixelDetectors']['AGIPD'].data[1]

    agipd_module = add_record(evt['analysis'], 'analysis', 'AGIPD', agipd_pulse)
    plotting.image.plotImage(agipd_module)
