"""Window to display images"""
from interface.Qt import QtGui
from interface.ui import Ui_imageWindow
import pyqtgraph
import numpy
from interface.ui import DataWindow
import datetime
import logging

class ImageWindow(DataWindow, Ui_imageWindow):
    """Window to display images"""
    def __init__(self, parent=None):
        # This also sets up the UI part
        DataWindow.__init__(self, parent)
        # This is imported here to prevent problems with sphinx
        from .ImageView import ImageView
        self.plot = ImageView(self.plotFrame, view=pyqtgraph.PlotItem())
        self.plot.ui.roiBtn.hide()
        self.plot.ui.normBtn.hide()
        self.plot.ui.normBtn.hide()
        self.plot.ui.roiPlot.hide()
        self._finish_layout()
        self.infoLabel.setText('')
        self.acceptable_data_types = ['image', 'vector']
        self.exclusive_source = True

    def get_time(self, index=None):
        """Returns the time of the given index, or the time of the last data point"""
        if index is None:
            index = self.plot.currentIndex
        # Check if we have enabled_sources
        source = None
        if(self._enabled_sources):
            for ds in self._enabled_sources.keys():
                if(len(self._enabled_sources[ds])):
                    title = self._enabled_sources[ds][0]
                    source = ds
                    break

        # There might be no data yet, so no plotdata
        if(source is not None and title in source.plotdata and
           source.plotdata[title].x is not None):
            pd = source.plotdata[title]
            dt = datetime.datetime.fromtimestamp(pd.x[index])
            return dt
        else:
            return datetime.datetime.now()

    def _image_transform(self, source, title):
        """Returns the appropriate transform for the content"""
        pd = source.plotdata[title]
        xmin = 0
        ymin = 0
        conf = source.conf[title]


        if "xmin" in conf:
            xmin = conf['xmin']
        if "ymin" in conf:
            ymin = conf['ymin']
        translate_transform = QtGui.QTransform().translate(ymin, xmin)
        xmax = pd.y.shape[-1] + xmin
        ymax = pd.y.shape[-2] + ymin

        if "xmax" in conf:
            if(conf['xmax'] <= xmin):
                logging.warning("xmax <= xmin for title %s on %s. Ignoring xmax", title, source.name())
            else:
                xmax = conf['xmax']
        if "ymax" in conf:
            if(conf['ymax'] <= ymin):
                logging.warning("ymax <= ymin for title %s on %s. Ignoring xmax", title, source.name())
            else:
                ymax = conf['ymax']
        # The order of dimensions in the scale call is (y,x) as in the numpy
        # array the last dimension corresponds to the x.
        scale_transform = QtGui.QTransform().scale((ymax-ymin)/pd.y.shape[-2],
                                                   (xmax-xmin)/pd.y.shape[-1])

        transpose_transform = QtGui.QTransform()
        if source.data_type[title] == 'image':
            transpose_transform *= QtGui.QTransform(0, 1, 0,
                                                    1, 0, 0,
                                                    0, 0, 1)
        if "transpose" in conf:
            transpose_transform *= QtGui.QTransform(0, 1, 0,
                                                    1, 0, 0,
                                                    0, 0, 1)
        transform = scale_transform*translate_transform*transpose_transform

        # print '|%f %f %f|' % (transform.m11(), transform.m12(), transform.m13())
        # print '|%f %f %f|' % (transform.m21(), transform.m22(), transform.m23())
        # print '|%f %f %f|' % (transform.m31(), transform.m32(), transform.m33())
        return transform

    def _configure_axis(self, source, title):
        """Configures the x and y axis of the plot, according to the
        source/title configuration and content type"""
        conf = source.conf[title]
        if source.data_type[title] == 'image':
            self.plot.getView().invertY(True)
        else:
            self.plot.getView().invertY(False)
        if ("flipy" in conf and conf['flipy'] is True):
            self.plot.getView().invertY(not self.plot.getView().getViewBox().yInverted())

        # Tranpose images to make x (last dimension) horizontal
        axis_labels = ['left', 'bottom']
        xlabel_index = 0
        ylabel_index = 1
        if source.data_type[title] == 'image':
            xlabel_index = (xlabel_index+1)%2
            ylabel_index = (ylabel_index+1)%2

        if "transpose" in conf:
            xlabel_index = (xlabel_index+1)%2
            ylabel_index = (ylabel_index+1)%2

        if "xlabel" in conf:
            self.plot.getView().setLabel(axis_labels[xlabel_index], conf['xlabel']) #pylint: disable=no-member
        if "ylabel" in conf:
            self.plot.getView().setLabel(axis_labels[ylabel_index], conf['ylabel'])  #pylint: disable=no-member

    def replot(self):
        """Replot data"""
        for source, title in self.source_and_titles():
            if(title not in source.plotdata):
                continue
            pd = source.plotdata[title]
            if(pd.y is None):
                continue
            auto_levels = self.actionAuto_Levels.isChecked()
            auto_range = self.actionAuto_Zoom.isChecked()
            auto_histogram = self.actionAuto_Histogram.isChecked()

            conf = source.conf[title]
            if "msg" in conf:
                msg = conf['msg']
                self.infoLabel.setText(msg)

            self._configure_axis(source, title)
            transform = self._image_transform(source, title)

            if(self.plot.image is None or # Plot if first image
               len(self.plot.image.shape) < 3 or # Plot if there's no history
               self.plot.image.shape[0]-1 == self.plot.currentIndex): # Plot if we're at the last image in history
                self.plot.setImage(numpy.array(pd.y, copy=False),
                                   transform=transform,
                                   autoRange=auto_range, autoLevels=auto_levels,
                                   autoHistogramRange=auto_histogram)
                if(len(self.plot.image.shape) > 2):
                    # Make sure to go to the last image
                    last_index = self.plot.image.shape[0]-1
                    self.plot.setCurrentIndex(last_index)

            self.setWindowTitle(pd.title)
            self.plot.ui.roiPlot.hide()
            dt = self.get_time()
            # Round to miliseconds
            self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
            self.dateLabel.setText(str(dt.date()))

