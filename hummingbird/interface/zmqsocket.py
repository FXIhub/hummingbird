# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""
Provides a wrapper for a ZeroMQ socket. Adapted from PyZeroMQt.
"""
import hashlib

import numpy
from zmq import EVENTS, FD, IDENTITY, POLLIN, RCVHWM, SUBSCRIBE, UNSUBSCRIBE

from .Qt import QtCore
from .zmqcontext import ZmqContext


class ZmqSocket(QtCore.QObject):
    """Wrapper around a zmq socket. Provides Qt signal handling"""
    ready_read = QtCore.Signal()
    ready_write = QtCore.Signal()
    def __init__(self, _type, parent=None, **kwargs):
        QtCore.QObject.__init__(self, parent, **kwargs)

        ctx = ZmqContext.instance()
        self._socket = ctx.socket(_type)

        fd = self._socket.getsockopt(FD)
        self._notifier = QtCore.QSocketNotifier(fd, QtCore.QSocketNotifier.Read, self)
        self._notifier.activated.connect(self.activity)
        self._socket.setsockopt(RCVHWM, 100)
        self.filters = []

    def __del__(self):
        """Close socket on deletion"""
        self._socket.close()

    def set_identity(self, name):
        """Set zmq socket identity"""
        self._socket.setsockopt(IDENTITY, name)

    def identity(self):
        """Return the zmq socket identity"""
        return self._socket.getsockopt(IDENTITY)

    def subscribe(self, title):
        """Subscribe to a broadcast with the given title"""
        # only subscribe if we're not already subscribed
        if title in self.filters:
            return
        # scramble the filter to avoid spurious matches (like CCD matching CCD1)        
        m = hashlib.md5()
        m.update(title.encode('UTF-8'))
        self._socket.setsockopt(SUBSCRIBE, m.digest())
        self.filters.append(title)

    def unsubscribe(self, title):
        """Unsubscribe to a broadcast with the given title"""
        m = hashlib.md5()
        m.update(title.encode('UTF-8'))
        self._socket.setsockopt(UNSUBSCRIBE, m.digest())
        self.filters.remove(title)

    def bind(self, addr):
        """Bind socket to address"""
        self._socket.bind(addr)

    def connect_socket(self, addr, tunnel=None):
        """Connect socket to endpoint, possible using an ssh tunnel
        The tunnel argument specifies the hostname of the ssh server to
        tunnel through.
        Note that this still succeeds even if there's no ZMQ server on
        the other end as the connection is asynchronous. For more details
        check the zmq_connect(3) documentation.
        """
        if(tunnel):
            from zmq import ssh
            # If there's no ssh server listening we're gonna
            # get stuck here for a long time as there's no timeout
            ssh.tunnel_connection(self._socket, addr, tunnel)
        else:            
            self._socket.connect(addr)

    def activity(self):
        """Callback run when there's activity on the socket"""
        self._notifier.setEnabled(False)
        while(self._socket.getsockopt(EVENTS) & POLLIN):
            self.ready_read.emit()
        self._notifier.setEnabled(True)

    def recv(self, flags=0):
        """Receive a message on the socket"""
        return self._socket.recv(flags)

    def recv_json(self, flags=0):
        """Receive and json decode a message on the socket"""
        return self._socket.recv_json(flags)

    def recv_multipart(self):
        """Receive a multipart message on the socket"""
        return self._socket.recv_multipart()

    def send(self, _msg):
        """Send a message on the socket"""
        return self._socket.send(_msg)

    def send_multipart(self, _msg):
        """Send a list of messages as a multipart message on the socket"""
        return self._socket.send_multipart(_msg)

    def recv_array(self, flags=0, copy=True, track=False):
        """Receive a numpy array"""
        md = self._socket.recv_json(flags=flags)
        msg = self._socket.recv(flags=flags, copy=copy, track=track)
        return  numpy.ndarray(shape=md['shape'], dtype=md['dtype'], buffer=msg, strides=md['strides'])
