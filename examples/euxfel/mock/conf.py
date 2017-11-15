state = {}
state['Facility'] = 'euxfel'

dark = 0.
event_number = 0

def onEvent(evt):
    global dark, event_number
    dark  += evt['photonPixelDetectors']['AGIPD1'].data
    event_number += 1
