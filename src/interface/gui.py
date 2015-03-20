"""Displays the results of the analysis to the user, using images and plots.
"""
from Qt import QtGui, QtCore
import sys
import pickle
from ui import AddBackendDialog, PreferencesDialog, PlotWindow, ImageWindow
from data_source import DataSource
import os
import json
import signal

class GUI(QtGui.QMainWindow):
    """Main Window Class.

    Contains only menus and toolbars. The plots will be in their own windows.
    """
    instance = None
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self._data_windows = []
        self._data_sources = []
        self.settings = QtCore.QSettings()
        self._init_geometry()
        self._init_menus()
        loading_sources = self._init_data_sources()
        try:            
            self._restore_data_windows(loading_sources)
        except KeyError:
            pass
        self._init_timer()
        GUI.instance = self

    # Inititialization
    # ----------------
    def _init_geometry(self):
        if(self.settings.contains("geometry")):
            self.restoreGeometry(self.settings.value("geometry"))
        if(self.settings.contains("windowState")):
            self.restoreState(self.settings.value("windowState"))


    def _restore_data_windows(self, data_sources):
        if(self.settings.contains("dataWindows")):
            data_windows = self.settings.value("dataWindows")
            for dw in data_windows:
                try:            
                    if(dw['window_type'] == 'ImageWindow'):
                        w = ImageWindow(self)
                    elif(dw['window_type'] == 'PlotWindow'):
                        w = PlotWindow(self)                    
                    else:
                        raise ValueError('window_type %s not supported' %(pw['window_type']))
                    for es in dw['enabled_sources']:
                        for ds in data_sources:
                            if(ds._hostname == es['hostname'] and
                               ds._port == es['port'] and
                               ds._ssh_tunnel == es['tunnel']):
                                source = ds
                                title = es['title']      
                                w.set_source_title(source,title)
                    w.restoreGeometry(dw['geometry'])
                    w.restoreState(dw['windowState'])
                    w.show()
                    self._data_windows.append(w)
                # Try to handle some version incompatibilities
                except KeyError:
                    pass
        
            
    def _init_menus(self):        
        self._backends_menu = self.menuBar().addMenu(self.tr("&Backends"))

        self._add_backend_action = QtGui.QAction("Add", self)
        self._backends_menu.addAction(self._add_backend_action)
        self._add_backend_action.triggered.connect(self._add_backend_triggered)

        self._reload_backend_action = QtGui.QAction("Reload", self)
        self._backends_menu.addAction(self._reload_backend_action)
        self._reload_backend_action.triggered.connect(self._reload_backend_triggered)

        self._backends_menu.addSeparator()

        self._displays_menu = self.menuBar().addMenu(self.tr("&Displays"))
        self._new_plot_action = QtGui.QAction("New Line Plot", self)
        self._displays_menu.addAction(self._new_plot_action)
        self._new_plot_action.triggered.connect(self._new_display_triggered)

        self._new_image_action = QtGui.QAction("New Image Viewer", self)
        self._displays_menu.addAction(self._new_image_action)
        self._new_image_action.triggered.connect(self._new_display_triggered)

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
            ds.query_titles_and_type()
            # Why do I need to call this explicitly?
            ds._get_command_reply(ds._ctrl_socket)
            
    # Add data windows to the GUI
    # --------------------
    def _new_display_triggered(self):
        if(self.sender() is self._new_plot_action):
            w = PlotWindow(self)
        elif(self.sender() is self._new_image_action):
            w = ImageWindow(self)
        w.show()
        self._data_windows.append(w)


    # Add data sources to the plots
    # -----------------------------
    def addSource(self, source):
        menu =  self._backends_menu.addMenu(source.name())
        for title in source.titles:            
            action = QtGui.QAction(title, self)
            action.setData([source,title])
            action.setCheckable(True)
            action.setChecked(False)
            menu.addAction(action)
            action.triggered.connect(self._source_title_triggered)

    def _source_title_triggered(self):
        action = self.sender()
        source,title = action.data()
        if(action.isChecked()):
            source.subscribe(title)
        else:
            source.unsubscribe(title)

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
        for p in self._data_windows:
            p.replot()

    # Open preferences dialog
    # -----------------------
    def _preferencesClicked(self):
        diag = PreferencesDialog(self)
        if(diag.exec_()):
            v = diag.outputPath.text()
            self.settings.setValue("outputPath", v)
            

    def saveDataWindows(self):
        dw_settings = []
        for dw in self._data_windows:
            if(isinstance(dw, PlotWindow)):
                window_type = 'PlotWindow'
            elif(isinstance(dw, ImageWindow)):
                window_type = 'ImageWindow'                
            else:
                raise ValueError('Unsupported dataWindow type %s' % (type(dw)) )
            enabled_sources = []
            for source,title in dw.source_and_titles():
                enabled_sources.append({'hostname': source._hostname,
                                        'port': source._port,
                                        'tunnel': source._ssh_tunnel,
                                        'title': title})

            dw_settings.append({'geometry': dw.saveGeometry(),
                                'windowState': dw.saveState(),
                                'enabled_sources': enabled_sources,
                                'window_type' : window_type})
        self.settings.setValue("dataWindows", dw_settings)

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
        self.saveDataWindows()
        # Make sure settings are saved
        del self.settings
        # Force exit to prevent pyqtgraph from crashing
        os._exit(0)

def start_interface():
    """Initialize and show the Interface."""
    QtCore.QCoreApplication.setOrganizationName("SPI")
    QtCore.QCoreApplication.setOrganizationDomain("spidocs.rtfd.org")
    QtCore.QCoreApplication.setApplicationName("Hummingbird")
    app = QtGui.QApplication(sys.argv)
    GUI().show()
    sys.exit(app.exec_())

def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    if QtGui.QMessageBox.question(None, '', "Are you sure you want to quit?",
                                  QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                                  QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
        GUI.instance.closeEvent(None)

# This has to be outside a function, for unknown reasons to me
signal.signal(signal.SIGINT, sigint_handler)

