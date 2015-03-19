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
        self._subscribed_titles = {}
        self._data_socket = ZmqSocket(SUB,self)
        try:            
            self.connect()
            self.connected = True
            self.get_data_port()
            self.titles = None
            self.data_type = None
        except (RuntimeError, zmq.error.ZMQError):
            QtGui.QMessageBox.warning(self.parent(), "Connection failed!", "Could not connect to %s" % self.name())
            raise
    def subscribe(self, title, plot):
        if title not in self._subscribed_titles:
            self._subscribed_titles[title] = [plot]
            try:
                self._data_socket.subscribe(bytes(title))
            # socket might still not exist
            except AttributeError:
                pass
        else:
            self._subscribed_titles[title].append(plot)
    def unsubscribe(self, title, plot):
        self._subscribed_titles[title].remove(plot)
        # Check if list is empty
        if not self._subscribed_titles[title]:
            self._data_socket.unsubscribe(bytes(title))
            self._subscribed_titles.pop(title)

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
    def query_configuration(self):
        self._ctrl_socket.send_multipart(['conf'])        
    def _get_command_reply(self, socket = None):
        if(socket is None):
            socket=self.sender()
        reply = socket.recv_json()
        if(reply[0] == 'data_port'):
            self._data_port = reply[1]
            addr = "tcp://%s:%s" % (self._hostname, self._data_port)
            self._data_socket.readyRead.connect(self._get_broadcast)
            self._data_socket.connect_socket(addr, self._ssh_tunnel)
            self.parent().add_backend(self)
            # Subscribe to stuff already requested
            for title in self._subscribed_titles.keys():
                self._data_socket.subscribe(bytes(title))
            self.query_configuration()
        elif(reply[0] == 'conf'):
            self.conf = reply[1]
            self.titles = self.conf.keys()
            self.data_type = {}
            for k in self.titles:
                self.data_type[k] = self.conf[k]['data_type']
                self._plotdata[k] = PlotData(self, k)

    def _get_broadcast(self):
        socket = self.sender()
        socket.blockSignals(True)
        QtCore.QCoreApplication.processEvents()
        socket.blockSignals(False)

        title = socket.recv()
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
        self._plotdata[title].set_data(data)

    def plot_append(self, title, data, data_x):
        self._plotdata[title].append(data, data_x)
