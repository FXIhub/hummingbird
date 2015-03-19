from interface.Qt import QtGui, QtCore
import datetime

class DataWindow(QtGui.QMainWindow):
    def __init__(self, parent = None):
         QtGui.QMainWindow.__init__(self,None)
         self._enabled_sources = {}
    def setupConnections(self):
        self.menuData_Sources.aboutToShow.connect(self.onMenuShow)        
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
                       key in self._enabled_sources[ds]):
                        action.setChecked(True)
                    else:
                        action.setChecked(False)
                    menu.addAction(action)
                    action.triggered.connect(self._source_title_triggered)

    def _source_title_triggered(self):
        action = self.sender()
        source,title = action.data()
        self.set_source_title(source,title,action.isChecked())

    def set_source_title(self, source, title, enable=True):
        if(enable):
            if(self._enabled_sources):
                # we'll assume there's just one source
                source = self._enabled_sources.keys()[0]
                source.unsubscribe(self._enabled_sources[source].pop())
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
