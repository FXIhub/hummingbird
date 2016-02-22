import analysis.event
import plotting.image
import h5py

state = {}
state['Facility'] = 'LCLS'
state['LCLS/DataSource'] = 'exp=amo15010:dir=/path/to/xtc/:run=73'

dark = 0.
event_number = 0

def onEvent(evt):

    global dark, event_number
    dark  += evt['photonPixelDetectors']['pnccdBackfullFrame'].data
    event_number += 1

def end_of_run():
    print "Saving average dark image to dark_run73.h5"
    with h5py.File('dark_run73.h5', 'w') as f:
        f['mean']  = dark  / event_number
