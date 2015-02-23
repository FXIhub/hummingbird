import ipc

_evt_counter = 0
_evt = None

data_titles = []
# We should probably define a schedule to transmit things, instead of doing it all the time

def set_data(title, data_y, data_x = None, unit=None):
    global data_titles
    if(title not in data_titles):
        data_titles.append(title)
    ipc.zmq().send(title, [ipc.uuid, 'set_data', title, data_y])

def new_data(title, data_y, data_x = None, unit=None):
    global data_titles
    if(title not in data_titles):
        data_titles.append(title)

    if(data_x is None):
        data_x = [_evt.id()]
    ipc.zmq().send(title, [ipc.uuid, 'new_data', title, data_y, data_x])


def set_current_event(evt):
    global _evt
    global _evt_counter
    _evt = evt
    _evt_counter += 1    
