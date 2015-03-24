"""Displays the results of the analysis to the user, using images and plots.
"""
from interface.Qt import QtGui, QtCore
from interface.ui import AddBackendDialog, PreferencesDialog
from interface.ui import PlotWindow, ImageWindow
from interface import DataSource
import logging
import os

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
        loaded_sources = []
        try:
            loaded_sources = self._init_data_sources()
        except (TypeError, KeyError):
            # Be a bit more resilient against configuration problems
            logging.warning("Failed to load data source settings! Continuing...")
        try:
            self._restore_data_windows(loaded_sources)
        except (TypeError, KeyError):
            # Be a bit more resilient against configuration problems
            logging.warning("Failed to load data windows settings! Continuing...")


        self._init_timer()
        GUI.instance = self

    def _init_geometry(self):
        """Restores the geometry of the main window."""
        if(self.settings.contains("geometry")):
            self.restoreGeometry(self.settings.value("geometry"))
        if(self.settings.contains("windowState")):
            self.restoreState(self.settings.value("windowState"))

    def _restore_data_windows(self, data_sources):
        """Restores the geometry and data sources of the data windows."""
        if(self.settings.contains("dataWindows")):
            data_windows = self.settings.value("dataWindows")
            for dw in data_windows:
                try:
                    if(dw['window_type'] == 'ImageWindow'):
                        w = ImageWindow(self)
                    elif(dw['window_type'] == 'PlotWindow'):
                        w = PlotWindow(self)
                    else:
                        raise ValueError(('window_type %s not supported'
                                          %(dw['window_type'])))
                    for es in dw['enabled_sources']:
                        for ds in data_sources:
                            if(ds.hostname == es['hostname'] and
                               ds.port == es['port'] and
                               ds.ssh_tunnel == es['tunnel']):
                                source = ds
                                title = es['title']
                                w.set_source_title(source, title)
                    w.restoreGeometry(dw['geometry'])
                    w.restoreState(dw['windowState'])
                    w.show()
                    self._data_windows.append(w)
                    logging.debug("Loaded %s from settings", type(w).__name__)
                # Try to handle some version incompatibilities
                except KeyError:
                    pass

    def _init_menus(self):
        """Initialize the menus."""
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
        """Restore data sources from the settings."""
        loaded_sources = []
        if(self.settings.contains("dataSources") and
           self.settings.value("dataSources") is not None):
            for ds in self.settings.value("dataSources"):
                ds = DataSource(self, ds[0], ds[1], ds[2])
                loaded_sources.append(ds)
                logging.debug("Loaded data source '%s' from settings", ds.name())
        return loaded_sources

    def _init_timer(self):
        """Initialize reploting timer."""
        self._replot_timer = QtCore.QTimer()
        self._replot_timer.setInterval(1000) # Replot every 1000 ms
        self._replot_timer.timeout.connect(self._replot)
        self._replot_timer.start()

    def add_backend(self, data_source):
        """Add backend to menu if it's not there yet
        and append to _data_sources"""
        actions = self._backends_menu.actions()
        unique = True
        for a in actions:
            if(a.text() == data_source.name()):
                unique = False
        if(not unique):
            QtGui.QMessageBox.warning(self, "Duplicate backend",
                                      "Duplicate backend. Ignoring %s" % data_source.name())
            return

        self._data_sources.append(data_source)
        logging.debug("Registering data source '%s' in the GUI", data_source.name())
        action = QtGui.QAction(data_source.name(), self)
        action.setData(data_source)
        action.setCheckable(True)
        action.setChecked(True)
        self._backends_menu.addAction(action)
        action.triggered.connect(self._data_source_triggered)

    def _add_backend_triggered(self):
        """Create and show the add backend dialog"""
        diag = AddBackendDialog(self)
        if(diag.exec_()):
            ssh_tunnel = None
            if(diag.checkBox.isChecked()):
                ssh_tunnel = diag.ssh.text()
            ds = DataSource(self, diag.hostname.text(),
                            diag.port.value(),
                            ssh_tunnel)
            logging.debug("Adding new data source '%s'", ds.name())

    def _reload_backend_triggered(self):
        """Reload backends, asking for brodcasts and configurations"""
        # Go through the data sources and ask for new keys
        for ds in self._data_sources:
            ds.query_titles_and_type()
            # Why do I need to call this explicitly??
            ds._get_command_reply(ds._ctrl_socket)

    def _new_display_triggered(self):
        """Create a new Data Window to display data broadcasts"""
        if(self.sender() is self._new_plot_action):
            w = PlotWindow(self)
        elif(self.sender() is self._new_image_action):
            w = ImageWindow(self)
        w.show()
        self._data_windows.append(w)

    def _data_source_triggered(self):
        """Start/Stop listening to a particular data source"""
        action = self.sender()
        ds = action.data()
        if(action.isChecked()):
            self._data_sources.append(ds)
        else:
            self._data_sources.remove(ds)

    def _replot(self):
        """Replot content on all data windows"""
        for p in self._data_windows:
            p.replot()

    def _preferencesClicked(self):
        """Open the preferences dialog"""
        diag = PreferencesDialog(self)
        if(diag.exec_()):
            v = diag.outputPath.text()
            self.settings.setValue("outputPath", v)

    def saveDataWindows(self):
        """Save data windows state and data sources to the settings file"""
        dw_settings = []
        for dw in self._data_windows:
            if(isinstance(dw, PlotWindow)):
                window_type = 'PlotWindow'
            elif(isinstance(dw, ImageWindow)):
                window_type = 'ImageWindow'
            else:
                raise ValueError('Unsupported dataWindow type %s' % (type(dw)))
            enabled_sources = []
            for source, title in dw.source_and_titles():
                enabled_sources.append({'hostname': source.hostname,
                                        'port': source.port,
                                        'tunnel': source.ssh_tunnel,
                                        'title': title})

            dw_settings.append({'geometry': dw.saveGeometry(),
                                'windowState': dw.saveState(),
                                'enabled_sources': enabled_sources,
                                'window_type' : window_type})
        self.settings.setValue("dataWindows", dw_settings)

    def closeEvent(self, event):
        """Save settings and exit nicely"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        # Save data sources
        ds_settings = []
        for ds in self._data_sources:
            ds_settings.append([ds.hostname, ds.port, ds.ssh_tunnel])
        self.settings.setValue("dataSources", ds_settings)
        self.saveDataWindows()
        # Make sure settings are saved
        del self.settings
        # Force exit to prevent pyqtgraph from crashing
        os._exit(0) #pylint: disable=protected-access
        # Never gets here, but anyway...
        event.accept()

    @property
    def data_sources(self):
        """Provide access to the GUI data sources"""
        return self._data_sources

    @property
    def data_windows(self):
        """Provide access to the GUI data widows"""
        return self._data_windows
