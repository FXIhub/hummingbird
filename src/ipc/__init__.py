from zmqserver import ZmqServer
from uuid import uuid4
import socket

server = None
hostname = socket.gethostname()
uuid = uuid4()

def init_IPC():
    global server
    server = ZmqServer()
