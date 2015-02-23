import zmq
import pickle
from zmq.eventloop import ioloop, zmqstream
import threading

class ZmqServer(object):
    def __init__(self):
        self._zmq_key = bytes('hummingbird')
        self._context = zmq.Context()
        self._data_socket = self._context.socket(zmq.PUB)
        self._data_socket.bind("tcp://*:5555")
        ioloop.install()
        self._ctrl_socket = self._context.socket(zmq.REP)
        self._ctrl_socket.bind("tcp://*:5554")
        self._ctrl_stream = zmqstream.ZMQStream(self._ctrl_socket)
        self._ctrl_stream.on_recv_stream(self.get_command)
        t = threading.Thread(target=self.ioloop)
        # Make sure the program exists even when the thread exists
        t.daemon = True
        t.start()

    def send(self, data):
        self._data_socket.send_multipart([self._zmq_key,pickle.dumps(data)])

    def get_command(self, stream, msg):
        print msg
        stream.send_multipart(msg)

    def ioloop(self):
        ioloop.IOLoop.instance().start()
        print "ioloop ended"
                
