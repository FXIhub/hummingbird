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
        # self.plot = pyqtgraph.GraphicsLayoutWidget()
        # vb = self.plot.addViewBox()
        # vb.setAspectLocked()
        # grad = pyqtgraph.GradientEditorItem(orientation='right')
        # self.plot.addItem(grad, 0, 1)
        # plt = pyqtgraph.PlotItem()
        # img = pyqtgraph.ImageItem()
        # plt.addItem(img)
        # vb.addItem(plt)
        self.plot = ImageView(self.plotFrame, view=pyqtgraph.PlotItem())
        self.plot.ui.roiBtn.hide()
        self.plot.ui.normBtn.hide()
        self.plot.ui.normBtn.hide()
        self.plot.ui.roiPlot.hide()
            
        layout = QtGui.QVBoxLayout(self.plotFrame)
        layout.addWidget(self.plot)
#        self.plot = img
        icon_path = os.path.dirname(os.path.realpath(__file__)) + "/../images/logo_48_transparent.png"
        icon = QtGui.QPixmap(icon_path); 
        self.logoLabel.setPixmap(icon)
        self.menuData_Sources.aboutToShow.connect(self.onMenuShow)
        self.actionSaveToJPG.triggered.connect(self.onSaveToJPG)
        #self.actionSave_to_JPG.setShortcut(QtGui.QKeySequence("Ctrl+P"))
        self.plot_title = str(self.title.text())
        self.title.textChanged.connect(self.onTitleChange)
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
        else:
            source.unsubscribe(key)
            self._enabled_source = None
            self._prev_source = None
            self._prev_key = None        

    def get_time(self, index=None):
        if index is None:
            index = self.plot.currentIndex
        key = self._enabled_source
        # There might be no data yet, so no plotdata
        if(key in self._parent._plotdata):
            pd = self._parent._plotdata[key]
            dt = datetime.datetime.fromtimestamp(pd._x[index])
            return dt
        else:
            return datetime.datetime.now()
            
    def replot(self):
        key = self._enabled_source
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
                                                                    0, 0, 1),
                                       autoRange=False, autoLevels=False)
                    last_index = self.plot.image.shape[0]-1
                    self.plot.setCurrentIndex(last_index)
            else:
                self.plot.setImage(numpy.array(pd._y),
                                   transform = QtGui.QTransform(0, 1, 0,
                                                                1, 0, 0,
                                                                0, 0, 1),
                                   autoRange=False, autoLevels=False)
            self.setWindowTitle(pd._title)
            self.plot.ui.roiPlot.hide()
            dt = self.get_time()
            # Round to miliseconds
            self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
            self.dateLabel.setText(str(dt.date()))

