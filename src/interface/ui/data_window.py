"""Base class for all the data display windows"""
from interface.Qt import QtGui, QtCore
import logging

class DataWindow(QtGui.QMainWindow):
    """Base class for all the data display windows
    (e.g. PlotWindow, ImageWindow)"""
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, None)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self._enabled_sources = {}
        self.settings = QtCore.QSettings()
        self.setupUi(self)
        self._setup_connections()
        self._parent = parent
        # If True this DataWindow was restored from saved settings
        self.restored = False

    def _setup_connections(self):
        """Initialize connections"""
        self.menuData_Sources.aboutToShow.connect(self.on_menu_show)
        self.actionSaveToJPG.triggered.connect(self.on_save_to_jpg)
        self.actionSaveToJPG.setShortcut(QtGui.QKeySequence("Ctrl+P"))

    def _finish_layout(self):
        """This is called after the derived classes finish settings up so
        that the lower common section of the window can be setup. Kinda ugly."""
        layout = QtGui.QVBoxLayout(self.plotFrame)
        layout.addWidget(self.plot)
        self.plot_title = str(self.title.text())
        self.title.textChanged.connect(self._on_title_change)

    def _on_title_change(self, title):
        """Change the name of the data window"""
        self.plot_title = str(title)

    def on_menu_show(self):
        """Show what data sources are available"""
        # Go through all the available data sources and add them
        self.menuData_Sources.clear()
        for ds in self._parent.data_sources:
            menu = self.menuData_Sources.addMenu(ds.name())
            if ds.titles is not None:
                for title in ds.titles:
                    if(ds.data_type[title] not in self.acceptable_data_types):
                        continue
                    action = QtGui.QAction(title, self)
                    action.setData([ds, title])
                    action.setCheckable(True)
                    if(ds in self._enabled_sources and
                       title in self._enabled_sources[ds]):
                        action.setChecked(True)
                    else:
                        action.setChecked(False)
                    menu.addAction(action)
                    action.triggered.connect(self._source_title_triggered)

    def get_time(self, index=None):
        """Returns the time of the given index, or the time of the last data point"""
        if index is None:
            index = self.current_index
        # Check if we have last_vector
        if(self.last_vector_x is not None):
            dt = datetime.datetime.fromtimestamp(self.last_vector_x[index])
            return dt

        # Check if we have enabled_sources
        source = None
        if(self._enabled_sources):
            for ds in self._enabled_sources.keys():
                if(len(self._enabled_sources[ds])):
                    title = self._enabled_sources[ds][0]
                    source = ds
                    break

        # There might be no data yet, so no plotdata
        if(source is not None and title in source.plotdata and
           source.plotdata[title].x is not None):
            pd = source.plotdata[title]
            dt = datetime.datetime.fromtimestamp(pd.x[index])
            return dt
        else:
            return datetime.datetime.now()

    def on_save_to_jpg(self):
        """Save a screenshot of the window"""
        dt = self.get_time()
        self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
        timestamp = '%04d%02d%02d_%02d%02d%02d' %(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        QtGui.QPixmap.grabWidget(self).save(self.settings.value("outputPath") + '/' +
                                            timestamp + '_' + self.plot_title + '.jpg', 'jpg')

    def _source_title_triggered(self):
        """Enable/disable a data source"""
        action = self.sender()
        source, title = action.data()
        self.set_source_title(source, title, action.isChecked())

    def set_source_title(self, source, title, enable=True):
        """Enable/disable a given broadcast"""
        if(enable):
            if(self.exclusive_source and self._enabled_sources):
                for s, t in self.source_and_titles():
                    self._enabled_sources[source].remove(t)
                    s.unsubscribe(t, self)
            source.subscribe(title, self)
            if(source in  self._enabled_sources):
                self._enabled_sources[source].append(title)
            else:
                self._enabled_sources[source] = [title]
            self.title.setText(str(title))
        else:
            source.unsubscribe(title, self)
            self._enabled_sources[source].remove(title)

    def closeEvent(self, event):
        """Unsubscribe to any remaining broadcasts before closing"""
        # Unsibscribe all everything
        logging.debug("Closing DataWindow %s" % (self))
        for source in self._enabled_sources.keys():
            for title in self._enabled_sources[source]:
                source.unsubscribe(title, self)
        # Remove myself from the interface plot list
        # otherwise we'll be called also on replot
        self._parent.data_windows.remove(self)
        event.accept()

    def source_and_titles(self):
        """Iterate through all available broadcasts"""
        for source in self._enabled_sources.keys():
            for title in self._enabled_sources[source]:
                yield source, title

    def get_state(self, settings):
        """Returns settings that can be used to restore the widget to the current state"""
        enabled_sources = []
        for source, title in self.source_and_titles():
            enabled_sources.append({'hostname': source.hostname,
                                    'port': source.port,
                                    'tunnel': source.ssh_tunnel,
                                    'title': title})
        settings['geometry'] = self.saveGeometry()
        settings['windowState'] = self.saveState()
        settings['enabled_sources'] = enabled_sources
        settings['window title'] = str(self.title.text())

        return settings

    def restore_from_state(self, settings, data_sources):
        """Restores the widget to the same state as when the settings were generated"""
        for es in settings['enabled_sources']:
            for ds in data_sources:
                if(ds.hostname == es['hostname'] and
                   ds.port == es['port'] and
                   ds.ssh_tunnel == es['tunnel']):
                    source = ds
                    title = es['title']
                    self.set_source_title(source, title)
        self.restoreGeometry(settings['geometry'])
        self.restoreState(settings['windowState'])
        self.title.setText(settings['window title'])
        self.show()
        self.restored = True
        logging.debug("Loaded %s from settings", type(self).__name__)
        
