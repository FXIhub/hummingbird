import ipc
import numpy

def plot(data, title, unit=None):
    ipc.server.send([ipc.uuid, 'plot', title, data])
