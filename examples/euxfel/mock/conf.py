import plotting.image

state = {}
state['Facility'] = 'euxfel'
state['socket'] = 'tcp://127.0.0.1:4501'

dark = 0.
event_number = 0

def onEvent(evt):
    global dark, event_number
    print("Available keys: " + str(evt.keys()))
    print(evt['photonPixelDetectors']['AGIPD1'].data.shape)
    dark  += evt['photonPixelDetectors']['AGIPD1'].data
    print(event_number)
    event_number += 1

    plotting.image.plotImage(evt['photonPixelDetectors']['AGIPD1'])
