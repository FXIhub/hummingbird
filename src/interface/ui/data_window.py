"""Base class for all the data display windows"""
from interface.Qt import QtGui, QtCore
import os

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

    def _setup_connections(self):
        """Initialize connections"""
        self.menuData_Sources.aboutToShow.connect(self.on_menu_show)
        self.actionSaveToJPG.triggered.connect(self.on_save_to_jpg)
        self.actionSaveToJPG.setShortcut(QtGui.QKeySequence("Ctrl+P"))

    def finish_layout(self):
        """This is called after the derived classes finish settings up so
        that the lower common section of the window can be setup. Kinda ugly."""
        layout = QtGui.QVBoxLayout(self.plotFrame)
        layout.addWidget(self.plot)
        icon_path = os.path.dirname(os.path.realpath(__file__)) + "/../images/logo_48_transparent.png"
        icon = QtGui.QPixmap(icon_path)
        self.logoLabel.setPixmap(icon)
        self.plot_title = str(self.title.text())
        self.title.textChanged.connect(self.on_title_change)

    def on_title_change(self, title):
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
