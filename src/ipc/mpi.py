import ipc

try:
    from mpi4py import MPI

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
except ImportError:
    rank = 0
    size = 1
    comm = None

def is_master():
    return rank == 0 and size > 1

def is_slave():
    return rank > 0

def send(title, data):
    comm.send([title, data], 0)

def master_loop():
    msg = comm.recv(None, MPI.ANY_SOURCE)
    if(msg[0] == '__data_conf__'):
        ipc.broadcast.data_conf.update(msg[1])
    else:
        # Inject a proper UUID
        msg[1][0] = ipc.uuid
        ipc.zmq().send(msg[0],msg[1])
