state = {}
state['Facility'] = 'euxfel'

dark = 0.
event_number = 0

def onEvent(evt):
    global dark, event_number
    print "Available keys: " + str(evt.keys())
    dark  += evt['photonPixelDetectors']['AGIPD1'].data
    event_number += 1
