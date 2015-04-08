"""Displays the results of the analysis to the user, using images and plots.
"""
from interface.Qt import QtGui, QtCore
from interface.ui import AddBackendDialog, PreferencesDialog
from interface.ui import PlotWindow, ImageWindow
from interface import DataSource
from interface.ui import Ui_mainWindow
import logging
import os

class GUI(QtGui.QMainWindow, Ui_mainWindow):
    """Main Window Class.

    Contains only menus and toolbars. The plots will be in their own windows.
    """
    instance = None
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self._data_windows = []
        self._data_sources = []
        self.settings = QtCore.QSettings()
        self.setupUi(self)
        self._init_geometry()
        loaded_sources = []
        try:
            loaded_sources = self._init_data_sources()
        except (TypeError, KeyError):
            raise
            # Be a bit more resilient against configuration problems
            logging.warning("Failed to load data source settings! Continuing...")
        try:
            self._restore_data_windows(loaded_sources)
        except (TypeError, KeyError):
            # Be a bit more resilient against configuration problems
            logging.warning("Failed to load data windows settings! Continuing...")

        self.plotdata_widget.restore_state(self.settings)

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
                        raise ValueError(('window_type %s not supported' %(dw['window_type'])))
                    w.restore_from_state(dw, data_sources)
                    self._data_windows.append(w)
                    logging.debug("Loaded %s from settings", type(w).__name__)
                # Try to handle some version incompatibilities
                except KeyError:
                    raise
                    pass

    def _init_data_sources(self):
        """Restore data sources from the settings."""
        loaded_sources = []
        pd_settings = []
        if(self.settings.contains("plotData") and
           self.settings.value("plotData") is not None):
            pd_settings = self.settings.value("plotData")

        if(self.settings.contains("dataSources") and
           self.settings.value("dataSources") is not None):
            for ds in self.settings.value("dataSources"):
                ds = DataSource(self, ds[0], ds[1], ds[2])
                ds.restore_state(pd_settings)
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
        self.plotdata_widget.add_source(data_source)
        self._status_message("Backend '%s' connected." % (data_source.name()), 5000)

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
        self._status_message("Reloading backends...")
        for ds in self._data_sources:
            ds.query_configuration()
        self._status_message("Reloading backends...done.", 3000)

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
        self.plotdata_widget.update()

    def _preferences_clicked(self):
        """Open the preferences dialog"""
        diag = PreferencesDialog(self)
        if(diag.exec_()):
            v = diag.outputPath.text()
            self.settings.setValue("outputPath", v)

    def save_data_windows(self):
        """Save data windows state and data sources to the settings file"""
        dw_settings = []
        for dw in self._data_windows:
            dw_settings.append(dw.get_state())
        return dw_settings

    def closeEvent(self, event): #pylint: disable=invalid-name
        """Save settings and exit nicely"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        # Save data sources
        ds_settings = []
        for ds in self._data_sources:
            ds_settings.append([ds.hostname, ds.port, ds.ssh_tunnel])
        self.settings.setValue("dataSources", ds_settings)
        self.plotdata_widget.save_state(self.settings)
        self.settings.setValue("plotData", self.plotdata_widget.save_plotdata())
        self.settings.setValue("dataWindows", self.save_data_windows())
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

    def _status_message(self, msg, timeout=0, process_events=True):
        """Set statusBar message and make sure to show it!"""
        self.statusbar.showMessage(msg, timeout)
        # Without this it might not actually be shown
        if(process_events):
            QtCore.QCoreApplication.processEvents()
