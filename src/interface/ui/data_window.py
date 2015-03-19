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
            if ds.keys is not None: 
                for key in ds.keys:
                    if(ds.data_type[key] not in self.acceptable_data_types):
                        continue
                    action = QtGui.QAction(key, self)
                    action.setData([ds,key])
                    action.setCheckable(True)
                    if(ds in self._enabled_sources and
                       key in self._enabled_sources[ds]):
                        action.setChecked(True)
                    else:
                        action.setChecked(False)
                    menu.addAction(action)
                    action.triggered.connect(self._source_key_triggered)

    def _source_key_triggered(self):
        action = self.sender()
        source,key = action.data()
        self.set_source_key(source,key,action.isChecked())

    def set_source_key(self, source, key, enable=True):
        if(enable):
            if(self._enabled_sources):
                # we'll assume there's just one source
                source = self._enabled_sources.keys()[0]
                key = self._enabled_sources[source].pop()
                source.unsubscribe(key)
            source.subscribe(key, self)
            if(source in  self._enabled_sources):                
                self._enabled_sources[source].append(key)
            else:
                self._enabled_sources[source] = [key]
            self.title.setText(str(key))
        else:
            source.unsubscribe(key, self)
            self._enabled_sources[source].remove(key)

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
            key = self._enabled_sources[source][0]
        # There might be no data yet, so no plotdata
        if(source is not None and key in source._plotdata):
            pd = source._plotdata[key]
            dt = datetime.datetime.fromtimestamp(pd._x[index])
            return dt
        else:
            return datetime.datetime.now()

    def closeEvent(self, event):
        # Unsibscribe all everything
        for source in self._enabled_sources.keys():
            for key in self._enabled_sources[source]:
                source.unsubscribe(key, self)
        # Remove myself from the interface plot list
        # otherwise we'll be called also on replot
        self._parent._data_windows.remove(self)

    def source_and_keys(self):
        for source in self._enabled_sources.keys():
            for key in self._enabled_sources[source]:
                yield source,key
