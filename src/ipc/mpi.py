"""Allows the backend and analysis to run in parallel using MPI."""
import ipc
import numpy
import numbers

def is_master():
    """Returns True if the process has MPI rank 0 and
    there are multiple processes."""
    return rank == 0 and size > 1

try:
    # Try to import MPI and create a group containing all the slaves
    from mpi4py import MPI

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    slave_group = comm.Get_group().Incl(range(1, size))
    slaves_comm = comm.Create(slave_group)
except ImportError:
    rank = 0
    size = 1
    comm = None
    slaves_comm = None


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

def master_loop():
    """Run the main loop on the master process.
    It retransmits all received messages using its zmqserver
    and handles any possible reductions."""
    msg = comm.recv(None, MPI.ANY_SOURCE)
    if(msg[0] == '__data_conf__'):
        ipc.broadcast.data_conf.update(msg[1])
    elif(msg[0] == '__reduce__'):
        title = msg[1]
        cmd = msg[2]
        if(msg[3] != ()):
            data_y = numpy.zeros(msg[3])
        else:
            data_y = 0
        data_x = msg[4]
        kwds = msg[5]
        data_y = comm.reduce(data_y)
        if(isinstance(data_y, numbers.Number)):
            print "[%s] - %g" %(title, data_y)
        ipc.zmq().send(title, [ipc.uuid, cmd, title, data_y, data_x, kwds])
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
    slaves_comm.Barrier()
    if(is_main_slave()):
        # Alert master for the reduction
        if(isinstance(data_y, numbers.Number)):
            comm.send(['__reduce__', title, cmd, (), data_x, kwds], 0)
        else:
            comm.send(['__reduce__', title, cmd, data_y.shape, data_x, kwds], 0)
    comm.reduce(data_y)

def sum(array):
    """Element-wise sum of a numpy array across all the slave processes.
    The result is only available in the main_slave (rank 1)."""
    _reduce(array, "SUM")

def max(array):
    """Element-wise max of a numpy array across all the slave processes.
    The result is only available in the main_slave (rank 1)."""
    _reduce(array, "MAX")

def min(array):
    """Element-wise max of a numpy array across all the slave processes.
    The result is only available in the main_slave (rank 1)."""
    _reduce(array, "MPI.MIN")

def prod(array):
    """Element-wise product of a numpy array across all the slave processes.
    The result is only available in the main_slave (rank 1)."""
    _reduce(array, "MPI.PROD")

def logical_or(array):
    """Element-wise logical OR of a numpy array across all the slave processes.
    The result is only available in the main_slave (rank 1)."""
    _reduce(array, "MPI.LOR")

def logical_and(array):
    """Element-wise logical AND of a numpy array across all the slave processes.
    The result is only available in the main_worker()."""
    _reduce(array, "MPI.LAND")

def _reduce(array, op):
    """Reduce a numpy array with the given MPI op across all the slave processes"""
    if(not isinstance(array,numpy.ndarray)):
        raise TypeError("argument must be a numpy ndarray")
    if(slaves_comm):
        if(is_main_slave()):
            slaves_comm.Reduce(MPI.IN_PLACE, array, op=getattr(MPI,op))
        else:
            slaves_comm.Reduce(array,  None, op=op)
