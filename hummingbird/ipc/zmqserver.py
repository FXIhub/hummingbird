# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Implements the server that broadcasts the results from the backend.
Analysis users do not need to deal with it."""
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import hashlib
import logging
import socket
import threading

import numpy
import tornado.ioloop
import zmq
import zmq.eventloop
import zmq.eventloop.zmqstream

from . import mpi as ipc_mpi
from hummingbird.utils.cmdline_args import argparser as _argparser

eventLimit = 125

# `IOLoop.current()` returns a thread local `IOLoop`. So we need this 
# global variable to tell the thread the correct `IOLoop` to start.
ioloop = tornado.ioloop.IOLoop.current()


class ZmqServer(object):
    """Implements the server that broadcasts the results from the backend.
    Analysis users do not need to deal with it."""
    def __init__(self, port):
        self._subscribed = set()
        self.reloadmaster = False
        
        self._batch_mode = bool(_argparser.parse_args().batch_mode)
        if self._batch_mode:
            return

        from hummingbird.backend import Worker
        self._state = Worker.state
        #self._zmq_key = bytes('hummingbird')
        self._context = zmq.Context()
        self._ctrl_socket = self._context.socket(zmq.REP)
        self._ctrl_port = self._state.get('zmq_ctrl_port', port)
        self._broker_pub_socket = self._context.socket(zmq.XPUB)
        self._broker_pub_port = self._state.get('zmq_data_port',
                                                self._ctrl_port+1)
        self._broker_sub_socket = self._context.socket(zmq.XSUB)
        self._broker_sub_port = self._state.get('zmq_xsub_port', 
                                                self._broker_pub_port+1)

        self._data_socket = self._context.socket(zmq.PUB)
        ## Does not match intent according to http://stackoverflow.com/questions/23800442/why-wont-zmq-drop-messages
        self._broker_sub_socket.setsockopt(zmq.RCVHWM, eventLimit)
        self._broker_pub_socket.setsockopt(zmq.SNDHWM, eventLimit)
        self._broker_pub_socket.setsockopt(zmq.SNDTIMEO, 0)
        self._data_socket.setsockopt(zmq.SNDHWM, eventLimit)
        self._data_socket.setsockopt(zmq.SNDTIMEO, 0)
        self._ctrl_socket.bind("tcp://*:%d" % (self._ctrl_port))
        self._broker_pub_socket.bind("tcp://*:%d" % (self._broker_pub_port))
        self._broker_sub_socket.bind("tcp://*:%d" % (self._broker_sub_port))
        self._data_socket.connect("tcp://127.0.0.1:%d" % (self._broker_sub_port))

        # We are installing event handlers for those sockets
        # but also for data stream, since a PUB socket actually
        # can leak data if it never is asked to process its events.
        # (According to some vague discussions.)
        # (e.g. https://github.com/zeromq/libzmq/issues/1256 )
        self._data_stream = zmq.eventloop.zmqstream.ZMQStream(self._data_socket)
        self._ctrl_stream = zmq.eventloop.zmqstream.ZMQStream(self._ctrl_socket)
        self._ctrl_stream.on_recv_stream(self._answer_command)

        self._xpub_stream = zmq.eventloop.zmqstream.ZMQStream(self._broker_pub_socket)
        self._xpub_stream.on_recv_stream(self._forward_xpub)

        self._xsub_stream = zmq.eventloop.zmqstream.ZMQStream(self._broker_sub_socket)
        self._xsub_stream.on_recv_stream(self._forward_xsub)

        ipc_uuid = ipc_hostname+':'+str(self._broker_pub_port)
        t = threading.Thread(target=self._ioloop)
        # Make sure the program exists even when the thread exists
        t.daemon = True
        t.start()

    def _send_array(self, array, flags=0, copy=True, track=False):
        """Send a numpy array with metadata"""
        md = dict(
            dtype=str(array.dtype),
            shape=array.shape,
            strides=array.strides,
        )
        if md['dtype'] == 'object':
            raise ValueError('Cannot broadcast arrays with dtype=object')
        self._data_socket.send_json(md, flags|zmq.SNDMORE)
        return self._data_socket.send(array, flags, copy=copy, track=track)

    def send(self, title, data):
        """Send a list of data items to the broadcast named title"""
        if self._batch_mode:
            return
        array_list = []
        for i in range(len(data)):
            if(isinstance(data[i], numpy.ndarray)):
                array_list.append(data[i])
                data[i] = '__ndarray__'
            elif(isinstance(data[i], numpy.number)):
                # JSON can't deal with numpy scalars
                data[i] = data[i].item()
        # Use the md5sum of the title as the key to avoid clashing
        # keys, when one title is a substring or another title
        # (e.g. "CCD" and "CCD1")
        m = hashlib.md5()
        m.update(title.encode('UTF-8'))
        self._data_socket.send(m.digest(), zmq.SNDMORE)
        if(len(array_list)):
            self._data_socket.send_json(data, zmq.SNDMORE)
        else:
            self._data_socket.send_json(data)
        for i in range(len(array_list)):
            if(i != len(array_list)-1):
                self._send_array(array_list[i], flags=zmq.SNDMORE)
            else:
                self._send_array(array_list[i])
    
    def _answer_command(self, stream, msg):
        """Reply to commands received on the _ctrl_stream"""
        if(msg[0] == 'conf'.encode('UTF-8')):
            from .broadcast import data_conf as ipc_broadcast_data_conf
            stream.socket.send_json(['conf', ipc_broadcast_data_conf])
        if(msg[0] == 'data_port'.encode('UTF-8')):
            stream.socket.send_json(['data_port', self._broker_pub_port])
        if(msg[0] == 'uuid'):
            stream.socket.send_json(['uuid', ipc_uuid])
        if(msg[0] == 'reload'.encode('UTF-8')):
            #TODO: Find a way to replace this with a direct function call (in all workers)
            stream.socket.send_json(['reload', True])
            print("Answering reload command")
            self.reloadmaster = True
            
    def _ioloop(self):
        """Start the ioloop fires the callbacks when data is received
        on the control stream. Runs on a separate thread."""
        ioloop.start()
        print("ioloop ended")

    def _forward_xsub(self, stream, msg):
        self._xpub_stream.send_multipart(msg)

    def _forward_xpub(self, stream, msg):
        if (msg[0][0] == '\x00') or (msg[0][0] == 0):
            logging.debug("Got unsubscription for: %r" % msg[0][1:])
            self._subscribed.discard(msg[0][1:])
        elif (msg[0][0] == '\x01') or (msg[0][0] == 1):
            logging.debug("Got subscription for: %r" % msg[0][1:])
            self._subscribed.add(msg[0][1:])
        else:
            raise ValueError('Unexpected message: %r' % msg[0])
        if ipc_mpi.is_master():
            for i in range(1, ipc.mpi_size):
                ipc_mpi.reload_comm.send(['__subscribed__',self._subscribed], i)
        self._xsub_stream.send_multipart(msg)

    @property
    def subscribed(self):
        return self._subscribed


_server = None
ipc_hostname = socket.gethostname()
ipc_port = None
ipc_uuid = None


def get_zmq_server():
    """Returns the ZmqServer for process.
    If it does not yet exist create one first."""
    global _server # pylint: disable=global-statement
    global ipc_port # pylint: disable=global-statement
    if(_server is None and ipc_mpi.is_zmqserver()):
        _server = ZmqServer(ipc_port)
    return _server
