from interface.Qt import QtGui, QtCore
from interface.ui import Ui_imageWindow
import pyqtgraph
import numpy
import os
from IPython.core.debugger import Tracer

class ImageWindow(QtGui.QMainWindow, Ui_imageWindow):
    def __init__(self, parent = None):
        QtGui.QMainWindow.__init__(self,None)
        self._parent = parent
        self.setupUi(self)
        self.plot = pyqtgraph.ImageView(self.plotFrame, view=pyqtgraph.PlotItem())
        self.plot.ui.roiBtn.hide()
        self.plot.ui.normBtn.hide()
        layout = QtGui.QVBoxLayout(self.plotFrame)
        layout.addWidget(self.plot)
        icon_path = os.path.dirname(os.path.realpath(__file__)) + "/../images/logo_48_transparent.png"
        icon = QtGui.QPixmap(icon_path); 
        self.logoLabel.setPixmap(icon)
        self.menuData_Sources.aboutToShow.connect(self.onMenuShow)
        self._enabled_sources = []
    def onMenuShow(self):
        # Go through all the available data sources and add them
        self.menuData_Sources.clear()
        for ds in self._parent._data_sources:
            menu =  self.menuData_Sources.addMenu(ds.name())
            if ds.keys is not None: 
                for key in ds.keys:
                    if(ds.data_type[key] != 'image'):
                        continue
                    action = QtGui.QAction(key, self)
                    action.setData([ds,key])
                    action.setCheckable(True)
                    if((ds.uuid+key) in self._enabled_sources):
                        action.setChecked(True)
                    else:
                        action.setChecked(False)
                    menu.addAction(action)
                    action.triggered.connect(self._source_key_triggered)

    def _source_key_triggered(self):
        action = self.sender()
        source,key = action.data()
        if(action.isChecked()):
            source.subscribe(key)
            self._enabled_sources.append(source.uuid+key)
        else:
            source.unsubscribe(key)
            self._enabled_sources.remove(source.uuid+key)

    def replot(self):
        for key in self._enabled_sources:
            # There might be no data yet, so no plotdata
            if(key in self._parent._plotdata):
                pd = self._parent._plotdata[key]
                if(self.plot.image is not None):               
                    last_index = self.plot.image.shape[0]-1
                    # Only update if we're in the last index
                    if(self.plot.currentIndex == last_index):
                        self.plot.setImage(numpy.array(pd._y), 
                                           transform = QtGui.QTransform(0, 1, 0,
                                                                        1, 0, 0,
                                                                        0, 0, 1))
                        last_index = self.plot.image.shape[0]-1
                        self.plot.setCurrentIndex(last_index)
                else:
                    self.plot.setImage(numpy.array(pd._y),
                                       transform = QtGui.QTransform(0, 1, 0,
                                                                    1, 0, 0,
                                                                    0, 0, 1))
                self.setWindowTitle(pd._title)
