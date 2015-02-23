#!/usr/bin/env python
"""
PyZeroMQt - zmqsocket.py: Provides a singleton wrapper for a ZeroMQ context
"""
from zmq import Context

class ZmqContext(object):
    self_=None
    def __init__(self, iothreads, defaultLinger):
        assert not ZmqContext.self_
        self._linger=defaultLinger
        self._context=Context(iothreads)

    def __del__(self): self._context.term()

    def majorVersion(self): return zmq.zmq_version_info()[0]

    def minorVersion(self): return zmq.zmq_version_info()[1]

    def patchVersion(self): return zmq.zmq_version_info()[2]

    def version(self): return zmq.zmq_version()

    def linger(self): return self._linger

    def setLinger(self, msec): self._linger=msec

    @staticmethod
    def instance(iothreads=4, defaultLinger=0):
        if not ZmqContext.self_: 
            ZmqContext.self_=ZmqContext(iothreads, defaultLinger)
        return ZmqContext.self_
