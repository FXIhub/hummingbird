from interface.Qt import QtGui, QtCore
import datetime
import os

class DataWindow(QtGui.QMainWindow):
    def __init__(self, parent = None):
        QtGui.QMainWindow.__init__(self,None)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self._enabled_sources = {}
        self.settings = QtCore.QSettings()
        self.setupUi(self)
        self.setup_connections()
        self._parent = parent

    def setup_connections(self):
        self.menuData_Sources.aboutToShow.connect(self.onMenuShow)
        self.actionSaveToJPG.triggered.connect(self.onSaveToJPG)
        self.actionSaveToJPG.setShortcut(QtGui.QKeySequence("Ctrl+P"))

    def finish_layout(self):
        layout = QtGui.QVBoxLayout(self.plotFrame)
        layout.addWidget(self.plot)
        icon_path = os.path.dirname(os.path.realpath(__file__)) + "/../images/logo_48_transparent.png"
        icon = QtGui.QPixmap(icon_path); 
        self.logoLabel.setPixmap(icon)
        self.plot_title = str(self.title.text())
        self.title.textChanged.connect(self.onTitleChange)

    def onTitleChange(self, title):
        self.plot_title = str(title)

    def onMenuShow(self):
        # Go through all the available data sources and add them
        self.menuData_Sources.clear()
        for ds in self._parent._data_sources:
            menu =  self.menuData_Sources.addMenu(ds.name())
            if ds.titles is not None: 
                for title in ds.titles:
                    if(ds.data_type[title] not in self.acceptable_data_types):
                        continue
                    action = QtGui.QAction(title, self)
                    action.setData([ds,title])
                    action.setCheckable(True)
                    if(ds in self._enabled_sources and
                       title in self._enabled_sources[ds]):
                        action.setChecked(True)
                    else:
                        action.setChecked(False)
                    menu.addAction(action)
                    action.triggered.connect(self._source_title_triggered)

    def onSaveToJPG(self):
        dt = self.get_time()
        self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
        timestamp = '%04d%02d%02d_%02d%02d%02d' %(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        QtGui.QPixmap.grabWidget(self).save(self.settings.value("outputPath") + '/' + timestamp + '_' + self.plot_title + '.jpg', 'jpg')

    def _source_title_triggered(self):
        action = self.sender()
        source,title = action.data()
        self.set_source_title(source,title,action.isChecked())

    def set_source_title(self, source, title, enable=True):
        if(enable):
            if(self.exclusive_source and self._enabled_sources):
                for s,t in self.source_and_titles():
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

    def get_time(self, index=None):
        if index is None:
            try:
                index = self.plot.currentIndex
            except NameError:
                index = -1
        # Check if we have enabled_sources
        source = None
        if(self._enabled_sources):
            source = self._enabled_sources.keys()[0]
            title = self._enabled_sources[source][0]
        # There might be no data yet, so no plotdata
        if(source is not None and title in source._plotdata and
           source._plotdata[title]._x is not None):
            pd = source._plotdata[title]
            dt = datetime.datetime.fromtimestamp(pd._x[index])
            return dt
        else:
            return datetime.datetime.now()

    def closeEvent(self, event):
        # Unsibscribe all everything
        for source in self._enabled_sources.keys():
            for title in self._enabled_sources[source]:
                source.unsubscribe(title, self)
        # Remove myself from the interface plot list
        # otherwise we'll be called also on replot
        self._parent._data_windows.remove(self)

    def source_and_titles(self):
        for source in self._enabled_sources.keys():
            for title in self._enabled_sources[source]:
                yield source,title
