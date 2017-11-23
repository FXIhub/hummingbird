import plotting.image


state = {}
state['Facility'] = 'euxfel'

dark = 0.
event_number = 0

def onEvent(evt):
    global dark, event_number
    print("Available keys: " + str(evt.keys()))
    print(evt['photonPixelDetectors']['AGIPD1'].data.shape)
    dark  += evt['photonPixelDetectors']['AGIPD1'].data
    #print(evt['eventID'])
    print(event_number)
    event_number += 1

    plotting.image.plotImage(evt['photonPixelDetectors']['AGIPD1'])
