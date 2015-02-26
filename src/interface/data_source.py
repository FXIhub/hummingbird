from Qt import QtGui, QtCore
from zmq import SUB, REQ, ssh
import zmq
import signal
from zmqsocket import ZmqSocket
from time import sleep

class DataSource(QtCore.QObject):
    def __init__(self, parent, hostname, port, ssh_tunnel = None):
        QtCore.QObject.__init__(self, parent)
        self._hostname = hostname
        self._port = port
        self._ssh_tunnel = ssh_tunnel
        self.connected = False
        try:            
            self.connect()
            self.connected = True
            self.get_data_port()
            self.keys = None
            self.data_type = None
        except (RuntimeError, zmq.error.ZMQError):
            QtGui.QMessageBox.warning(self.parent(), "Connection failed!", "Could not connect to %s" % self.name())
            raise
    def subscribe(self, key):
        self._data_socket.subscribe(bytes(key))
    def unsubscribe(self, key):
        self._data_socket.unsubscribe(bytes(key))
    def name(self):
        if(self._ssh_tunnel):
            return '%s (%s)' % (self._hostname, self._ssh_tunnel)
        else:
            return self._hostname
    def connect(self):
        self._ctrl_socket = ZmqSocket(REQ)
        addr = "tcp://%s:%d" % (self._hostname, self._port)
        self._ctrl_socket.readyRead.connect(self._get_command_reply)
        self._ctrl_socket.connect(addr, self._ssh_tunnel)
    def get_data_port(self):
        self._ctrl_socket.send_multipart(['data_port'])
    def get_uuid(self):
        self._ctrl_socket.send_multipart(['uuid'])
    def query_keys_and_type(self):
        self._ctrl_socket.send_multipart(['keys'])

    def _get_command_reply(self):
        socket=self.sender()
        reply = socket.recv_multipart()
        if(reply[0] == 'data_port'):
            self._data_port = reply[1]
            self._data_socket = ZmqSocket(SUB)
            addr = "tcp://%s:%s" % (self._hostname, self._data_port)
            self._data_socket.readyRead.connect(self.parent()._get_broadcast)
            self._data_socket.connect(addr, self._ssh_tunnel)
            self.parent().add_backend_to_menu(self)
            self.get_uuid()
        elif(reply[0] == 'uuid'):
            self.uuid = reply[1]
            self.query_keys_and_type()
        elif(reply[0] == 'keys'):
            reply.pop(0)
            self.keys = reply[:len(reply)/2]
            self.data_type = {}
            for k,t in zip(self.keys,reply[len(reply)/2:]):                
                self.data_type[k] = t






