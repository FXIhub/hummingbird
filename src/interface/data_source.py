from Qt import QtGui, QtCore
from zmq import SUB, REQ, ssh
import zmq
import signal
from zmqsocket import ZmqSocket
from time import sleep
from plotdata import PlotData
import json

class DataSource(QtCore.QObject):
    def __init__(self, parent, hostname, port, ssh_tunnel = None):
        QtCore.QObject.__init__(self, parent)
        self._hostname = hostname
        self._port = port
        self._ssh_tunnel = ssh_tunnel
        self.connected = False
        self._plotdata = {}
        self._params = {}
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
        self._ctrl_socket.connect_socket(addr, self._ssh_tunnel)
    def get_data_port(self):
        self._ctrl_socket.send_multipart(['data_port'])
    def get_uuid(self):
        self._ctrl_socket.send_multipart(['uuid'])
    def query_keys_and_type(self):
        self._ctrl_socket.send_multipart(['keys'])
        
    def _get_command_reply(self, socket = None):
        if(socket is None):
            socket=self.sender()
        reply = socket.recv_json()
        if(reply[0] == 'data_port'):
            self._data_port = reply[1]
            self._data_socket = ZmqSocket(SUB,self)
            addr = "tcp://%s:%s" % (self._hostname, self._data_port)
            self._data_socket.readyRead.connect(self._get_broadcast)
            self._data_socket.connect_socket(addr, self._ssh_tunnel)
            self.parent().add_backend(self)
            self.get_uuid()
        elif(reply[0] == 'uuid'):
            self.uuid = reply[1]
            self.query_keys_and_type()
        elif(reply[0] == 'keys'):
            self.conf = reply[1]
            self.keys = self.conf.keys()
            self.data_type = {}
            for k in self.keys:
                self.data_type[k] = self.conf[k]['data_type']

    def _get_broadcast(self):
        socket = self.sender()
        socket.blockSignals(True)
        QtCore.QCoreApplication.processEvents()
        socket.blockSignals(False)
        parts = socket.recv_multipart()
        # The first part is a key, so we discard
        for recvd in parts[1::2]:            
            data = json.loads(recvd)
            for i in range(len(data)):
                if data[i] == '__ndarray__':
                    data[i] = socket.recv_array()

            self._process_broadcast(data)
            
    def _process_broadcast(self, payload):
        # The uuid identifies the sender uniquely        
        uuid = payload[0]
        cmd = payload[1]
        if(cmd == 'set_data'):
            title = payload[2]
            data = payload[3]
            self.plot(str(uuid),title,data, source)

        if(cmd == 'new_data'):
            title = payload[2]
            data = payload[3]
            data_x = payload[4]
            params = payload[5]
            if(title in self._params):
                self._params[title].update(params)
            else:
                self._params[title] = params
            self.plot_append(str(uuid),title,data,data_x)

    def plot(self, uuid, title, data):
        if(uuid+title not in self._plotdata):
            self._plotdata[uuid+title] = PlotData(self, title)
        self._plotdata[uuid+title].set_data(data)

    def plot_append(self, uuid, title, data, data_x):
        if(uuid+title not in self._plotdata):
            self._plotdata[uuid+title] = PlotData(self, title)
        self._plotdata[uuid+title].append(data, data_x)
