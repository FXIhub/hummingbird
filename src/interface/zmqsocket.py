"""
Provides a wrapper for a ZeroMQ socket. Adapted from PyZeroMQt.
"""
from Qt import QtCore
from zmqcontext import ZmqContext
from zmq import FD, LINGER, IDENTITY, SUBSCRIBE, UNSUBSCRIBE, EVENTS, \
                POLLIN, POLLOUT, POLLERR, NOBLOCK, ZMQError, EAGAIN, RCVHWM
import numpy
import hashlib

class ZmqSocket(QtCore.QObject):
    readyRead=QtCore.Signal()
    readyWrite=QtCore.Signal()
    def __init__(self, _type, parent=None, **kwargs):
        QtCore.QObject.__init__(self, parent, **kwargs)

        ctx=ZmqContext.instance()
        self._socket=ctx._context.socket(_type)
        self.setLinger(ctx.linger())

        fd=self._socket.getsockopt(FD)
        self._notifier=QtCore.QSocketNotifier(fd, QtCore.QSocketNotifier.Read, self)
        self._notifier.activated.connect(self.activity)
        self._socket.setsockopt(RCVHWM, 10)
        
    def __del__(self): self._socket.close()

    def setIdentity(self, name): self._socket.setsockopt(IDENTITY, name)

    def identity(self): return self._socket.getsockopt(IDENTITY)

    def setLinger(self, msec): self._socket.setsockopt(LINGER, msec)

    def linger(self): return self._socket.getsockopt(LINGER)

    def subscribe(self, _filter): 
        # scramble the filter to avoid spurious matches (like CCD matching CCD1)
        m = hashlib.md5()
        m.update(_filter)
        self._socket.setsockopt(SUBSCRIBE, m.digest())    

    def unsubscribe(self, _filter):
        m = hashlib.md5()
        m.update(_filter)
        self._socket.setsockopt(UNSUBSCRIBE, m.digest())

    def bind(self, addr): self._socket.bind(addr)

    def connect_socket(self, addr, tunnel=None):
        if(tunnel):
            from zmq import ssh
            ssh.tunnel_connection(self._socket, addr, tunnel)
        else:
            self._socket.connect(addr)

    def activity(self):
        self._notifier.setEnabled(False);
        while(self._socket.getsockopt(EVENTS) & POLLIN):
            self.readyRead.emit()
        self._notifier.setEnabled(True);

    def recv(self, flags=0):
        return self._socket.recv(flags)

    def recv_json(self, flags=0):
        return self._socket.recv_json(flags)

    def recv_multipart(self):
        return self._socket.recv_multipart()

    def send(self, _msg): return self._socket.send(_msg)

    def send_multipart(self, _msg): return self._socket.send_multipart(_msg)

    def recv_array(self, flags=0, copy=True, track=False):
        """recv a numpy array"""
        md = self._socket.recv_json(flags=flags)        
        msg = self._socket.recv(flags=flags, copy=copy, track=track)
        buf = buffer(msg)
        return  numpy.ndarray(shape = md['shape'], dtype=md['dtype'], buffer = buf, strides = md['strides'])
