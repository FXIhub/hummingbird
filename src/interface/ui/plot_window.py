from interface.Qt import QtGui, QtCore
from interface.ui import Ui_plotWindow
import pyqtgraph
import numpy
import os

class PlotWindow(QtGui.QMainWindow, Ui_plotWindow):
    lineColors = [(252, 175, 62), (114, 159, 207), (255, 255, 255), (239, 41, 41), (138, 226, 52), (173, 127, 168)]
    def __init__(self, parent = None):
        QtGui.QMainWindow.__init__(self,None)
        self._parent = parent
        self.setupUi(self)
        self.settings = QtCore.QSettings()
        self.plot = pyqtgraph.PlotWidget(self.plotFrame, antialiasing=True)
        self.plot.hideAxis('bottom')
        self.legend = self.plot.addLegend()        
        self.legend.hide()
        layout = QtGui.QVBoxLayout(self.plotFrame)
        layout.addWidget(self.plot)
        icon_path = os.path.dirname(os.path.realpath(__file__)) + "/../images/logo_48_transparent.png"
        icon = QtGui.QPixmap(icon_path); 
        self.logoLabel.setPixmap(icon)
        self.menuData_Sources.aboutToShow.connect(self.onMenuShow)
        self.actionSave_to_JPG.triggered.connect(self.onSaveToJPG)
        self.actionSave_to_JPG.setShortcut(QtGui.QKeySequence("Ctrl+P"))
        self.actionLegend_Box.triggered.connect(self.onViewLegendBox)
        self.actionX_axis.triggered.connect(self.onViewXAxis)
        self.actionY_axis.triggered.connect(self.onViewYAxis)
        self._enabled_sources = []
    def onMenuShow(self):
        # Go through all the available data sources and add them
        self.menuData_Sources.clear()
        for ds in self._parent._data_sources:
            menu =  self.menuData_Sources.addMenu(ds.name())
            if ds.keys is not None:
                for key in ds.keys:
                    if(ds.data_type[key] != 'scalar'):
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

    def onViewLegendBox(self):
        action = self.sender()
        if(action.isChecked()):
            self.legend.show()
        else:
            self.legend.hide()

    def onViewXAxis(self):
        action = self.sender()
        if(action.isChecked()):
            self.plot.showAxis('bottom')
        else:
            self.plot.hideAxis('bottom')

    def onViewYAxis(self):
        action = self.sender()
        if(action.isChecked()):
            self.plot.showAxis('left')
        else:
            self.plot.hideAxis('left')

    def onSaveToJPG(self):
        QtGui.QPixmap.grabWidget(self.centralwidget).save(self.settings.value("outputPath") + '/screenshot.jpg', 'jpg')

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
        self.plot.clear()
        color_index = 0
        titlebar = []
        for key in self._enabled_sources:
            # There might be no data yet, so no plotdata
            if(key in self._parent._plotdata):
                pd = self._parent._plotdata[key]
                titlebar.append(pd._title)

                self.legend.removeItem(key)
                color = PlotWindow.lineColors[color_index % len(PlotWindow.lineColors)]
                if(pd._x is not None):
                    plt = self.plot.plot(x=numpy.array(pd._x, copy=False),
                                         y=numpy.array(pd._y, copy=False), clear=False, pen=color)
                else:
                    plt = self.plot.plot(numpy.array(pd._y, copy=False), clear=False, pen=color)
                found = False
                for sample, label in self.legend.items:
                    if(label.text == pd._title):
                        found = True
                        break
                if(not found):
                    self.legend.addItem(plt,pd._title)
                color_index += 1
        self.setWindowTitle(", ".join(titlebar))
