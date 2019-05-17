"""
For testing the EuXFEL backend, start the karabo server:

./karabo-bridge-server-sim 1234

from the karabo-bridge (https://github.com/European-XFEL/karabo-bridge-py).
and then start the Hummingbird backend:

./hummingbird.py -b examples/euxfel/mock/conf.py
"""
import plotting.image
import analysis.agipd
import analysis.event
from backend import add_record

state = {}
state['Facility'] = 'EuXFEL'
state['EuXFEL/DataSource'] = 'tcp://127.0.0.1:1234'
state['EuXFEL/DataFormat'] = 'Calib'
state['EuXFEL/RecvTrains'] = True
state['EuXFEL/SkipPulses'] = 0

event_number = 0
def onEvent(evt):
    global event_number
    #analysis.event.printKeys(evt)
    #analysis.event.printNativeKeys(evt)
    analysis.event.printProcessingRate()
    T = evt["eventID"]["Timestamp"]
    #print(event_number, T.timestamp, T.pulseId, T.cellId, T.trainId)
    agipd_module_8 = evt['photonPixelDetectors']['AGIPD'].data[8]
    agipd_gain = evt['photonPixelDetectors']['AGIPD'].data[-1]
    agipd_0 = add_record(evt['analysis'], 'analysis', 'AGIPD', agipd_module_8)
    plotting.image.plotImage(agipd_0)
    event_number += 1
