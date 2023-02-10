# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Allows the backend and analysis to run in parallel using MPI."""
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import logging
import numbers
import sys
import time

import numpy


try:
    # Try to import MPI and create a group containing all the slaves
    from mpi4py import MPI
    # Only use MPI if there is more than one process
    use_mpi = MPI.COMM_WORLD.Get_size() > 1
except ImportError:
    use_mpi = False

if use_mpi:
    # World communicator
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    # Other communicators
    slaves_group = comm.Get_group().Incl(range(1, size))
    slaves_comm = comm.Create(slaves_group)
    reload_comm = comm.Clone()
    # These communicators will be initialised after reading the configuration file
    event_reader_group = None
    event_reader_comm = None
    logging.debug('Initiailsed for MPI operation mode (size = %i, rank = %i).' % (size, rank))
else:
    # World communicator
    comm = None
    rank = 0
    size = 1
    # Other communicators
    slaves_group = None
    slaves_comm = None
    reload_comm = None
    event_reader_group = None
    event_reader_comm = None
    logging.debug('Initialised for serial operation mode.')

# MASTER PROCESS

def is_master():
    """Returns True if the process has MPI rank 0 and
    there are multiple processes."""
    return rank == 0 and size > 1

# SLAVE PROCESSES
    
def is_slave():
    """Returns True if the process has MPI rank > 0."""
    return rank > 0

def nr_slaves():
    """Returns number of slaves"""
    return 0 if not use_mpi else slaves_group.size

def slave_rank():
    return None if not use_mpi else slaves_group.rank

def is_main_slave():
    """Returns True if the process has MPI rank == 1."""
    return rank == 1

def is_main_worker():
    """Returns True if the process is the main slave or there is only one process."""
    return is_main_slave() or size == 1

# WORKERS

def is_worker():
    """Returns True if the process is a slave or there is only one process."""
    return use_mpi or is_slave()

def nr_workers():
    """Returns nr. of available workers."""
    return 1 if not use_mpi else slaves_group.size

def worker_index():
    return 0 if not use_mpi else slave_rank()
    
# EVENT READERS

def init_event_reader_comm(slave_event_reader_min_rank):
    if not use_mpi:
        return
    if slaves_group.size == 1 and slave_event_reader_min_rank > 0:
        logging.error('Cannot reduce the number of event readers because there is only one.')
        sys.exit(1)
    global event_reader_group
    global event_reader_comm
    if slave_event_reader_min_rank > 0:
        # Reduce event_reader_comm
        event_reader_group = comm.Get_group().Incl(range(1+slave_event_reader_min_rank, comm.size))
    else:
        event_reader_group = comm.Get_group().Incl(range(1+0, comm.size))
    event_reader_comm = comm.Create(event_reader_group)

def is_event_reader():
    """Returns True if the process is an event reader."""
    if use_mpi and event_reader_comm is None:
        logging.warning('Event reader communicator not initialised yet!')
        return None
    return True if not use_mpi else (event_reader_group.rank != MPI.UNDEFINED)
        
def is_main_event_reader():
    """Returns True if the process has rank == 0 in the reader communicator or if there is only one process."""
    if use_mpi and event_reader_comm is None:
        logging.warning('Event reader communicator not initialised yet!')
        return None
    return True if not use_mpi else (event_reader_group.rank == 0)
    
def nr_event_readers():
    """Returns nr. of event readers i.e. processes that run an event loop."""
    if use_mpi and event_reader_comm is None:
        logging.warning('Event reader communicator not initialised yet!')
        return None
    return 1 if not use_mpi else event_reader_group.size
        
def event_reader_rank():
    if use_mpi and event_reader_comm is None:
        logging.warning('Event reader communicator not initialised yet!')
    if not use_mpi:
        return 0
    else:
        if event_reader_group.rank == MPI.UNDEFINED:
            logging.warning('Cannot determine event reader rank for process that is not part of the event reader communicator.')
            return None
        else:
            return event_reader_group.rank

# SOURCES
        
def get_source(sources):
    """Returns source based on a given list of sources and 
    given the rank of the current process. Slaves are distributed equally 
    across available data sources."""
    return sources[rank % len(sources)]

# ZMQ SERVER

def is_zmqserver():
    """Returns True if the process has MPI rank 0, which
    is always the worker hosting the zmq server."""
    return rank == 0


# COMMUNICATIONS

def send(title, data):
    """Send a list of data items to the master node."""
    if comm is not None:
        comm.send([title, data], 0)

# RELOADING OF CONFIGURATION FILE

subscribed = set()
def checkreload():
    from .zmqserver import get_zmq_server as ipc_zmq
    global subscribed

    if ipc_zmq() is not None:
        if ipc_zmq().reloadmaster == True:
            ipc_zmq().reloadmaster = False
            if reload_comm is not None:
                for i in range(1,size):
                    reload_comm.send(['__reload__'], i)
            return True
    if is_slave():
        if reload_comm.Iprobe():
            msg = reload_comm.recv()
            if(msg[0] == '__reload__'):
                logging.debug('Got reload')
                return True
            elif(msg[0] == '__subscribed__'):
                logging.debug('Got subscribed %s' % msg[1])
                subscribed = msg[1]
    return False

# MASTER LOOP

reducedata = {}
slavesdone = []
def master_loop():
    """Run the main loop on the master process.
    It retransmits all received messages using its zmqserver
    and handles any possible reductions."""
    status = MPI.Status()
    msg = comm.recv(None, MPI.ANY_SOURCE, status = status)
    if(msg[0] == '__data_conf__'):
        from .broadcast import data_conf as ipc_broadcast_data_conf
        ipc_broadcast_data_conf.update(msg[1])
    elif(msg[0] == '__reduce__'):
        cmd = msg[1]
        if(msg[2] != ()):
            data_y = numpy.zeros(msg[1])
        else:
            data_y = 0
        incomingdata = msg[3]
        getback = msg[4]
        
        source = status.Get_source()
        
        # This indicates that we really should have an object for the state
        if cmd not in reducedata:
            reducedata[cmd] = {}
        reducedata[cmd][source] = incomingdata
        
        if getback:
            cnt = 0
            for data in reducedata[cmd]:
                data_y = data_y + reducedata[cmd][data]
            comm.send(data_y, source)
    elif(msg[0] == '__exit__'):
        slavesdone.append(True)
        logging.info("Slave with rank = %d reports to be done" %msg[1])
        if len(slavesdone) == nr_slaves():
            MPI.Finalize()
            return True
    else:
        # Inject a proper UUID
        from .zmqserver import get_zmq_server as ipc_zmq, ipc_uuid
        msg[1][0] = ipc_uuid
        ipc_zmq().send(msg[0], msg[1])

def slave_done():
    send('__exit__', rank)
            
def sum(cmd, array):
    """Element-wise sum of a numpy array across all processes of event readers.
    The result is only available in the main event reader (rank 0 in event reader comm)."""
    #_reduce(array, "SUM")
    #return
    if not use_mpi:
        return

    getback = is_main_event_reader()
    if(isinstance(array, numbers.Number)):
        comm.send(['__reduce__', cmd, (), array, getback], dest=0)
    else:
        comm.send(['__reduce__', cmd, array.shape, array, getback], dest=0)
    
    if not getback:
        return None
    else:
        databack = comm.recv(None, 0)
        if(isinstance(databack, numbers.Number)):
            array[()] = databack
        else:
            array[:] = databack[:]
    
# WE MIGHT WANT TO DELETE THE CODE BELOW (Benedikt? Carl?)

def send_reduce(title, cmd, data_y, data_x, **kwds):
    """Reduce data and send it to the master. Not currently used, maybe
    should be removed."""
    # Need an MPI barrier here on the slaves side
    # Otherwise the main_slave can block the master
    # while other slaves are sending data
    # DO NOT USE ME
    print("DO NOT USE send_reduce")
    slaves_comm.Barrier()
    if(is_main_slave()):
        # Alert master for the reduction
        if(isinstance(data_y, numbers.Number)):
            comm.send(['__reduce__', title, cmd, (), data_x, kwds, data_y], 0)
        else:
            comm.send(['__reduce__', title, cmd, data_y.shape, data_x, kwds, data_y], 0)
            
def max(array):
    """Element-wise max of a numpy array across all the slave processes.
    The result is only available in the main_slave (rank 1)."""
    _reduce(array, "MAX")

def min(array):
    """Element-wise max of a numpy array across all the slave processes.
    The result is only available in the main_slave (rank 1)."""
    _reduce(array, "MIN")

def prod(array):
    """Element-wise product of a numpy array across all the slave processes.
    The result is only available in the main_slave (rank 1)."""
    _reduce(array, "PROD")

def logical_or(array):
    """Element-wise logical OR of a numpy array across all the slave processes.
    The result is only available in the main_slave (rank 1)."""
    _reduce(array, "LOR")

def logical_and(array):
    """Element-wise logical AND of a numpy array across all the slave processes.
    The result is only available in the main_worker()."""
    _reduce(array, "LAND")

def _reduce(array, op):
    """Reduce a numpy array with the given MPI op across all the slave processes"""
    if(not isinstance(array,numpy.ndarray)):
        raise TypeError("argument must be a numpy ndarray")
    if(slaves_comm):
        if(is_main_slave()):
            slaves_comm.Reduce(MPI.IN_PLACE, array, op=getattr(MPI,op))
        else:
            slaves_comm.Reduce(array,  None, op=getattr(MPI,op))
