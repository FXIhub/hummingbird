"""Displays the results of the analysis to the user, using images and plots.
"""
from Qt import QtGui, QtCore
import sys
import pickle
import pyqtgraph
from ui import AddBackendDialog, PreferencesDialog, PlotWindow, ImageWindow
from data_source import DataSource
import os
import json

class Interface(QtGui.QMainWindow):
    """Main Window Class.

    Contains only menus and toolbars. The plots will be in their own windows.
    """
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self._plot_windows = []
        self._data_sources = []
        self.settings = QtCore.QSettings()
        self._init_geometry()
        self._init_menus()
        loading_sources = self._init_data_sources()
        self._restore_plot_windows(loading_sources)
        self._init_connections()
        self._init_timer()

    # Inititialization
    # ----------------
    def _init_geometry(self):
        if(self.settings.contains("geometry")):
            self.restoreGeometry(self.settings.value("geometry"))
        if(self.settings.contains("windowState")):
            self.restoreState(self.settings.value("windowState"))


    def _restore_plot_windows(self, data_sources):
        if(self.settings.contains("plotWindows")):
            plot_windows = self.settings.value("plotWindows")
            for pw in plot_windows:
                if(pw['window_type'] == 'ImageWindow'):
                    w = ImageWindow(self)
                    for es in pw['enabled_sources']:
                        for ds in data_sources:
                            if(ds._hostname == es['hostname'] and
                               ds._port == es['port'] and
                               ds._ssh_tunnel == es['tunnel']):
                                source = ds
                                key = es['key']      
                                w.set_source_key(source,key)
                    
                elif(pw['window_type'] == 'PlotWindow'):
                    w = PlotWindow(self)
                else:
                    raise ValueError('window_type %s not supported' %(pw['window_type']))
                w.restoreGeometry(pw['geometry'])
                w.restoreState(pw['windowState'])
                w.show()
                self._plot_windows.append(w)
        
            
    def _init_menus(self):        
        self._backends_menu = self.menuBar().addMenu(self.tr("&Backends"))

        self._add_backend_action = QtGui.QAction("Add", self)
        self._backends_menu.addAction(self._add_backend_action)
        self._add_backend_action.triggered.connect(self._add_backend_triggered)

        self._reload_backend_action = QtGui.QAction("Reload", self)
        self._backends_menu.addAction(self._reload_backend_action)
        self._reload_backend_action.triggered.connect(self._reload_backend_triggered)

        self._backends_menu.addSeparator()

        self._plots_menu = self.menuBar().addMenu(self.tr("&Plots"))
        self._new_plot_action = QtGui.QAction("New Line Plot", self)
        self._plots_menu.addAction(self._new_plot_action)
        self._new_plot_action.triggered.connect(self._new_plot_triggered)

        self._new_image_action = QtGui.QAction("New Image Plot", self)
        self._plots_menu.addAction(self._new_image_action)
        self._new_image_action.triggered.connect(self._new_plot_triggered)

        self._options_menu = self.menuBar().addMenu(self.tr("&Options"))
        self._preferences_action = QtGui.QAction("Preferences", self)
        self._options_menu.addAction(self._preferences_action)
        self._preferences_action.triggered.connect(self._preferencesClicked)

    def _init_data_sources(self):
        loaded_sources = []
        if(self.settings.contains("dataSources") and 
           self.settings.value("dataSources") is not None):
            for ds in self.settings.value("dataSources"):
                ds = DataSource(self, ds[0], ds[1], ds[2])
                loaded_sources.append(ds)    
        return loaded_sources

    def _init_connections(self):
        pass

    def _init_timer(self):
        self._replot_timer = QtCore.QTimer()
        self._replot_timer.setInterval(1000) # Replot every 1000 ms
        self._replot_timer.timeout.connect(self._replot)
        self._replot_timer.start()

    # Add backends to the GUI
    # -------------------------
    def add_backend(self, ds):
        # Add backend to menu if it's not there yet
        # and append to _data_sources
        actions = self._backends_menu.actions()
        unique = True
        for a in actions:
            if(a.text() == ds.name()):
                unique = False
        if(not unique):
            QtGui.QMessageBox.warning(self, "Duplicate backend", "Duplicate backend. Ignoring %s" % ds.name())
            return

        self._data_sources.append(ds)
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

    def _reload_backend_triggered(self):
        # Go through the data sources and ask for new keys
        for ds in self._data_sources:
            ds.query_keys_and_type()
            # Why do I need to call this explicitly?
            ds._get_command_reply(ds._ctrl_socket)
            
    # Add plots to the GUI
    # --------------------
    def _new_plot_triggered(self):
        if(self.sender() is self._new_plot_action):
            w = PlotWindow(self)
        elif(self.sender() is self._new_image_action):
            w = ImageWindow(self)
        w.show()
        self._plot_windows.append(w)


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

    # Refresh plots
    # -------------
    def _replot(self):
        for p in self._plot_windows:
            p.replot()

    # Open preferences dialog
    # -----------------------
    def _preferencesClicked(self):
        diag = PreferencesDialog(self)
        if(diag.exec_()):
            v = diag.outputPath.text()
            self.settings.setValue("outputPath", v)
            

    def savePlotWindows(self):
        pw_settings = []
        for pw in self._plot_windows:
            enabled_sources = []
            if(isinstance(pw,PlotWindow)):
                print  pw._enabled_sources
                for es in pw._enabled_sources.values():
                    ds = es['source']
                    enabled_sources.append({'hostname': ds._hostname,
                                            'port': ds._port,
                                            'tunnel': ds._ssh_tunnel,
                                            'key': es['key']})
                    window_type = 'PlotWindow'
            elif(isinstance(pw,ImageWindow)):
                ds = pw._prev_source
                if(ds is not None):
                    enabled_sources.append({'hostname': ds._hostname,
                                            'port': ds._port,
                                            'tunnel': ds._ssh_tunnel,
                                            'key': pw._prev_key})
                window_type = 'ImageWindow'
                
            else:
                raise ValueError('Unsupported plotWindow type %s' % (type(pw)) )

            pw_settings.append({'geometry': pw.saveGeometry(),
                                'windowState': pw.saveState(),
                                'enabled_sources': enabled_sources,
                                'window_type' : window_type})
        self.settings.setValue("plotWindows", pw_settings)

    # Closing the GUI
    # ---------------
    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        # Save data sources
        ds_settings = []
        for ds in self._data_sources:
            ds_settings.append([ds._hostname, ds._port, ds._ssh_tunnel])        
        self.settings.setValue("dataSources", ds_settings)
        self.savePlotWindows()
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



