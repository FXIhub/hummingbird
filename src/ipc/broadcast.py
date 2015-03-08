import numpy
import ipc

_evt_counter = 0
_evt = None

data_conf = {}

def init_data(title, **kwds):
    if(title in data_conf.keys()):
        data_conf[title].update(kwds)
    else:
        data_conf[title] = kwds
    if(ipc.mpi.is_slave()):
        ipc.mpi.send('__data_conf__', data_conf)

def check_type(title, data_y):
    if(title not in data_conf):
        data_conf[title] = {}
    if('data_type' not in data_conf[title]):
        if(isinstance(data_y,numpy.ndarray)):
            if(len(data_y.shape) == 1):
                data_conf[title]['data_type'] = 'vector'
            elif(len(data_y.shape) == 2):
                data_conf[title]['data_type'] = 'image'
            else:
                raise ValueError("Type %s not supported" % (type(data_y)))

        else:
            data_conf[title]['data_type'] = 'scalar'
        if(ipc.mpi.is_slave()):
            ipc.mpi.send('__data_conf__', data_conf)

def set_data(title, data_y, data_x = None, unit=None):
    check_type(title, data_y)
    if(ipc.mpi.is_slave()):
        ipc.mpi.send(title, [ipc.uuid, 'set_data', title, data_y])
    else:
        ipc.zmq().send(title, [ipc.uuid, 'set_data', title, data_y])

def new_data(title, data_y, data_x = None, unit=None, reduce=False, 
             denominator=None, **kwds):
    check_type(title, data_y)

    if(data_x is None):
        data_x = _evt.id()
    if(ipc.mpi.is_slave()):
        if(reduce):
            ipc.mpi.send_reduce(title, 'new_data', data_y, data_x, **kwds)
        else:
            ipc.mpi.send(title, [ipc.uuid, 'new_data', title, data_y, data_x, kwds])
    else:
        ipc.zmq().send(title, [ipc.uuid, 'new_data', title, data_y, data_x, kwds])



def set_current_event(evt):
    global _evt
    global _evt_counter
    _evt = evt
    _evt_counter += 1    
