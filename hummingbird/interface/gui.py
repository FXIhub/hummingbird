# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Displays the results of the analysis to the user, using images and plots."""
import logging
import os

from . import DataSource
from .Qt import QtCore, QtGui
from .recorder import H5Recorder
from .ui import (AddBackendDialog, ImageWindow, PlotWindow, PreferencesDialog,
                 Ui_mainWindow)


class GUI(QtGui.QMainWindow, Ui_mainWindow):
    """Main Window Class.

    Contains only menus and toolbars. The plots will be in their own windows.
    """
    instance = None
    def __init__(self, restore):
        QtGui.QMainWindow.__init__(self)
        self._data_windows = []
        self._data_sources = []
        self._recorder = None
        self.settings = None
        self.setupUi(self)
        self.restore_settings(restore)        
        GUI.instance = self

    # This is to fix a resizing bug on Mac
    def resizeEvent(self, event):
        QtGui.QMainWindow.resizeEvent(self, event)
        QtGui.QApplication.processEvents()

    def clear(self):
        """Closes all DataWindows and remove all DataSources"""
        # Need to copy self._data_windows before iterating
        # as the original list gets modified in the close() call
        # screwing a simple iteration
        for dw in list(self._data_windows):
            dw.close()
            del dw
        self._data_windows = []

        for ds in self._data_sources:
            del ds
        self._data_sources = []
        self.plotdata_widget.table.clearContents()
        self.plotdata_widget.table.setRowCount(0)
        actions = self._backends_menu.actions()
        for a in actions:
            # All the added backups have a data() element
            if(a.data()):
                # Remove them                
                self._backends_menu.removeAction(a)

    def restore_settings(self, do_restore, filename = None):
        if(filename):
            s = QtCore.QSettings(filename, QtCore.QSettings.IniFormat)
        else:
            s = QtCore.QSettings()
        self._init_geometry(s)
        self._init_recorder(s)
        self._init_timer(s)
        loaded_sources = []
        try:
            if do_restore:
                loaded_sources = self._init_data_sources(s)
        except (TypeError, KeyError):
            # raise
            # Be a bit more resilient against configuration problems
            logging.warning("Failed to load data source settings! Continuing...")
        if do_restore:
            try:
                self._restore_data_windows(s, loaded_sources)
            except (TypeError, KeyError):
                # raise
                # Be a bit more resilient against configuration problems
                logging.warning("Failed to load data windows settings! Continuing...")
            self.plotdata_widget.restore_state(s)
        self.settings = s

    def _init_geometry(self, settings):
        """Restores the geometry of the main window."""
        if(settings.contains("geometry")):
            self.restoreGeometry(settings.value("geometry"))
        if(settings.contains("windowState")):
            self.restoreState(settings.value("windowState"))

    def _init_recorder(self, settings):
        """Initializes the recorder"""
        if not settings.contains("outputPath"):
            settings.setValue("outputPath", ".")
        if not settings.contains("plotFontSize"):
            settings.setValue("plotFontSize", "13")
        if not settings.contains("plotRefresh"):
            settings.setValue("plotRefresh", "1000")            
        self._recorder = H5Recorder(settings.value("outputPath"), 100)

    def _restore_data_windows(self, settings, data_sources):
        """Restores the geometry and data sources of the data windows."""
        if(settings.contains("dataWindows")):
            data_windows = settings.value("dataWindows")
            if data_windows is None:
                return
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

    def _init_data_sources(self, settings):
        """Restore data sources from the settings."""
        loaded_sources = []
        pd_settings = []
        if(settings.contains("plotData") and
           settings.value("plotData") is not None):
            pd_settings = settings.value("plotData")

        if(settings.contains("dataSources") and
           settings.value("dataSources") is not None):
            for ds in settings.value("dataSources"):
                ds = DataSource(self, ds[0], ds[1], ds[2], ds[3])
                ds.restore_state(pd_settings)
                loaded_sources.append(ds)
                logging.debug("Loaded data source '%s' from settings", ds.name())
        return loaded_sources

    def _init_timer(self, settings):
        """Initialize reploting timer."""
        self._replot_timer = QtCore.QTimer()
        self._replot_timer.setInterval(int(settings.value("plotRefresh"))) # Replot every 1000 ms
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
        data_source._recorder = self._recorder
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

    def _reload_configuration_triggered(self):
        """Reloads the configuration in the backends"""
        for ds in self._data_sources:
            ds.query_reloading()
        self._status_message("Reloading configuration...done.", 3000)
        
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
        if self._replot_timer is not None:
            pass
            #self._replot_timer.stop()
        
        for p in self._data_windows:
            p.replot()
        self.plotdata_widget.update()
        
        if self._replot_timer is not None:
            pass
            #self._replot_timer.start()

    def _preferences_clicked(self):
        """Open the preferences dialog"""
        diag = PreferencesDialog(self)
        if(diag.exec_()):
            v = diag.outputPath.text()
            self.settings.setValue("outputPath", v)
            size = diag.fontSize.value()
            self.settings.setValue("plotFontSize", size)          
            for dw in self._data_windows:
                dw.updateFonts()
            self._recorder.outpath = v
            plot_refresh = diag.plotRefresh.value()
            self.settings.setValue("plotRefresh", plot_refresh)
            self._replot_timer.setInterval(plot_refresh)              

    def _recorder_toggled(self, turn_on):
        """Start/Stop the recorder"""
        if self._recorder is None:
            self._recorder_action.setChecked(False)
            return
        if (turn_on):
            record_titles = self.plotdata_widget.record_titles(True)
            if not len(record_titles):
                return
            success = self._recorder.openfile()
            if not success:
                self._recorder_action.setChecked(False)
                return
            for ds in self._data_sources:
                if ds.name() in record_titles:
                    for title in record_titles[ds.name()]:
                        ds.subscribe_for_recording(title)
        else:
            self._recorder.closefile()
            record_titles = self.plotdata_widget.record_titles(False)
            for ds in self._data_sources:
                if ds.name() in record_titles:
                    for title in record_titles[ds.name()]:
                        ds.unsubscribe_for_recording(title)
                
    def save_data_windows(self):
        """Save data windows state and data sources to the settings file"""
        dw_settings = []
        for dw in self._data_windows:
            dw_settings.append(dw.get_state())
        return dw_settings

    def _on_save_settings_triggered(self):
        # We need a non native dialog to work around a Qt bug
        # https://bugreports.qt.io/browse/QTBUG-16722        
        fname = QtGui.QFileDialog.getSaveFileName(self, "Save Settings", filter="Humminbird Settings (*.hum)", 
                                                  options=QtGui.QFileDialog.DontUseNativeDialog)
        if(fname):
            self.save_settings(fname)

    def _on_load_settings_triggered(self):
        # We need a non native dialog to work around a Qt bug
        # https://bugreports.qt.io/browse/QTBUG-16722        
        fname = QtGui.QFileDialog.getOpenFileName(self, "Load Settings", filter="Humminbird Settings (*.hum)", 
                                                  options=QtGui.QFileDialog.DontUseNativeDialog)
        if(fname):
            self.clear()
            self.restore_settings(fname)

    def save_settings(self, filename=None):
        if(filename):
            s = QtCore.QSettings(filename, QtCore.QSettings.IniFormat)
        else:
            s = QtCore.QSettings()
        s.setValue("geometry", self.saveGeometry())
        s.setValue("windowState", self.saveState())
        # Save data sources
        ds_settings = []
        for ds in self._data_sources:
            ds_settings.append([ds.hostname, ds.port, ds.ssh_tunnel, ds.conf])
        s.setValue("dataSources", ds_settings)
        self.plotdata_widget.save_state(s)
        s.setValue("plotData", self.plotdata_widget.save_plotdata())
        s.setValue("dataWindows", self.save_data_windows())
        # Make sure settings are saved
        s.sync()

    def closeEvent(self, event): #pylint: disable=invalid-name
        """Save settings and exit nicely"""
        self.save_settings()
        # Force exit to prevent pyqtgraph from crashing, lingering windows
        QtGui.qApp.quit()
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
