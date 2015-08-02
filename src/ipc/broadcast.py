"""Broadcasts the analysed data to be displayed in the interface."""
import numpy
import ipc
import logging

evt = None
data_conf = {}

def init_data(title, **kwds):
    """Configures the data broadcast named title. All the keyword=value
    pairs given will be set in the configuration dictionary for that broadcast,
    which are then available at the interface."""
    if(title in data_conf.keys()):
        data_conf[title].update(kwds)
    else:
        logging.debug("Initializing source '%s.'" % title)
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
            # Special handling for data plots
            if(len(data_y.shape) == 1) or (len(data_y.shape) == 2 and data_y.shape[0] == 2):
                data_conf[title]['data_type'] = 'vector'
            # Images with more longer first dimension
            elif(len(data_y.shape) == 2):
                data_conf[title]['data_type'] = 'image'
            else:
                raise ValueError(("%dD data not supported; shape=%s" %
                                  (len(data_y.shape), data_y.shape)))

        else:
            data_conf[title]['data_type'] = 'scalar'
        if(ipc.mpi.is_slave()):
            ipc.mpi.send('__data_conf__', data_conf)

def new_data(title, data_y, mpi_reduce=False, **kwds):
    """Send a new data item, which will be appended to any existing
    values at the interface. If mpi_reduce is True data_y will be
    summed over all the slaves. All keywords pairs given will also be
    transmitted and available at the interface."""
    _check_type(title, data_y)
    event_id = evt.event_id()
    if(ipc.mpi.is_slave()):
        if(mpi_reduce):
            ipc.mpi.send_reduce(title, 'new_data', data_y, event_id, **kwds)
        else:
            ipc.mpi.send(title, [ipc.uuid, 'new_data', title, data_y,
                                 event_id, kwds])
    else:
        ipc.zmq().send(title, [ipc.uuid, 'new_data', title, data_y,
                               event_id, kwds])
        logging.debug("Sending data on source '%s'" % title)
        
def set_current_event(_evt):
    """Updates the current event, such that it can
    be accessed easily in analysis code"""
    ipc.broadcast.evt = _evt


