from interface.Qt import QtGui, QtCore
from interface.ui import Ui_imageWindow
import pyqtgraph
import numpy
import os
from IPython.core.debugger import Tracer
from .ImageView import ImageView
import datetime

class ImageWindow(QtGui.QMainWindow, Ui_imageWindow):
    def __init__(self, parent = None):
        QtGui.QMainWindow.__init__(self,None)
        self._parent = parent
        self.setupUi(self)
        self.settings = QtCore.QSettings()
        self.plot = ImageView(self.plotFrame, view=pyqtgraph.PlotItem())
        self.plot.ui.roiBtn.hide()
        self.plot.ui.normBtn.hide()
        self.plot.ui.normBtn.hide()
        self.plot.ui.roiPlot.hide()            
        layout = QtGui.QVBoxLayout(self.plotFrame)
        layout.addWidget(self.plot)
        icon_path = os.path.dirname(os.path.realpath(__file__)) + "/../images/logo_48_transparent.png"
        icon = QtGui.QPixmap(icon_path); 
        self.logoLabel.setPixmap(icon)
        self.menuData_Sources.aboutToShow.connect(self.onMenuShow)
        self.actionSaveToJPG.triggered.connect(self.onSaveToJPG)
        self.actionSaveToJPG.setShortcut(QtGui.QKeySequence("Ctrl+P"))
        self.plot_title = str(self.title.text())
        self.title.textChanged.connect(self.onTitleChange)
        self.infoLabel.setText('')
        self._enabled_source = None
        self._prev_source = None
        self._prev_key = None
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
                    if((ds.uuid+key) == self._enabled_source):
                        action.setChecked(True)
                    else:
                        action.setChecked(False)
                    menu.addAction(action)
                    action.triggered.connect(self._source_key_triggered)

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
            if(self._prev_source):
                self._prev_source.unsubscribe(self._prev_key)
            source.subscribe(key)
            self._enabled_source = source.uuid+key
            self._prev_source = source
            self._prev_key = key
            self.title.setText(str(key))  
        else:
            source.unsubscribe(key)
            self._enabled_source = None
            self._prev_source = None
            self._prev_key = None        

    def get_time(self, index=None):
        if index is None:
            index = self.plot.currentIndex
        key = self._enabled_source
        source = self._prev_source
        # There might be no data yet, so no plotdata
        if(source is not None and key in source._plotdata):
            pd = source._plotdata[key]
            dt = datetime.datetime.fromtimestamp(pd._x[index])
            return dt
        else:
            return datetime.datetime.now()
            
    def replot(self):
        key = self._enabled_source
        source = self._prev_source
        # There might be no data yet, so no plotdata
        if(source is not None and key in source._plotdata):
            pd = source._plotdata[key]
            autoLevels = self.actionAuto_Levels.isChecked()
            autoRange = self.actionAuto_Zoom.isChecked()
            autoHistogram = self.actionAuto_Histogram.isChecked()
            transpose_transform = QtGui.QTransform(0, 1, 0,
                                                   1, 0, 0,
                                                   0, 0, 1)            
            xmin = 0
            ymin = 0
            xmax = pd._y.shape[2]
            ymax = pd._y.shape[1]
            transform = QtGui.QTransform()

            if "xmin" in self._prev_source.conf[self._prev_key]:
                xmin = self._prev_source.conf[self._prev_key]['xmin']
            if "ymin" in self._prev_source.conf[self._prev_key]:
                ymin = self._prev_source.conf[self._prev_key]['ymin']
            transform.translate(xmin, ymin)
            transform.scale(1.0/xmax, 1.0/ymax)                        
            if "xmax" in self._prev_source.conf[self._prev_key]:
                xmax = self._prev_source.conf[self._prev_key]['xmax']
            if "ymax" in self._prev_source.conf[self._prev_key]:
                ymax = self._prev_source.conf[self._prev_key]['ymax']
            transform.scale(xmax-xmin, ymax-ymin)            
            transform = transpose_transform*transform

            if "xlabel" in self._prev_source.conf[self._prev_key]:
                self.plot.getView().setLabel('bottom', self._prev_source.conf[self._prev_key]['xlabel'])
            if "ylabel" in self._prev_source.conf[self._prev_key]:
                self.plot.getView().setLabel('left', self._prev_source.conf[self._prev_key]['ylabel'])
                
            if(self.plot.image is not None):               
                last_index = self.plot.image.shape[0]-1
                # Only update if we're in the last index
                if(self.plot.currentIndex == last_index):
                    self.plot.setImage(numpy.array(pd._y), 
                                       transform = transform,
                                       autoRange=autoRange, autoLevels=autoLevels,
                                       autoHistogramRange=autoHistogram)
                    last_index = self.plot.image.shape[0]-1
                    self.plot.setCurrentIndex(last_index)
            else:
                self.plot.setImage(numpy.array(pd._y),
                                   transform = transform,
                                   autoRange=autoRange, autoLevels=autoLevels,
                                   autoHistogramRange=autoHistogram)
                # Make sure to go to the last image
                last_index = self.plot.image.shape[0]-1
                self.plot.setCurrentIndex(last_index)

            self.setWindowTitle(pd._title)
            self.plot.ui.roiPlot.hide()
            dt = self.get_time()
            # Round to miliseconds
            self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
            self.dateLabel.setText(str(dt.date()))

