"""Displays the results of the analysis to the user, using images and plots.
"""
from Qt import QtGui, QtCore
import sys
from zmq import SUB, REQ, ssh
import pickle
import pyqtgraph
import threading
from zmq.eventloop import ioloop, zmqstream
import zmq

class Interface(QtGui.QMainWindow):
    """Main Window Class.

    Contains only menus and toolbars. The plots will be in their own windows.
    """
    plot_requested=QtCore.Signal(str,str,list)
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self._initZMQ()
        self._plots = {}
        self.plot_requested.connect(self.plot)
        
    def _initZMQ(self):
        ioloop.install()

        self._context = zmq.Context()
        self._zmq_key = bytes('hummingbird')

        self._data_socket = self._context.socket(zmq.SUB)
        self._data_socket.setsockopt(zmq.SUBSCRIBE, self._zmq_key)
        ssh.tunnel_connection(self._data_socket, "tcp://localhost:5555", "login")
        self._data_stream = zmqstream.ZMQStream(self._data_socket)
        self._data_stream.on_recv_stream(self._get_broadcast)

        self._ctrl_socket = self._context.socket(zmq.REQ)
        ssh.tunnel_connection(self._ctrl_socket, "tcp://localhost:5554", "login")
        self._ctrl_stream = zmqstream.ZMQStream(self._ctrl_socket)
        self._ctrl_stream.on_recv_stream(self._get_command_reply)

        self._io_thread = IOLoopThread()
        self._io_thread.start()
        
    def _get_command_reply(self, stream, reply):
        print reply

    def _get_broadcast(self, stream, parts):
        # The first part is a key, so we discard
        for recvd in parts[1::2]:            
            self._process_broadcast(pickle.loads(recvd))
#        QtCore.QCoreApplication.instance().processEvents()

    def _process_broadcast(self, payload):
        # The uuid identifies the sender uniquely        
        uuid = payload[0]
        cmd = payload[1]
        if(cmd == 'plot'):
            title = payload[2]
            data = payload[3]
            # This must use a connection because it's being executed
            # by the IOLoopThread which cannot plot
            self.plot_requested.emit(str(uuid),str(title),list(data))
    
    def plot(self, uuid, title, data):
        if(uuid+title in self._plots):
            print "In _plot %s" % (title)
            self._plots[uuid+title].plot(data, clear=True,antialias=True)
        else:
            print "New plot"
            self._plots[uuid+title] = pyqtgraph.plot(data,title=title,antialias=True)
        QtCore.QCoreApplication.instance().processEvents()

def start_interface():
    """Initialize and show the Interface."""
    QtCore.QCoreApplication.setOrganizationName("SPI")
    QtCore.QCoreApplication.setOrganizationDomain("spidocs.rtfd.org")
    QtCore.QCoreApplication.setApplicationName("Hummingbird")
    app = QtGui.QApplication(sys.argv)
    mw = Interface()
    mw.show()
    ret = app.exec_()
    sys.exit(ret)


class IOLoopThread(QtCore.QThread):
    def run(self):
        ioloop.IOLoop.instance().start()
        print "ioloop ended"
