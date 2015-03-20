from interface.Qt import QtGui, QtCore
from interface.ui import Ui_imageWindow
import pyqtgraph
import numpy
import os
from IPython.core.debugger import Tracer
from data_window import DataWindow
import datetime

class ImageWindow(DataWindow, Ui_imageWindow):
    def __init__(self, parent = None):
        # This also sets up the UI part
        DataWindow.__init__(self,parent)
        # This is imported here to prevent problems with sphinx
        from .ImageView import ImageView
        self.plot = ImageView(self.plotFrame, view=pyqtgraph.PlotItem())
        self.plot.ui.roiBtn.hide()
        self.plot.ui.normBtn.hide()
        self.plot.ui.normBtn.hide()
        self.plot.ui.roiPlot.hide()
        self.finish_layout()
        self.infoLabel.setText('')
        self.acceptable_data_types = ['image', 'vector']
        self.exclusive_source = True
            
    def replot(self):
        for source,title in self.source_and_titles():
            if(title not in source._plotdata):
                continue
            pd = source._plotdata[title]
            if(pd._y is None):
                continue
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

            if source.data_type[title] == 'image':
                self.plot.getView().invertY(True)
            else:
                self.plot.getView().invertY(False)

            conf = source.conf[title]
            if "msg" in conf:
                msg = conf['msg']
                self.infoLabel.setText(msg)

            if ("flipy" in conf and conf['flipy'] is True):
                self.plot.getView().invertY(not self.plot.getView().getViewBox().yInverted())

            if "xmin" in conf:
                xmin = conf['xmin']
            if "ymin" in conf:
                ymin = conf['ymin']
            transform.translate(xmin, ymin)
            transform.scale(1.0/xmax, 1.0/ymax)                        
            if "xmax" in conf:
                xmax = conf['xmax']
            if "ymax" in conf:
                ymax = conf['ymax']
            transform.scale(xmax-xmin, ymax-ymin)
            # Tranpose images to make x (last dimension) horizontal
            axis_labels = ['left','bottom']
            xlabel_index = 0
            ylabel_index = 1
            if source.data_type[title] == 'image':
                transform = transpose_transform*transform
                xlabel_index = (xlabel_index+1)%2
                ylabel_index = (ylabel_index+1)%2

            if "transpose" in conf:
                transform = transpose_transform*transform
                xlabel_index = (xlabel_index+1)%2
                ylabel_index = (ylabel_index+1)%2

            if "xlabel" in conf:
                self.plot.getView().setLabel(axis_labels[xlabel_index], conf['xlabel'])
            if "ylabel" in conf:
                self.plot.getView().setLabel(axis_labels[ylabel_index], conf['ylabel'])

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

