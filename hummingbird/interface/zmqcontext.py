#!/usr/bin/env python
# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""
PyZeroMQt - zmqsocket.py: Provides a singleton wrapper for a ZeroMQ context
"""
from zmq import Context


class ZmqContext(object):
    """Provides a singleton wrapper for a ZeroMQ context"""
    self_ = None
    def __init__(self, iothreads):
        assert not ZmqContext.self_
        self._context = Context(iothreads)

    def __del__(self):
        self._context.term()

    def socket(self, socket_type):
        """Creates and returns a socket of the given type"""
        return self._context.socket(socket_type)

    @staticmethod
    def instance(iothreads=4):
        """Returns the singleton instance of the ZeroMQ context"""
        if not ZmqContext.self_:
            ZmqContext.self_ = ZmqContext(iothreads)
        return ZmqContext.self_
