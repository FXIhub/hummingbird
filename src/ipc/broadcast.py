import numpy
import ipc

_evt_counter = 0
_evt = None

data_conf = {}
# We should probably define a schedule to transmit things, instead of doing it all the time

def init_data(title, **kwds):
    if(title in data_conf.keys()):
        data_conf[title].update(kwds)
    else:
        data_conf[title] = kwds

def set_data(title, data_y, data_x = None, unit=None):
    if(title not in data_conf):
        data_conf[title] = {}
    if('data_type' not in data_conf[title]):
        if(isinstance(data_y,numpy.ndarray)):
            data_conf[title]['data_type'] = 'image'
        else:
            data_conf[title]['data_type'] = 'scalar'

    ipc.zmq().send(title, [ipc.uuid, 'set_data', title, data_y])

def new_data(title, data_y, data_x = None, unit=None, **kwds):
    if(title not in data_conf):
        data_conf[title] = {}
    if('data_type' not in data_conf[title]):
        if(isinstance(data_y,numpy.ndarray)):
            data_conf[title]['data_type'] = 'image'
        else:
            data_conf[title]['data_type'] = 'scalar'

    if(data_x is None):
        data_x = _evt.id()
    ipc.zmq().send(title, [ipc.uuid, 'new_data', title, data_y, data_x, kwds])

def set_current_event(evt):
    global _evt
    global _evt_counter
    _evt = evt
    _evt_counter += 1    
