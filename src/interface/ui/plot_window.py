from interface.Qt import QtGui, QtCore
from interface.ui import Ui_plotWindow
import pyqtgraph
import numpy
import os
import datetime

class PlotWindow(QtGui.QMainWindow, Ui_plotWindow):
    lineColors = [(252, 175, 62), (114, 159, 207), (255, 255, 255), (239, 41, 41), (138, 226, 52), (173, 127, 168)]
    def __init__(self, parent = None):
        QtGui.QMainWindow.__init__(self,None)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
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
        self.plot_title = str(self.title.text())
        self.title.textChanged.connect(self.onTitleChange)
        self.actionSaveToJPG.triggered.connect(self.onSaveToJPG)
        self.actionSaveToJPG.setShortcut(QtGui.QKeySequence("Ctrl+P"))
        self.actionLegend_Box.triggered.connect(self.onViewLegendBox)
        self.actionX_axis.triggered.connect(self.onViewXAxis)
        self.actionY_axis.triggered.connect(self.onViewYAxis)
        self._enabled_sources = {}
        
    def onMenuShow(self):
        # Go through all the available data sources and add them
        self.menuData_Sources.clear()
        for ds in self._parent._data_sources:
            menu =  self.menuData_Sources.addMenu(ds.name())
            if ds.keys is not None:
                for key in ds.keys:
                    if(ds.data_type[key] != 'scalar' and 
                       ds.data_type[key] != 'vector'):
                        continue
                    action = QtGui.QAction(key, self)
                    action.setData([ds,key])
                    action.setCheckable(True)

                    if((ds.name()+key) in self._enabled_sources.keys()):
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
        dt = self.get_time()
        self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
        timestamp = '%04d%02d%02d_%02d%02d%02d' %(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        QtGui.QPixmap.grabWidget(self).save(self.settings.value("outputPath") + '/' + timestamp + '_' + self.plot_title + '.jpg', 'jpg')

    def onTitleChange(self, title):
        self.plot_title = str(title)
        
    def _source_key_triggered(self):
        action = self.sender()
        source,key = action.data()
        if(action.isChecked()):
            source.subscribe(key,self)
            self._enabled_sources[source.name()+key] = {'source': source, 'key': key}
            self.title.setText(str(key))
        else:
            source.unsubscribe(key,self)
            self._enabled_sources.pop(source.name()+key)

    def get_time(self):
        if self._enabled_sources:
            key = self._enabled_sources.keys()[0]
            source = self._enabled_sources[key]['source']
            # There might be no data yet, so no plotdata
            if(key in source._plotdata):
                pd = source._plotdata[key]
                dt = datetime.datetime.fromtimestamp(pd._x[-1])
            else: dt = datetime.datetime.now()
        else: dt = datetime.datetime.now()
        return dt

    def replot(self):
        self.plot.clear()
        color_index = 0
        titlebar = []
        self.plot.plotItem.legend.items = []

        for key in sorted(self._enabled_sources):
            source = self._enabled_sources[key]['source']
            # There might be no data yet, so no plotdata
            if(key in source._plotdata):
                pd = source._plotdata[key]
                titlebar.append(pd._title)

                color = PlotWindow.lineColors[color_index % len(PlotWindow.lineColors)]
                pen = None
                symbol = None
                symbolPen = None
                symbolBrush = None
                symbolSize = 3
                if(self.actionLines.isChecked()):
                    pen = color
                if(self.actionPoints.isChecked()):
                    symbol = 'o'
                    symbolPen = color
                    symbolBrush = color

                source_key =  self._enabled_sources[key]['key']
                if(self.actionX_axis.isChecked()):
                    if 'xlabel' in source.conf[source_key]:
                        self.plot.setLabel('bottom', source.conf[source_key]['xlabel'])                
                if(self.actionY_axis.isChecked()):
                    if 'ylabel' in source.conf[source_key]:
                        self.plot.setLabel('left', source.conf[source_key]['ylabel'])

                if(source.data_type[source_key] == 'scalar'):
                    y = pd._y
                elif(source.data_type[source_key] == 'vector'):
                    y = pd._y[-1,:]

                if(pd._x is not None and source.data_type[source_key] == 'scalar'):
                    plt = self.plot.plot(x=numpy.array(pd._x, copy=False),
                                         y=numpy.array(y, copy=False), clear=False, pen=pen, symbol=symbol, symbolPen=symbolPen, symbolBrush=symbolBrush, symbolSize=symbolSize)
                else:
                    plt = self.plot.plot(numpy.array(y, copy=False), clear=False,  pen=pen, symbol=symbol, symbolPen=symbolPen, symbolBrush=symbolBrush,symbolSize=symbolSize)
                self.legend.addItem(plt,pd._title)
                color_index += 1
        self.setWindowTitle(", ".join(titlebar))
        dt = self.get_time()
        # Round to miliseconds
        self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
        self.dateLabel.setText(str(dt.date()))

    def closeEvent(self, event):
        # Unsibscribe all everything
        for d in self._enabled_sources.values():
            d['source'].unsubscribe(d['key'],self)
        # Remove myself from the interface plot list
        # otherwise we'll be called also on replot
        self._parent._plot_windows.remove(self)
