# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Allows the backend and analysis to run in parallel using MPI."""
import ipc
import numpy
import numbers
import logging
import time

reducedata = {}
slavesdone = []

def is_master():
    """Returns True if the process has MPI rank 0 and
    there are multiple processes."""
    return rank == 0 and size > 1

def is_zmqserver():
    """Returns True if the process has MPI rank 0, which
    is always the worker hosting the zmq server."""
    return rank == 0

def nr_workers():
    """Returns nr. of available workers."""
    return (size - 1) if (size > 1) else size

def get_source(sources):
    """Returns source based on a given list of sources and 
    given the rank of the current process. Slaves are distributed equally 
    across available data sources."""
    return sources[rank % len(sources)]
        
try:
    # Try to import MPI and create a group containing all the slaves
    from mpi4py import MPI

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    slave_group = comm.Get_group().Incl(range(1, size))
    slaves_comm = comm.Create(slave_group)
    reload_comm = comm.Clone()

    MPI_TAG_INIT   = 1 + 4353
    MPI_TAG_EXPAND = 2 + 4353
    MPI_TAG_READY  = 3 + 4353
    MPI_TAG_CLOSE  = 4 + 4353

except ImportError:
    rank = 0
    size = 1
    comm = None
    slaves_comm = None
    reload_comm = None

subscribed = set()

def slave_rank():
    if size > 1:
        return rank -1
    else:
        return 0

def is_slave():
    """Returns True if the process has MPI rank > 0."""
    return rank > 0

def is_main_slave():
    """Returns True if the process has MPI rank == 1."""
    return rank == 1

def is_main_worker():
    """Returns True if the process is the main slave or there is only one process."""
    return is_main_slave() or size == 1

def send(title, data):
    """Send a list of data items to the master node."""
    comm.send([title, data], 0)

def checkreload():
    global subscribed

    if ipc.zmq() is not None:
        if ipc.zmq().reloadmaster == True:
            ipc.zmq().reloadmaster = False
            if reload_comm is not None:
                for i in xrange(1,size):
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

def master_loop():
    """Run the main loop on the master process.
    It retransmits all received messages using its zmqserver
    and handles any possible reductions."""
    status = MPI.Status()
    msg = comm.recv(None, MPI.ANY_SOURCE, status = status)
    if(msg[0] == '__data_conf__'):
        ipc.broadcast.data_conf.update(msg[1])
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
        logging.warning("Slave with rank = %d reports to be done" %msg[1])
        if len(slavesdone) == nr_workers():
            MPI.Finalize()
            return True
    else:
        # Inject a proper UUID
        msg[1][0] = ipc.uuid
        ipc.zmq().send(msg[0], msg[1])

def send_reduce(title, cmd, data_y, data_x, **kwds):
    """Reduce data and send it to the master. Not currently used, maybe
    should be removed."""
    # Need an MPI barrier here on the slaves side
    # Otherwise the main_slave can block the master
    # while other slaves are sending data
    # DO NOT USE ME
    print "DO NOT USE send_reduce"
    slaves_comm.Barrier()
    if(is_main_slave()):
        # Alert master for the reduction
        if(isinstance(data_y, numbers.Number)):
            comm.send(['__reduce__', title, cmd, (), data_x, kwds, data_y], 0)
        else:
            comm.send(['__reduce__', title, cmd, data_y.shape, data_x, kwds, data_y], 0)

def sum(cmd, array):
    """Element-wise sum of a numpy array across all the slave processes.
    The result is only available in the main_slave (rank 1)."""
    #_reduce(array, "SUM")
    if(isinstance(array, numbers.Number)):
        comm.send(['__reduce__', cmd, (), array, is_main_slave()], 0)
    else:
        comm.send(['__reduce__', cmd, array.shape, array, is_main_slave()], 0)
    
    if not is_main_slave():
        return None

    databack = comm.recv(None, 0)
    if(isinstance(databack, numbers.Number)):
        array[()] = databack
    else:
        array[:] = databack[:]
    

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

def slave_done():
    send('__exit__', rank)
