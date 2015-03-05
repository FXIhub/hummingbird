"""Displays the results of the analysis to the user, using images and plots.
"""
from Qt import QtGui, QtCore
import sys
import pickle
import pyqtgraph
from plotdata import PlotData
from ui import AddBackendDialog, PlotWindow, ImageWindow
from data_source import DataSource
import os

class Interface(QtGui.QMainWindow):
    """Main Window Class.

    Contains only menus and toolbars. The plots will be in their own windows.
    """
    plot_requested=QtCore.Signal(str,str,list)
    new_data=QtCore.Signal(str,str,list,list)
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self._plot_windows = []
        self._data_sources = []
        self._plotdata = {}
        self.settings = QtCore.QSettings()
        self._init_geometry()
        self._init_menus()
        self._init_data_sources()
        self._init_connections()
        self._init_timer()

    # Inititialization
    # ----------------
    def _init_geometry(self):
        if(self.settings.contains("geometry")):
            self.restoreGeometry(self.settings.value("geometry"))
        if(self.settings.contains("windowState")):
            self.restoreState(self.settings.value("windowState"))
            
    def _init_menus(self):
        self._backends_menu = self.menuBar().addMenu(self.tr("&Backends"))

        self._add_backend_action = QtGui.QAction("Add", self)
        self._backends_menu.addAction(self._add_backend_action)
        self._backends_menu.addSeparator()
        self._add_backend_action.triggered.connect(self._add_backend_triggered)

        self._plots_menu = self.menuBar().addMenu(self.tr("&Plots"))
        self._new_plot_action = QtGui.QAction("New Line Plot", self)
        self._plots_menu.addAction(self._new_plot_action)
        self._new_plot_action.triggered.connect(self._new_plot_triggered)

        self._new_image_action = QtGui.QAction("New Image Plot", self)
        self._plots_menu.addAction(self._new_image_action)
        self._new_image_action.triggered.connect(self._new_plot_triggered)

    def _init_data_sources(self):
        if(self.settings.contains("dataSources")):
            for ds in self.settings.value("dataSources"):
                ds = DataSource(self, ds[0], ds[1], ds[2])
                if(ds.connected):
                    self._data_sources.append(ds)
            
    def _init_connections(self):
        self.plot_requested.connect(self.plot)
        self.new_data.connect(self.plot_append)

    def _init_timer(self):
        self._replot_timer = QtCore.QTimer()
        self._replot_timer.setInterval(1000) # Replot every 100 ms
        self._replot_timer.timeout.connect(self._replot)
        self._replot_timer.start()

    # Add backends to the GUI
    # -------------------------
    def add_backend_to_menu(self, ds):
        action = QtGui.QAction(ds.name(), self)
        action.setData(ds)
        action.setCheckable(True)
        action.setChecked(True)        
        self._backends_menu.addAction(action)
        action.triggered.connect(self._data_source_triggered)

    def _add_backend_triggered(self):
        diag = AddBackendDialog(self)
        if(diag.exec_()):
            ssh_tunnel = None
            if(diag.checkBox.isChecked()):
                ssh_tunnel = diag.ssh.text()
            ds = DataSource(self, diag.hostname.text(),
                            diag.port.value(),
                            ssh_tunnel)
            if(ds.connected):
                self._data_sources.append(ds)

    # Add plots to the GUI
    # --------------------
    def _new_plot_triggered(self):
        if(self.sender() is self._new_plot_action):
            w = PlotWindow(self)
        elif(self.sender() is self._new_image_action):
            w = ImageWindow(self)
        w.show()
        self._plot_windows.append(w)

    def plot(self, uuid, title, data):
        if(uuid+title not in self._plotdata):
            self._plotdata[uuid+title] = PlotData(self, uuid, '', title)
        self._plotdata[uuid+title].set_data(data)

    def plot_append(self, uuid, title, data, data_x):
        if(uuid+title not in self._plotdata):
            self._plotdata[uuid+title] = PlotData(self, uuid, '', title)
        self._plotdata[uuid+title].append(data, data_x)

    # Add data sources to the plots
    # -----------------------------
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

    def _data_source_triggered(self):
        action = self.sender()
        ds = action.data()
        if(action.isChecked()):
            self._data_sources.append(ds)
        else:
            self._data_sources.remove(ds)

    # Receiving signals form broadcast
    # --------------------------------
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
            self.plot(str(uuid),title,data)

        if(cmd == 'new_data'):
            title = payload[2]
            data = payload[3]
            data_x = payload[4]
            self.plot_append(str(uuid),title,data,data_x)
    
    # Refresh plots
    # -------------
    def _replot(self):
        for p in self._plot_windows:
            p.replot()


    # Closing the GUI
    # ---------------
    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        ds_settings = []
        for ds in self._data_sources:
            ds_settings.append([ds._hostname, ds._port, ds._ssh_tunnel])        
        self.settings.setValue("dataSources", ds_settings)
        # Make sure settings are saved
        del self.settings
        # Force exit to prevent pyqtgraph from crashing
        os._exit(0)

            
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



