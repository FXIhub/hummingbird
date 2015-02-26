import zmq
import pickle
from zmq.eventloop import ioloop, zmqstream
import threading
import ipc

class ZmqServer(object):
    def __init__(self):
        self._zmq_key = bytes('hummingbird')
        self._context = zmq.Context()
        self._data_socket = self._context.socket(zmq.PUB)
        self._data_port = 13132
        self._data_socket.bind("tcp://*:%d", self._data_port)
        ioloop.install()
        self._ctrl_socket = self._context.socket(zmq.REP)
        self._ctrl_socket.bind("tcp://*:13131")
        self._ctrl_stream = zmqstream.ZMQStream(self._ctrl_socket)
        self._ctrl_stream.on_recv_stream(self.get_command)
        t = threading.Thread(target=self.ioloop)
        # Make sure the program exists even when the thread exists
        t.daemon = True
        t.start()

    def send(self, title, data):
        self._data_socket.send_multipart([bytes(title),pickle.dumps(data)])

    def get_command(self, stream, msg):
        if(msg[0] == 'keys'):
            stream.socket.send_multipart(['keys']+ipc.broadcast.data_titles)
        if(msg[0] == 'data_port'):
            stream.socket.send_multipart(['data_port',bytes(self._data_port)])

    def ioloop(self):
        ioloop.IOLoop.instance().start()
        print "ioloop ended"
                
