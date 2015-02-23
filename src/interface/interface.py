"""Displays the results of the analysis to the user, using images and plots.
"""
from Qt import QtGui, QtCore
import sys
import pickle
import pyqtgraph
import plot
from ui import AddBackendDialog
from data_source import DataSource

class Interface(QtGui.QMainWindow):
    """Main Window Class.

    Contains only menus and toolbars. The plots will be in their own windows.
    """
    plot_requested=QtCore.Signal(str,str,list)
    new_data=QtCore.Signal(str,str,list,list)
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self._init_menus()
        self._initZMQ()
        self._plotdata = {}
        self._data_sources = []
        self.plot_requested.connect(self.plot)
        self.new_data.connect(self.plot_append)
        self._replot_timer = QtCore.QTimer()
        # Replot every 100 ms
        self._replot_timer.setInterval(100)
        self._replot_timer.timeout.connect(self._replot)
        self._replot_timer.start()

        self._data_sources.append(DataSource(self,'localhost',
                                             5554,'login'))

    def _initZMQ(self):
        pass
#        self._context = zmq.Context()
#        self._zmq_key = bytes('hummingbird')

        # self._data_socket = self._context.socket(zmq.SUB)
        # self._data_socket.setsockopt(zmq.SUBSCRIBE, self._zmq_key)
        # ssh.tunnel_connection(self._data_socket, "tcp://localhost:5555", "login")
        # self._data_stream = zmqstream.ZMQStream(self._data_socket)
        # self._data_stream.on_recv_stream(self._get_broadcast)

        # self._ctrl_socket = self._context.socket(zmq.REQ)
        # ssh.tunnel_connection(self._ctrl_socket, "tcp://localhost:5554", "login")
        # self._ctrl_stream = zmqstream.ZMQStream(self._ctrl_socket)
        # self._ctrl_stream.on_recv_stream(self._get_command_reply)

#        self._io_thread = IOLoopThread()
#        self._io_thread.start()

    def _init_menus(self):
        self._backends_menu = self.menuBar().addMenu(self.tr("&Backends"))

        self._add_backend_action = QtGui.QAction("Add", self)
        self._backends_menu.addAction(self._add_backend_action)
        self._add_backend_action.triggered.connect(self._add_backend_triggered)
        
    def _add_backend_triggered(self):
        diag = AddBackendDialog(self)
        if(diag.exec_()):
            ssh_tunnel = None
            if(diag.checkBox.isChecked()):
                ssh_tunnel = diag.ssh.text()
            self._data_sources.append(DataSource(diag.hostname.text(),
                                                 diag.port.value(),
                                                 ssh_tunnel))

    def _get_broadcast(self):
        socket = self.sender()
        parts = socket.recv_multipart()
        # The first part is a key, so we discard
        for recvd in parts[1::2]:            
            self._process_broadcast(pickle.loads(recvd))

    def _process_broadcast(self, payload):
        # The uuid identifies the sender uniquely        
        uuid = payload[0]
        cmd = payload[1]
        if(cmd == 'set_data'):
            title = payload[2]
            data = payload[3]
            self.plot_requested.emit(str(uuid),str(title),list(data))

        if(cmd == 'new_data'):
            title = payload[2]
            data = payload[3]
            data_x = payload[4]
            self.new_data.emit(str(uuid),str(title),list(data),list(data_x))
    
    def plot(self, uuid, title, data):
        if(uuid+title not in self._plotdata):
            self._plotdata[uuid+title] = plot.PlotData(uuid, '', title)
        self._plotdata[uuid+title].set_data(data)

    def plot_append(self, uuid, title, data, data_x):
        if(uuid+title not in self._plotdata):
            self._plotdata[uuid+title] = plot.PlotData(uuid, '', title)
        self._plotdata[uuid+title].append(data, data_x)


    def _replot(self):
        for p in self._plotdata.values():
            p.replot()

    def closeEvent(self, event):
        print "Closing"
        QtCore.QCoreApplication.instance().quit()

    def addSource(self, source):
        menu =  self._backends_menu.addMenu(source.name())
        for key in source.keys:            
            action = QtGui.QAction(key, self)
            action.setData([source,key])
            action.setCheckable(True)
            action.setChecked(False)
            menu.addAction(action)
            action.triggered.connect(self._source_key_triggered)

    def _source_key_triggered(self):
        action = self.sender()
        source,key = action.data()
        if(action.isChecked()):
            source.subscribe(key)
        else:
            source.unsubscribe(key)

            
def start_interface():
    """Initialize and show the Interface."""
    sys.excepthook = exceptionHandler
    QtCore.QCoreApplication.setOrganizationName("SPI")
    QtCore.QCoreApplication.setOrganizationDomain("spidocs.rtfd.org")
    QtCore.QCoreApplication.setApplicationName("Hummingbird")
    app = QtGui.QApplication(sys.argv)
    mw = Interface()
    mw.show()
    ret = app.exec_()
    sys.exit(ret)

def exceptionHandler(exceptionType, value, traceback):
    """Handle exceptions in debugging mode"""
    sys.__excepthook__(exceptionType, value, traceback)
    QtGui.QApplication.instance().exit()
    sys.exit(-1)



