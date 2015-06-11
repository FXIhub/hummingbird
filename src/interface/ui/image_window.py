"""Window to display images"""
from interface.Qt import QtGui, QtCore
from interface.ui import Ui_imageWindow
from interface.ui import DataWindow
import utils.array
import pyqtgraph
import numpy
import datetime
import logging
import os

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
        self.acceptable_data_types = ['image', 'vector', 'triple', 'running_hist']
        self.exclusive_source = True
        self.alert = False
        self.meanmap = None
        self.vline = None
        self.hline = None

        self.settingsWidget.setVisible(self.actionPlotSettings.isChecked())
        self.settingsWidget.ui.colormap_min.editingFinished.connect(self.set_colormap_range)
        self.settingsWidget.ui.colormap_max.editingFinished.connect(self.set_colormap_range)
        self.settingsWidget.ui.colormap_min.setValidator(QtGui.QDoubleValidator())
        self.settingsWidget.ui.colormap_max.setValidator(QtGui.QDoubleValidator())
        self.settingsWidget.ui.colormap_full_range.clicked.connect(self.set_colormap_full_range)

        self.settingsWidget.ui.histogram_show.toggled.connect(self.plot.getHistogramWidget().setVisible)
        self.actionHistogram.triggered.connect(self.plot.getHistogramWidget().setVisible)
        self.actionHistogram.triggered.connect(self.settingsWidget.ui.histogram_show.setChecked)
        self.settingsWidget.ui.histogram_show.toggled.connect(self.actionHistogram.setChecked)
        
        self.settingsWidget.ui.x_show.toggled.connect(self.toggle_axis)
        self.actionX_axis.triggered.connect(self.toggle_axis)        
        self.settingsWidget.ui.y_show.toggled.connect(self.toggle_axis)
        self.actionY_axis.triggered.connect(self.toggle_axis)        
        self.settingsWidget.ui.histogram_show.toggled.connect(self.toggle_axis)
        self.actionHistogram.triggered.connect(self.toggle_axis)

        self.set_sounds_and_volume()
        self.actionSound_on_off.triggered.connect(self.toggle_alert)
                
        self.plot.getHistogramWidget().region.sigRegionChangeFinished.connect(self.set_colormap_range)
        self.actionPlotSettings.triggered.connect(self.toggle_settings)

        # Make sure to disable native menus
        self.plot.getView().setMenuEnabled(False)
        self.plot.getHistogramWidget().vb.setMenuEnabled(False)
        self.x_axis_name = 'left'
        self.y_axis_name = 'bottom'
        self._set_logscale_lookuptable()

        self.running_hist_initialised = False

    def set_sounds_and_volume(self):
        self.soundsGroup = QtGui.QActionGroup(self.menuSounds)
        self.soundsGroup.setExclusive(True)
        self.actionBeep.setActionGroup(self.soundsGroup)
        self.actionBeep.triggered.connect(self.toggle_sounds)
        self.actionClick.setActionGroup(self.soundsGroup)
        self.actionClick.triggered.connect(self.toggle_sounds)
        self.actionPunch.setActionGroup(self.soundsGroup)
        self.actionPunch.triggered.connect(self.toggle_sounds)
        self.actionWhack.setActionGroup(self.soundsGroup)
        self.actionWhack.triggered.connect(self.toggle_sounds)
        self.actionSharp.setActionGroup(self.soundsGroup)
        self.actionSharp.triggered.connect(self.toggle_sounds)
        self.actionGlass.setActionGroup(self.soundsGroup)
        self.actionGlass.triggered.connect(self.toggle_sounds)
        self.sound = 'beep'
        
        self.volumeGroup = QtGui.QActionGroup(self.menuVolume)
        self.volumeGroup.setExclusive(True)
        self.actionHigh.setActionGroup(self.volumeGroup)
        self.actionHigh.triggered.connect(self.toggle_volume)
        self.actionMedium.setActionGroup(self.volumeGroup)
        self.actionMedium.triggered.connect(self.toggle_volume)
        self.actionLow.setActionGroup(self.volumeGroup)
        self.actionLow.triggered.connect(self.toggle_volume)
        self.volume = 1

    def get_time_and_msg(self, index=None):
        """Returns the time/msg of the given index, or the time/msg of the last data point"""
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
            msg = pd.l[index]
        else:
            dt = datetime.datetime.now()
            msg = ''
        return dt, msg
        
    def _image_transform(self, img, source, title):
        """Returns the appropriate transform for the content"""
        xmin = 0
        ymin = 0
        conf = source.conf[title]

        if "xmin" in conf:
            xmin = conf['xmin']
        if "ymin" in conf:
            ymin = conf['ymin']

        translate_transform = QtGui.QTransform().translate(ymin, xmin)
        xmax = img.shape[-1] + xmin
        ymax = img.shape[-2] + ymin

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
        scale_transform = QtGui.QTransform().scale((ymax-ymin)/img.shape[-2],
                                                   (xmax-xmin)/img.shape[-1])

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

        self.x_axis_name =  axis_labels[xlabel_index]
        self.y_axis_name =  axis_labels[ylabel_index]
        if(self.actionX_axis.isChecked()):
            if(self.settingsWidget.ui.x_label_auto.isChecked() and 
               "xlabel" in conf):
                self.plot.getView().setLabel(axis_labels[xlabel_index], conf['xlabel']) #pylint: disable=no-member
            else:
                self.plot.getView().setLabel(axis_labels[xlabel_index], self.settingsWidget.ui.x_label.text()) #pylint: disable=no-member

        if(self.actionY_axis.isChecked()):
            if(self.settingsWidget.ui.y_label_auto.isChecked() and 
               "ylabel" in conf):
                self.plot.getView().setLabel(axis_labels[ylabel_index], conf['ylabel'])  #pylint: disable=no-member
            else:
                self.plot.getView().setLabel(axis_labels[ylabel_index], self.settingsWidget.ui.y_label.text()) #pylint: disable=no-member

    def _set_logscale_lookuptable(self):
        N = 1000000
        self.lut = numpy.empty((N,4), dtype=numpy.ubyte)
        grad = numpy.log(numpy.linspace(1, 1e5, N))
        self.lut[:,:3] = (255 * grad / grad.max()).reshape(N,1)
        self.lut[:, 3] = 255
        
    def _set_logscale(self, source, title):
        conf = source.conf[title]
        if source.data_type[title] == 'image' and ("log" in conf):
            if conf["log"]:
                self.plot.imageItem.setLookupTable(self.lut)

    def _fill_meanmap(self, triple, conf):
        xbins, ybins = (100,100)
        xmin, xmax = (0,100)
        ymin, ymax = (0,100)
        if 'xbins' in conf:
            xbins = conf['xbins']
        if 'ybins' in conf:
            ybins = conf['ybins']
        if 'xmin' in conf:
            xmin = conf['xmin']
        if 'ymin' in conf:
            ymin = conf['ymin']
        if 'xmax' in conf:
            xmax = conf['xmax']
        if 'ymax' in conf:
            ymax = conf['ymax']
                        
        if self.meanmap is None:
            self.meanmap = numpy.zeros((3, ybins, xbins), dtype=float)
            self.meanmap_dx = (xmax - float(xmin))/xbins
            self.meanmap_dy = (ymax - float(ymin))/ybins
            translate_transform = QtGui.QTransform().translate(ymin-self.meanmap_dy/2., xmin-self.meanmap_dx/2.)
            scale_transform = QtGui.QTransform().scale(self.meanmap_dy, self.meanmap_dx)
            transpose_transform = QtGui.QTransform()
            transpose_transform *= QtGui.QTransform(0, 1, 0,
                                                    1, 0, 0,
                                                    0, 0, 1)
            self.meanmap_transform = scale_transform*translate_transform*transpose_transform
        ix = numpy.round((triple[0] - xmin)/self.meanmap_dx)
        if (ix < 0):
            ix = 0
        elif (ix >= xbins):
            ix = xbins - 1
        iy = numpy.round((triple[1] - ymin)/self.meanmap_dy)
        if (iy < 0):
            iy = 0
        elif (iy >= ybins):
            iy = ybins - 1
        self.meanmap[0,iy,ix] += triple[2]
        self.meanmap[1,iy,ix] += 1
        visited = self.meanmap[1] != 0
        if (self.settingsWidget.ui.show_visitedmap.isChecked()):
            return visited, self.meanmap_transform, triple[0], triple[1]
        elif (self.settingsWidget.ui.show_heatmap.isChecked()):
            return self.meanmap[1], self.meanmap_transform, triple[0], triple[1]
        else:
            if len(self.meanmap[1][visited]):
                self.meanmap[2][visited] = self.meanmap[0][visited]/self.meanmap[1][visited]
            return self.meanmap[2], self.meanmap_transform, triple[0], triple[1]

    def _show_crosshair(self, x,y):
        if (self.actionCrosshair.isChecked()):
            if self.vline is None:
                self.vline = pyqtgraph.InfiniteLine(angle=90, movable=False)
                self.plot.getView().addItem(self.vline)
            if self.hline is None:
                self.hline = pyqtgraph.InfiniteLine(angle=0, movable=False)
                self.plot.getView().addItem(self.hline)
            self.hline.setPos(y)
            self.vline.setPos(x)
        else:
            if self.vline is not None:
                self.plot.getView().removeItem(self.vline)
                self.vline = None
            if self.hline is not None:
                self.plot.getView().removeItem(self.hline)
                self.hline = None
        
    def init_running_hist(self,source, title):
        print "init"
        conf = source.conf[title]
        self.settingsWidget.ui.runningHistWindow.setText(str(conf["window"]))
        self.settingsWidget.ui.runningHistBins.setText(str(conf["bins"]))
        self.settingsWidget.ui.runningHistMin.setText(str(conf["hmin"]))
        self.settingsWidget.ui.runningHistMax.setText(str(conf["hmax"]))
        self.running_hist_initialised = True

    def replot(self):
        """Replot data"""
        for source, title in self.source_and_titles():
            if(title not in source.plotdata):
                continue
            pd = source.plotdata[title]
            if(pd.y is None or len(pd.y) == 0):
                continue
            
            conf = source.conf[title]
            if "alert" in conf and self.alert:
                alert = conf['alert']
                if alert:
                    os.system('afplay -v %f src/interface/ui/sounds/%s.wav &' %(self.volume,self.sound))
            
            if(self.settingsWidget.ui.ignore_source.isChecked() is False):
                if 'vmin' in conf and conf['vmin'] is not None:
                    cmin = self.settingsWidget.ui.colormap_min
                    cmin.setText(str(conf['vmin']))
                if 'vmax' in conf and conf['vmax'] is not None:
                    cmax = self.settingsWidget.ui.colormap_max
                    cmax.setText(str(conf['vmax']))
                if 'vmin' in conf or 'vmax' in conf:
                    self.set_colormap_range()

            if conf["data_type"] == "running_hist":
                if not self.running_hist_initialised:
                    self.init_running_hist(source, title)
                window = int(self.settingsWidget.ui.runningHistWindow.text())
                bins   = int(self.settingsWidget.ui.runningHistBins.text())
                hmin   = int(self.settingsWidget.ui.runningHistMin.text())
                hmax   = int(self.settingsWidget.ui.runningHistMax.text())
                v      = pd.y[-1]
                length = pd.maxlen
                img = utils.array.runningHistogram(v, title, length, window, bins, hmin, hmax)
                print img.sum()
                if not img.shape[0]:
                    continue
            else:
                img = numpy.array(pd.y, copy=False)
            self._configure_axis(source, title)
            transform = self._image_transform(img, source, title)
            
            if conf["data_type"] == "running_hist":
                translate_transform = QtGui.QTransform().translate(0, hmin)
                scale_transform = QtGui.QTransform().scale(1, float(hmax-hmin)/float(bins))
                transform = scale_transform*translate_transform

            if(self.plot.image is None or # Plot if first image
               len(self.plot.image.shape) < 3 or # Plot if there's no history
               self.plot.image.shape[0]-1 == self.plot.currentIndex): # Plot if we're at the last image in history
                auto_levels = False
                auto_range = False
                auto_histogram = False
                if(self.plot.image is None and self.restored == False):
                    # Turn on auto on the first image
                    auto_levels = True
                    auto_rage = True
                    auto_histogram = True
                if "data_type" in conf and conf["data_type"] == "triple":
                    img, transform, x, y = self._fill_meanmap(img[0], conf)
                else:
                    x, y = (0,0)
                if (self.settingsWidget.ui.show_trend.isChecked()):
                    _trend = getattr(numpy, str(self.settingsWidget.ui.trend_options.currentText()))
                    img = _trend(img, axis=0)
                self.plot.setImage(img,
                                   transform=transform,
                                   autoRange=auto_range, autoLevels=auto_levels,
                                   autoHistogramRange=auto_histogram)

                self._show_crosshair(x,y)
                if(len(self.plot.image.shape) > 2):
                    # Make sure to go to the last image
                    last_index = self.plot.image.shape[0]-1
                    self.plot.setCurrentIndex(last_index, autoHistogramRange=auto_histogram)
                self._set_logscale(source, title)

            self.setWindowTitle(pd.title)
            dt, msg = self.get_time_and_msg()
            self.infoLabel.setText(msg)
            # Round to miliseconds
            self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
            self.dateLabel.setText(str(dt.date()))

    def set_colormap_full_range(self):
        """Ensures that the colormap covers the full range of values in the data"""
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
        """Set the minimum and maximum values for the colormap"""
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
        """Show/hide settings widget"""
        # if(visible):
        #     new_size = self.size() + QtCore.QSize(0,self.settingsWidget.sizeHint().height()+10)
        # else:
        #     new_size = self.size() - QtCore.QSize(0,self.settingsWidget.sizeHint().height()+10)
        # self.resize(new_size)
        self.settingsWidget.setVisible(visible)

    def get_state(self, _settings = None):
        """Returns settings that can be used to restore the widget to the current state"""
        settings = _settings or {}
        settings['window_type'] = 'ImageWindow'
        settings['actionPlotSettings'] = self.actionPlotSettings.isChecked()
        # Disabled QLineEdits are confusing to QSettings. Store a dummy _
        settings['x_label'] = "_" + self.settingsWidget.ui.x_label.text()
        settings['y_label'] = "_" + self.settingsWidget.ui.y_label.text()
        settings['x_label_auto'] = self.settingsWidget.ui.x_label_auto.isChecked()
        settings['y_label_auto'] = self.settingsWidget.ui.y_label_auto.isChecked()
        settings['colormap_min'] = str(self.settingsWidget.ui.colormap_min.text())
        settings['colormap_max'] = str(self.settingsWidget.ui.colormap_max.text())
        settings['transpose'] = self.settingsWidget.ui.transpose.currentText()
        settings['flipy'] = self.settingsWidget.ui.flipy.currentText()
        settings['viewbox'] = self.plot.getView().getViewBox().getState()
        settings['x_view'] = self.actionX_axis.isChecked()
        settings['y_view'] = self.actionY_axis.isChecked()
        settings['histogram_view'] = self.actionHistogram.isChecked()
        
        return DataWindow.get_state(self, settings)

    def restore_from_state(self, settings, data_sources):
        """Restores the widget to the same state as when the settings were generated"""
        self.actionPlotSettings.setChecked(settings['actionPlotSettings'])
        self.actionPlotSettings.triggered.emit(self.actionPlotSettings.isChecked())
        self.settingsWidget.ui.x_label.setText(settings['x_label'][1:])
        self.settingsWidget.ui.y_label.setText(settings['y_label'][1:])
        self.settingsWidget.ui.x_label_auto.setChecked(settings['x_label_auto'])
        self.settingsWidget.ui.x_label_auto.toggled.emit(settings['x_label_auto'])
        self.settingsWidget.ui.y_label_auto.setChecked(settings['y_label_auto'])
        self.settingsWidget.ui.y_label_auto.toggled.emit(settings['y_label_auto'])
        self.settingsWidget.ui.colormap_min.setText(settings['colormap_min'])
        self.settingsWidget.ui.colormap_max.setText(settings['colormap_max'])
        self.settingsWidget.ui.colormap_max.editingFinished.emit()
        transpose = self.settingsWidget.ui.transpose
        transpose.setCurrentIndex(transpose.findText(settings['transpose']))
        flipy = self.settingsWidget.ui.flipy
        flipy.setCurrentIndex(flipy.findText(settings['flipy']))
        self.plot.getView().getViewBox().setState(settings['viewbox'])
        self.actionX_axis.setChecked(settings['x_view'])
        self.actionX_axis.triggered.emit(settings['x_view'])
        self.actionY_axis.setChecked(settings['y_view'])
        self.actionY_axis.triggered.emit(settings['y_view'])
        self.actionHistogram.setChecked(settings['histogram_view'])
        self.actionHistogram.triggered.emit(settings['histogram_view'])

        return DataWindow.restore_from_state(self, settings, data_sources)

    def toggle_axis(self, visible):
        if(self.sender() == self.actionX_axis or 
           self.sender() == self.settingsWidget.ui.x_show):
            self.plot.getView().getAxis(self.x_axis_name).setVisible(visible)
            self.settingsWidget.ui.x_show.setChecked(visible)
            self.actionX_axis.setChecked(visible)

        if(self.sender() == self.actionY_axis or 
           self.sender() == self.settingsWidget.ui.y_show):
            self.plot.getView().getAxis(self.y_axis_name).setVisible(visible)
            self.settingsWidget.ui.y_show.setChecked(visible)
            self.actionY_axis.setChecked(visible)

        if(self.sender() == self.actionHistogram or 
           self.sender() == self.settingsWidget.ui.histogram_show):
            self.plot.getHistogramWidget().setVisible(visible)
            self.settingsWidget.ui.histogram_show.setChecked(visible)
            self.actionHistogram.setChecked(visible)

    def toggle_alert(self, activated):
        self.alert = activated

    def toggle_sounds(self):
        self.sound = str(self.soundsGroup.checkedAction().text())

    def toggle_volume(self):
        volume = str(self.volumeGroup.checkedAction().text())
        if volume == "High":
            self.volume = 10
        elif volume == "Medium":
            self.volume = 1
        elif volume == "Low":
            self.volume = 0.1
    
        
            
