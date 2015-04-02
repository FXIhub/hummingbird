"""Window to display images"""
from interface.Qt import QtGui, QtCore
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
        from .image_view import ImageView
        self.plot = ImageView(self, view=pyqtgraph.PlotItem())
        self._finish_layout()
        self.infoLabel.setText('')
        self.acceptable_data_types = ['image', 'vector']
        self.exclusive_source = True

        self.settingsWidget.setVisible(self.actionPlotSettings.isChecked())
        self.settingsWidget.ui.colormap_min.editingFinished.connect(self.set_colormap_range)
        self.settingsWidget.ui.colormap_max.editingFinished.connect(self.set_colormap_range)
        self.settingsWidget.ui.colormap_min.setValidator(QtGui.QDoubleValidator())
        self.settingsWidget.ui.colormap_max.setValidator(QtGui.QDoubleValidator())
        self.settingsWidget.ui.colormap_full_range.clicked.connect(self.set_colormap_full_range)

        self.plot.getHistogramWidget().region.sigRegionChangeFinished.connect(self.set_colormap_range)
        self.actionPlotSettings.triggered.connect(self.toggle_settings)

        # Make sure to disable native menus
        self.plot.getView().setMenuEnabled(False)
        self.plot.getHistogramWidget().vb.setMenuEnabled(False)

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
        if(self.settingsWidget.ui.transpose.currentText() == 'Yes' or
           (self.settingsWidget.ui.transpose.currentText() == 'Auto' 
            and "transpose" in conf)):
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
        if(self.settingsWidget.ui.flipy.currentText() == 'Yes' or
           (self.settingsWidget.ui.flipy.currentText() == 'Auto' and
            "flipy" in conf and conf['flipy'] is True)):
            self.plot.getView().invertY(not self.plot.getView().getViewBox().yInverted())

        # Tranpose images to make x (last dimension) horizontal
        axis_labels = ['left', 'bottom']
        xlabel_index = 0
        ylabel_index = 1
        if source.data_type[title] == 'image':
            xlabel_index = (xlabel_index+1)%2
            ylabel_index = (ylabel_index+1)%2

        if(self.settingsWidget.ui.transpose.currentText() == 'Yes' or
           (self.settingsWidget.ui.transpose.currentText() == 'Auto' 
            and "transpose" in conf)):
            xlabel_index = (xlabel_index+1)%2
            ylabel_index = (ylabel_index+1)%2

        if(self.settingsWidget.ui.x_label_auto.isChecked() and 
           "xlabel" in conf):
            self.plot.getView().setLabel(axis_labels[xlabel_index], conf['xlabel']) #pylint: disable=no-member
        else:
            self.plot.getView().setLabel(axis_labels[xlabel_index], self.settingsWidget.ui.x_label.text()) #pylint: disable=no-member
        if(self.settingsWidget.ui.y_label_auto.isChecked() and 
           "ylabel" in conf):
            self.plot.getView().setLabel(axis_labels[ylabel_index], conf['ylabel'])  #pylint: disable=no-member
        else:
            self.plot.getView().setLabel(axis_labels[ylabel_index], self.settingsWidget.ui.y_label.text()) #pylint: disable=no-member

    def replot(self):
        """Replot data"""
        for source, title in self.source_and_titles():
            if(title not in source.plotdata):
                continue
            pd = source.plotdata[title]
            if(pd.y is None):
                continue

            conf = source.conf[title]
            if "msg" in conf:
                msg = conf['msg']
                self.infoLabel.setText(msg)

            self._configure_axis(source, title)
            transform = self._image_transform(source, title)
            
            if(self.plot.image is None or # Plot if first image
               len(self.plot.image.shape) < 3 or # Plot if there's no history
               self.plot.image.shape[0]-1 == self.plot.currentIndex): # Plot if we're at the last image in history
                auto_levels = False
                auto_range = False
                auto_histogram = False
                if(self.plot.image is None):
                    # Turn on auto on the first image
                    auto_levels = True
                    auto_rage = True
                    auto_histogram = True
                self.plot.setImage(numpy.array(pd.y, copy=False),
                                   transform=transform,
                                   autoRange=auto_range, autoLevels=auto_levels,
                                   autoHistogramRange=auto_histogram)
                if(len(self.plot.image.shape) > 2):
                    # Make sure to go to the last image
                    last_index = self.plot.image.shape[0]-1
                    self.plot.setCurrentIndex(last_index, autoHistogramRange=auto_histogram)


            self.setWindowTitle(pd.title)
#            self.plot.ui.roiPlot.hide()
            dt = self.get_time()
            # Round to miliseconds
            self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
            self.dateLabel.setText(str(dt.date()))

    def set_colormap_full_range(self):
        if(self.plot.image is None):
            return
        
        cmin = self.settingsWidget.ui.colormap_min
        cmax = self.settingsWidget.ui.colormap_max
        data_min = numpy.min(self.plot.image)
        data_max = numpy.max(self.plot.image)
        cmin.setText(str(data_min))
        cmax.setText(str(data_max))
        self.set_colormap_range()

    def set_colormap_range(self):
        cmin = self.settingsWidget.ui.colormap_min
        cmax = self.settingsWidget.ui.colormap_max
        region = self.plot.getHistogramWidget().region

        if(self.sender() == region):
            cmin.setText(str(region.getRegion()[0]))
            cmax.setText(str(region.getRegion()[1]))
            return

        # Sometimes the values in the lineEdits are
        # not proper floats so we get ValueErrors
        try:
            # If necessary swap min and max
            if(float(cmin.text()) > float(cmax.text())):
                _tmp = cmin.text()
                cmin.setText(cmax.text())
                cmax.setText(_tmp)

            region = [float(cmin.text()), float(cmax.text())]
            self.plot.getHistogramWidget().region.setRegion(region)
        except ValueError:
            return

    def toggle_settings(self, visible):
        # if(visible):
        #     new_size = self.size() + QtCore.QSize(0,self.settingsWidget.sizeHint().height()+10)
        # else:
        #     new_size = self.size() - QtCore.QSize(0,self.settingsWidget.sizeHint().height()+10)
        # self.resize(new_size)
        self.settingsWidget.setVisible(visible)

