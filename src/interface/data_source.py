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
        self._subscribed_keys = {}
        try:            
            self.connect()
            self.connected = True
            self.get_data_port()
            self.keys = None
            self.data_type = None
        except (RuntimeError, zmq.error.ZMQError):
            QtGui.QMessageBox.warning(self.parent(), "Connection failed!", "Could not connect to %s" % self.name())
            raise
    def subscribe(self, key, plot):
        if key not in self._subscribed_keys:
            self._subscribed_keys[key] = [plot]
            try:
                self._data_socket.subscribe(bytes(key))
            # socket might still not exist
            except AttributeError:
                pass
        else:
            self._subscribed_keys[key].append(plot)
    def unsubscribe(self, key, plot):
        self._subscribed_keys[key].remove(plot)
        # Check if list is empty
        if not self._subscribed_keys[key]:
            self._data_socket.unsubscribe(bytes(key))
            self._subscribed_keys.pop(key)

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
            # Subscribe to stuff already requested
            for key in self._subscribed_keys.keys():
                self._data_socket.subscribe(bytes(key))
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

        key = socket.recv()
        data = socket.recv_json()
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
            self.plot(title,data, source)

        if(cmd == 'new_data'):
            title = payload[2]
            data = payload[3]
            data_x = payload[4]
            conf = payload[5]
            self.conf[title].update(conf)
            self.plot_append(title,data,data_x)

    def plot(self, title, data):
        if(title not in self._plotdata):
            self._plotdata[title] = PlotData(self, title)
        self._plotdata[title].set_data(data)

    def plot_append(self, title, data, data_x):
        if(title not in self._plotdata):
            self._plotdata[title] = PlotData(self, title)
        self._plotdata[title].append(data, data_x)

    def get_plot_data(self, title):
        if(title in self._plotdata):
            return self._plotdata[title]
        return None
