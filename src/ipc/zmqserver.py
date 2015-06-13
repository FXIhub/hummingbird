"""Implements the server that broadcasts the results from the backend.
Analysis users do not need to deal with it."""
import zmq
import zmq.eventloop
import zmq.eventloop.zmqstream
import threading
import ipc
import numpy
import hashlib
import ipc.mpi

class ZmqServer(object):
    """Implements the server that broadcasts the results from the backend.
    Analysis users do not need to deal with it."""
    def __init__(self):
        self._zmq_key = bytes('hummingbird')
        self._context = zmq.Context()
        self._data_socket = self._context.socket(zmq.PUB)
        self._data_port = 13132
        self._data_socket.setsockopt(zmq.SNDHWM, 10)
        self._data_socket.bind("tcp://*:%d" % (self._data_port))
        zmq.eventloop.ioloop.install()
        self._ctrl_socket = self._context.socket(zmq.REP)
        self._ctrl_socket.bind("tcp://*:13131")
        self._ctrl_stream = zmq.eventloop.zmqstream.ZMQStream(self._ctrl_socket)
        self._ctrl_stream.on_recv_stream(self._answer_command)
        ipc.uuid = ipc.hostname+':'+str(self._data_port)
        t = threading.Thread(target=self._ioloop)
        # Make sure the program exists even when the thread exists
        t.daemon = True
        self.reloadmaster = False
        t.start()


    def _send_array(self, array, flags=0, copy=True, track=False):
        """Send a numpy array with metadata"""
        md = dict(
            dtype=str(array.dtype),
            shape=array.shape,
            strides=array.strides,
        )
        self._data_socket.send_json(md, flags|zmq.SNDMORE)
        return self._data_socket.send(array, flags, copy=copy, track=track)

    def send(self, title, data):
        """Send a list of data items to the broadcast named title"""
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
        m.update(bytes(title))
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
    
    def checksignaltime(self):
        if self.reloadmaster:
            import os, signal
            self.reloadmaster = False
            with open('.pid', 'r') as file:
                pid = int(file.read())
            os.kill(pid, signal.SIGUSR1)

    def _answer_command(self, stream, msg):
        """Reply to commands received on the _ctrl_stream"""
        if(msg[0] == 'conf'):
            stream.socket.send_json(['conf', ipc.broadcast.data_conf])
        if(msg[0] == 'data_port'):
            stream.socket.send_json(['data_port', bytes(self._data_port)])
        if(msg[0] == 'uuid'):
            stream.socket.send_json(['uuid', bytes(ipc.uuid)])
        if(msg[0] == 'reload'):
            #TODO: Find a way to replace this with a direct function call (in all workers)
            stream.socket.send_json(['reload', bytes(True)])
            print "Answering reload command"
            self.reloadmaster = True
            
    def _ioloop(self):
        """Start the ioloop fires the callbacks when data is received
        on the control stream. Runs on a separate thread."""
        zmq.eventloop.ioloop.IOLoop.instance().start()
        print "ioloop ended"
