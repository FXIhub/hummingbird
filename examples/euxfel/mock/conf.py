import plotting.image
import analysis.agipd

state = {}
state['Facility'] = 'euxfel'
state['socket'] = 'tcp://127.0.0.1:4501'

dark = 0.
event_number = 0

def onEvent(evt):
    global dark, event_number
    print("Available keys: " + str(evt.keys()))
    print(evt['photonPixelDetectors']['AGIPD1'].data.shape)
    agipd_0 = analysis.agipd.get_panel(evt, evt['photonPixelDetectors']['AGIPD1'], 0)
    dark  += agipd_0.data
    print(event_number)
    event_number += 1

    plotting.image.plotImage(agipd_0)
