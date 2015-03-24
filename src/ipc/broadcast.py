"""Broadcasts the analysed data to be displayed in the interface."""
import numpy
import ipc

evt = None
data_conf = {}

def init_data(title, **kwds):
    """Configures the data broadcast named title. All the keyword=value
    pairs given will be set in the configuration dictionary for that broadcast,
    which are then available at the interface."""
    if(title in data_conf.keys()):
        data_conf[title].update(kwds)
    else:
        data_conf[title] = kwds
    if(ipc.mpi.is_slave()):
        ipc.mpi.send('__data_conf__', data_conf)

def _check_type(title, data_y):
    """Make sure that the given broadcast already has the data_type set.
    If not set it appropriately."""
    if(title not in data_conf):
        data_conf[title] = {}
    if('data_type' not in data_conf[title]):
        if(isinstance(data_y, numpy.ndarray)):
            if(len(data_y.shape) == 1):
                data_conf[title]['data_type'] = 'vector'
            elif(len(data_y.shape) == 2):
                data_conf[title]['data_type'] = 'image'
            else:
                raise ValueError(("%dD data not supported; shape=%s" %
                                  (len(data_y.shape), data_y.shape)))

        else:
            data_conf[title]['data_type'] = 'scalar'
        if(ipc.mpi.is_slave()):
            ipc.mpi.send('__data_conf__', data_conf)

def set_data(title, data_y, data_x=None):
    """Send a stream of data, which should erase and replace
    any existing values at the interface. I think it's currently
    unused so maybe should be removed."""
    _check_type(title, data_y)
    if(ipc.mpi.is_slave()):
        ipc.mpi.send(title, [ipc.uuid, 'set_data', title, data_y, data_x])
    else:
        ipc.zmq().send(title, [ipc.uuid, 'set_data', title, data_y, data_x])

def new_data(title, data_y, data_x=None, **kwds):
    """Send a new data item, which will be appended to any existing
    values at the interface. All keywords pairs given will also be
    transmitted and available at the interface."""
    _check_type(title, data_y)
    if(data_x is None):
        data_x = ipc.broadcast.evt.event_id()
    if(ipc.mpi.is_slave()):
        if(reduce):
            ipc.mpi.send_reduce(title, 'new_data', data_y, data_x, **kwds)
        else:
            ipc.mpi.send(title, [ipc.uuid, 'new_data', title, data_y,
                                 data_x, kwds])
    else:
        ipc.zmq().send(title, [ipc.uuid, 'new_data', title, data_y,
                               data_x, kwds])

def set_current_event(_evt):
    """Updates the current event, such that it can
    be accessed easily in analysis code"""
    ipc.broadcast.evt = _evt
