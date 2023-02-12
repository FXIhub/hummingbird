# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Broadcasts the analysed data to be displayed in the interface."""
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import hashlib
import logging
import numpy

from . import mpi as ipc_mpi


evt = None
data_conf = {}
sent_time = {}


def init_data(title, **kwds):
    """Configures the data broadcast named title. All the keyword=value
    pairs given will be set in the configuration dictionary for that broadcast,
    which are then available at the interface."""
    if(title in data_conf.keys()):
        data_conf[title].update(kwds)
    else:
        logging.debug("Initializing source '%s.'" % title)
        data_conf[title] = kwds
    if(ipc_mpi.is_slave()):
        ipc_mpi.send('__data_conf__', data_conf)

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
        if(ipc_mpi.is_slave()):
            ipc_mpi.send('__data_conf__', data_conf)

def new_data(title, data_y, mpi_reduce=False, **kwds):
    """Send a new data item, which will be appended to any existing
    values at the interface. If mpi_reduce is True data_y will be
    summed over all the slaves. All keywords pairs given will also be
    transmitted and available at the interface."""
    from .zmqserver import ipc_uuid, get_zmq_server as ipc_zmq
    from . import influx as ipc_influx

    global sent_time
    _check_type(title, data_y)
    event_id = evt.event_id()

    # If send_rate is given limit the send rate to it
    if 'send_rate' in kwds and kwds['send_rate'] is not None:
        send_rate = float(kwds['send_rate']) / ipc_mpi.nr_workers()
        cur_time = event_id
        if title in sent_time:
            send_probability = (cur_time-sent_time[title])*send_rate
        else:
            send_probability = 1
        sent_time[title] = cur_time
        if numpy.random.random() > send_probability:
            # do not send the data
            return

    if(ipc_mpi.is_slave()):
        if(mpi_reduce):
            ipc_mpi.send_reduce(title, 'new_data', data_y, event_id, **kwds)
        else:
            m = hashlib.md5()
            m.update(title.encode('UTF-8'))
            if m.digest() in ipc_mpi.subscribed:
                ipc_mpi.send(title, [ipc_uuid, 'new_data', title, data_y,
                                     event_id, kwds])
            else:
                logging.debug('%s not subscribed, not sending' % (title))
    else:
        ipc_zmq().send(title, [ipc_uuid, 'new_data', title, data_y,
                               event_id, kwds])
        logging.debug("Sending data on source '%s'" % title)
    if data_conf[title]["data_type"] == "scalar":
        ipc_influx.write(title, data_y, event_id, kwds)
        

def set_current_event(_evt):
    """Updates the current event, such that it can
    be accessed easily in analysis code"""
    global evt
    evt = _evt
