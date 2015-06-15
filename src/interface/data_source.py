"""Manages a connection with one backend"""
from interface.Qt import QtGui, QtCore
from zmq import SUB, REQ
import zmq
from interface.zmqsocket import ZmqSocket
from interface.plotdata import PlotData
import logging

class DataSource(QtCore.QObject):
    """Manages a connection with one backend"""
    plotdata_added = QtCore.Signal(PlotData)
    subscribed = QtCore.Signal(str)
    unsubscribed = QtCore.Signal(str)
    def __init__(self, parent, hostname, port, ssh_tunnel=None):
        QtCore.QObject.__init__(self, parent)
        self._hostname = hostname
        self._port = port
        self._ssh_tunnel = ssh_tunnel
        self.connected = False
        self._plotdata = {}
        self._subscribed_titles = {}
        self._recorded_titles = {}
        self._recorder = None
        self._data_socket = ZmqSocket(SUB, self)
        self.conf = {}
        try:
            self._connect()
            self.connected = True
            self._get_data_port()
            self.titles = None
            self.data_type = None
        except (RuntimeError, zmq.error.ZMQError):
            QtGui.QMessageBox.warning(self.parent(), "Connection failed!", "Could not connect to %s" % self.name())
            raise

    def subscribe(self, title, plot):
        """Subscribe to the broadcast named title, and associate it with the given plot"""
        if title not in self._subscribed_titles:
            self._subscribed_titles[title] = [plot]
            try:
                self._data_socket.subscribe(bytes(title))
                self.subscribed.emit(title)
                logging.debug("Subscribing to %s on %s.", title, self.name())
            # socket might still not exist
            except AttributeError:
                pass
        else:
            self._subscribed_titles[title].append(plot)
            
    def unsubscribe(self, title, plot):
        """Dissociate the given plot with the broadcast named title.
        If no one else is associated with it unsubscribe"""
        self._subscribed_titles[title].remove(plot)
        # Check if list is empty
        if not self._subscribed_titles[title]:
            self._data_socket.unsubscribe(bytes(title))
            self.unsubscribed.emit(title)
            logging.debug("Unsubscribing from %s on %s.", title, self.name())
            self._subscribed_titles.pop(title)

    def subscribe_for_recording(self, title):
        """Subscribe to the broadcast named title, and associate it with recorder"""
        # Only subscribe if we are not already subscribing for plotting
        if title in self._subscribed_titles:
            return
        if title not in self._recorded_titles:
            self._recorded_titles[title] = True
            try:
                self._data_socket.subscribe(bytes(title))
                self.subscribed.emit(title)
                logging.debug("Subscribing to %s on %s.", title, self.name())
            # socket might still not exist
            except AttributeError:
                pass

    def unsubscribe_for_recording(self, title):
        """Dissociate the recorder with the broadcast named title.
        If no one else is associated with it unsubscrine"""
        self._recorded_titles[title] = False
        if not title in self._subscribed_titles:
            self._data_socket.unsubscribe(bytes(title))
            self.unsubscribed.emit(title)
            logging.debug("Unsubscribing from %s on %s.", title, self.name())
            self._recorded_titles.pop(title)
            
    def name(self):
        """Return a string representation of the data source"""
        if(self._ssh_tunnel):
            return '%s (%s)' % (self._hostname, self._ssh_tunnel)
        else:
            return self._hostname

    @property
    def plotdata(self):
        """Returns the data source dictionary of plotdata"""
        return self._plotdata

    def _connect(self):
        """Connect to the configured backend"""
        self._ctrl_socket = ZmqSocket(REQ)
        addr = "tcp://%s:%d" % (self._hostname, self._port)
        self._ctrl_socket.ready_read.connect(self._get_request_reply)
        self._ctrl_socket.connect_socket(addr, self._ssh_tunnel)

    def _get_data_port(self):
        """Ask to the backend for the data port"""
        self._ctrl_socket.send_multipart(['data_port'])

    def query_configuration(self):
        """Ask to the backend for the configuration"""
        self._ctrl_socket.send_multipart(['conf'])

    def query_reloading(self):
        """Ask the backend to reload its configuration"""
        self._ctrl_socket.send_multipart(['reload'])
        
    def _get_request_reply(self, socket=None):
        """Handle the reply of the backend to a previous request"""
        if(socket is None):
            socket = self.sender()
        reply = socket.recv_json()
        if(reply[0] == 'data_port'):
            self._data_port = reply[1]
            logging.debug("Data source '%s' received data_port=%s", self.name(), self._data_port)
            addr = "tcp://%s:%s" % (self._hostname, self._data_port)
            self._data_socket.ready_read.connect(self._get_broadcast)
            self._data_socket.connect_socket(addr, self._ssh_tunnel)
            self.parent().add_backend(self)
            # Subscribe to stuff already requested
            for title in self._subscribed_titles.keys():
                self._data_socket.subscribe(bytes(title))
                self.subscribed.emit(title)
                logging.debug("Subscribing to %s on %s.", title, self.name())
            self.query_configuration()
        elif(reply[0] == 'conf'):
            self.conf = reply[1]
            self.titles = self.conf.keys()
            self.data_type = {}
            for k in self.conf.keys():
                if('data_type' not in self.conf[k]):
                    # Broadcasts without any data will not have a data_type
                    # Let's remove them from the title list and continue
                    self.titles.remove(k)
                    continue
                self.data_type[k] = self.conf[k]['data_type']
                if(k not in self._plotdata):
                    self._plotdata[k] = PlotData(self, k)
                    self.plotdata_added.emit(self._plotdata[k])
            # Remove PlotData which is no longer in the conf
            for k in self._plotdata.keys():
                if k not in self.titles:
                    self._plotdata.pop(k)

    def _get_broadcast(self):
        """Receive a data package on the data socket"""
        socket = self.sender()
        socket.blockSignals(True)
        QtCore.QCoreApplication.processEvents()
        socket.blockSignals(False)

        # Discard key
        socket.recv()
        data = socket.recv_json()
        for i in range(len(data)):
            if data[i] == '__ndarray__':
                data[i] = socket.recv_array()
        self._process_broadcast(data)

    def _process_broadcast(self, payload):
        """Handle a data package received by the data socket"""
        cmd = payload[1]
        title = payload[2]
        data = payload[3]
        if(title not in self.conf):
            # We're getting data we were not expecting
            # Let's discard it and order an immediate reconfigure
            logging.debug("Received unexpected data with title %s on %s. Reconfiguring...", title, self.name())
            return
        if(cmd == 'new_data'):
            data_x = payload[4]
            conf = payload[5]
            self.conf[title].update(conf)
            if self._plotdata[title].recordhistory:
                self._recorder.append(title, data, data_x)
            if 'msg' in conf:
                self._plotdata[title].append(data, data_x, conf['msg'])
            else:
                self._plotdata[title].append(data, data_x, '')

    @property
    def hostname(self):
        """Give access to the data source hostname"""
        return self._hostname

    @property
    def port(self):
        """Give access to the data source port"""
        return self._port

    @property
    def ssh_tunnel(self):
        """Give access to the data source ssh_tunnel"""
        return self._ssh_tunnel

    @property
    def subscribed_titles(self):
        """Returns the currently subscribed titles"""
        return self._subscribed_titles.keys()

    def restore_state(self, state):
        """Restores any plotdata that are saved in the state"""
        for pds in state:
            if(pds['data_source'][0] == self.hostname and
               pds['data_source'][1] == self.port and
               pds['data_source'][2] == self.ssh_tunnel):
                # It's a match!
                k = pds['title']
                pd = PlotData(self, k)
                pd.restore_state(pds, self)
                self._plotdata[k] = pd            
                self.plotdata_added.emit(self._plotdata[k])
