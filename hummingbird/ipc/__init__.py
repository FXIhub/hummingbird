"""Handles the communication between the backend<->interface, as well
as the MPI communication between different backend processes."""
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

from . import broadcast, influx, mpi  # pylint: disable=unused-import
from .broadcast import (new_data,  # pylint: disable=unused-import
                        set_current_event)
from .zmqserver import (get_zmq_server as zmq,  # pylint: disable=unused-import
                        ipc_hostname as hostname,
                        ipc_port as port,
                        ipc_uuid as uuid)
