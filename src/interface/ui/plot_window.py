from interface.Qt import QtGui, QtCore
from interface.ui import Ui_plotWindow
import pyqtgraph
import numpy
import os
import datetime
from data_window import DataWindow

class PlotWindow(DataWindow, Ui_plotWindow):
    lineColors = [(252, 175, 62), (114, 159, 207), (255, 255, 255), (239, 41, 41), (138, 226, 52), (173, 127, 168)]
    def __init__(self, parent = None):
        DataWindow.__init__(self,None)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self._parent = parent
        self.setupUi(self)
        self.setupConnections()
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
        self.plot_title = str(self.title.text())
        self.title.textChanged.connect(self.onTitleChange)
        self.actionSaveToJPG.triggered.connect(self.onSaveToJPG)
        self.actionSaveToJPG.setShortcut(QtGui.QKeySequence("Ctrl+P"))
        self.actionLegend_Box.triggered.connect(self.onViewLegendBox)
        self.actionX_axis.triggered.connect(self.onViewXAxis)
        self.actionY_axis.triggered.connect(self.onViewYAxis)
        self.acceptable_data_types = ['scalar', 'vector']
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
        
    def replot(self):
        self.plot.clear()
        color_index = 0
        titlebar = []
        self.plot.plotItem.legend.items = []

        for source in self._enabled_sources.keys():
            for key in self._enabled_sources[source]:
                if(key not in source._plotdata):
                    # There might be no data yet, so no plotdata
                    continue
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

                conf = source.conf[key]
                if(self.actionX_axis.isChecked()):
                    if 'xlabel' in conf:
                        self.plot.setLabel('bottom', conf['xlabel'])                
                if(self.actionY_axis.isChecked()):
                    if 'ylabel' in conf:
                        self.plot.setLabel('left', conf['ylabel'])

                if(source.data_type[key] == 'scalar'):
                    y = pd._y
                elif(source.data_type[key] == 'vector'):
                    y = pd._y[-1,:]

                if(pd._x is not None and source.data_type[key] == 'scalar'):
                    plt = self.plot.plot(x=numpy.array(pd._x, copy=False),
                                         y=numpy.array(y, copy=False), clear=False, pen=pen, symbol=symbol,
                                         symbolPen=symbolPen, symbolBrush=symbolBrush, symbolSize=symbolSize)
                else:
                    plt = self.plot.plot(numpy.array(y, copy=False), clear=False,  pen=pen, symbol=symbol,
                                         symbolPen=symbolPen, symbolBrush=symbolBrush,symbolSize=symbolSize)
                self.legend.addItem(plt,pd._title)
                color_index += 1
        self.setWindowTitle(", ".join(titlebar))
        dt = self.get_time()
        # Round to miliseconds
        self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
        self.dateLabel.setText(str(dt.date()))
