"""Handles the communication between the backend<->interface, as well
as the MPI communication between different backend processes."""
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import socket

from . import broadcast, influx, mpi
from .broadcast import (new_data,  # pylint: disable=unused-import
                        set_current_event)
from .zmqserver import ZmqServer

_server = None
hostname = socket.gethostname()
port = None
uuid = None

def zmq():
    """Returns the ZmqServer for process.
    If it does not yet exist create one first."""
    global _server # pylint: disable=global-statement
    global port # pylint: disable=global-statement
    if(_server is None and mpi.is_zmqserver()):
        _server = ZmqServer(port)
    return _server
