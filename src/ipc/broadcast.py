import ipc


# We should probably define a schedule to transmit things, instead of doing it all the time

def set_data(data, title, unit=None):
    ipc.zmq().send([ipc.uuid, 'set_data', title, data])

def new_data(data, title, unit=None):
    ipc.zmq().send([ipc.uuid, 'new_data', title, data])
