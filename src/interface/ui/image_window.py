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
                    if(ds.data_type[key] != 'image' and ds.data_type[key] != 'vector'):
                        continue
                    action = QtGui.QAction(key, self)
                    action.setData([ds,key])
                    action.setCheckable(True)
                    if((ds.name()+key) == self._enabled_source):
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
                    

    def set_source_key(self, source, key, enable=True):
        if(enable):
            if(self._prev_source):
                self._prev_source.unsubscribe(self._prev_key)
            source.subscribe(key, self)
            self._enabled_source = source.name()+key
            self._prev_source = source
            self._prev_key = key
            self.title.setText(str(key))
        else:
            source.unsubscribe(key, self)
            self._enabled_source = None
            self._prev_source = None
            self._prev_key = None        

    def _source_key_triggered(self):
        action = self.sender()
        source,key = action.data()
        self.set_source_key(source,key,action.isChecked())

    def get_time(self, index=None):
        if index is None:
            index = self.plot.currentIndex
        key = self._enabled_source
        source = self._prev_source
        # There might be no data yet, so no plotdata
        if(source is not None and self._prev_key in source._plotdata):
            pd = source._plotdata[self._prev_key]
            dt = datetime.datetime.fromtimestamp(pd._x[index])
            return dt
        else:
            return datetime.datetime.now()
            
    def replot(self):
        key = self._enabled_source
        source = self._prev_source
        # There might be no data yet, so no plotdata
        if(source is not None and self._prev_key in source._plotdata):
            pd = source._plotdata[self._prev_key]
            autoLevels = self.actionAuto_Levels.isChecked()
            autoRange = self.actionAuto_Zoom.isChecked()
            autoHistogram = self.actionAuto_Histogram.isChecked()
            transpose_transform = QtGui.QTransform(0, 1, 0,
                                                   1, 0, 0,
                                                   0, 0, 1)            
            xmin = 0
            ymin = 0
            xmax = pd._y.shape[-1]
            ymax = pd._y.shape[-2]
            transform = QtGui.QTransform()

            if source.data_type[self._prev_key] == 'image':
                self.plot.getView().invertY(True)
            else:
                self.plot.getView().invertY(False)

            if "msg" in self._prev_source.conf[self._prev_key]:
                msg = self._prev_source.conf[self._prev_key]['msg']
                self.infoLabel.setText(msg)

            if ("flipy" in self._prev_source.conf[self._prev_key] and
                self._prev_source.conf[self._prev_key]['flipy'] is True):
                self.plot.getView().invertY(not self.plot.getView().getViewBox().yInverted())

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
            # Tranpose images to make x (last dimension) horizontal
            axis_labels = ['left','bottom']
            xlabel_index = 0
            ylabel_index = 1
            if source.data_type[self._prev_key] == 'image':
                transform = transpose_transform*transform
                xlabel_index = (xlabel_index+1)%2
                ylabel_index = (ylabel_index+1)%2

            if "transpose" in self._prev_source.conf[self._prev_key]:
                transform = transpose_transform*transform
                xlabel_index = (xlabel_index+1)%2
                ylabel_index = (ylabel_index+1)%2

            if "xlabel" in self._prev_source.conf[self._prev_key]:
                self.plot.getView().setLabel(axis_labels[xlabel_index], self._prev_source.conf[self._prev_key]['xlabel'])
            if "ylabel" in self._prev_source.conf[self._prev_key]:
                self.plot.getView().setLabel(axis_labels[ylabel_index], self._prev_source.conf[self._prev_key]['ylabel'])
                
            if(self.plot.image is not None and len(self.plot.image.shape) > 2):
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
                if(len(self.plot.image.shape) > 2):
                    # Make sure to go to the last image
                    last_index = self.plot.image.shape[0]-1
                    self.plot.setCurrentIndex(last_index)

            self.setWindowTitle(pd._title)
            self.plot.ui.roiPlot.hide()
            dt = self.get_time()
            # Round to miliseconds
            self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
            self.dateLabel.setText(str(dt.date()))


    def closeEvent(self, event):
        # Unsibscribe all everything
        if self._prev_source is not None:
            self._prev_source.unsubscribe(self._prev_key,self)
        # Remove myself from the interface plot list
        # otherwise we'll be called also on replot
        self._parent._plot_windows.remove(self)
