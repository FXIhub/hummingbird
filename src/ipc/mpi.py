import ipc
import numpy
import numbers

def is_master():
    return rank == 0 and size > 1

try:
    from mpi4py import MPI

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    slave_group = comm.Get_group().Incl(range(1,size))
    slaves_comm = comm.Create(slave_group)
except ImportError:
    rank = 0
    size = 1
    comm = None


def is_slave():
    return rank > 0

def is_main_slave():
    return rank == 1

def send(title, data):
    comm.send([title, data], 0)

def master_loop():
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
        ipc.zmq().send(msg[0],msg[1])

def send_reduce(title, cmd, data_y, data_x, **kwds):
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
    
