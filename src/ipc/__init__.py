from zmqserver import ZmqServer
from uuid import uuid4
import socket

_server = None
hostname = socket.gethostname()
uuid = None

def zmq():
    global _server
    if(_server is None):
        _server = ZmqServer()
    return _server
    

from broadcast import set_data, new_data, set_current_event
