# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Window to display 2D plots"""
import datetime
import os

import numpy
import pyqtgraph

from hummingbird import utils
from ..colorbar import ColorBar
from ..Qt import QtCore, QtGui
from . import DataWindow, LinePlotSettings, Ui_plotWindow
from .pg_time_axis import DateAxisItem


class Histogram(object):
    def __init__(self, hmin, hmax, bins):
        self._bins = bins
        self._range = (hmin, hmax)
        self._step = (hmax-hmin) / float(bins)
        self._histogram = numpy.zeros(self._bins)
        self._last_add_index = 0

    def _value_to_index(self, value):
        index = int((value - self._range[0]) / self._step)
        if index < 0 or index >= self._bins:
            return None
        else:
            return index
        
    def add_value(self, value):
        index = self._value_to_index(value)
        if index is not None:
            self._histogram[index] += 1

    def add_values_from_ringbuffer(self, ringbuffer):
        current_index = ringbuffer.number_of_added_elements
        number_of_values_to_add = current_index-self._last_add_index
        if number_of_values_to_add > 0:
            values = numpy.array(ringbuffer, copy=False)[-(current_index-self._last_add_index):]
        else:
            return
        for this_value in values:
            self.add_value(this_value)
        self._last_add_index = current_index

    def reset(self):
        print("Reset histogram!")
        self._histogram[:] = 0
        self._last_add_index = 0

    @property
    def values_x(self):
        return numpy.linspace(self._range[0] + self._step/2., self._range[1] - self._step/2., self._bins)

    @property
    def values_y(self):
        return self._histogram

class NormalizedHistogram(Histogram):
    def __init__(self, hmin, hmax, bins):
        super(NormalizedHistogram, self).__init__(hmin, hmax, bins)
        self._weight = numpy.zeros(self._histogram.shape)

    def add_value(self, value, weight):
        index = self._value_to_index(value)
        if index is not None:
            self._histogram[index] += weight
            self._weight[index] += 1.

    def add_values_from_ringbuffer(self, ringbuffer):
        current_index = ringbuffer.number_of_added_elements
        number_of_values_to_add = (current_index-self._last_add_index)
        if number_of_values_to_add > 0:
            values = numpy.array(ringbuffer, copy=False)[-number_of_values_to_add:, 0]
            weights = numpy.array(ringbuffer, copy=False)[-number_of_values_to_add:, 1]
        else:
            return
        for this_value, this_weight in zip(values, weights):
            self.add_value(this_value, this_weight)
        self._last_add_index = current_index

    def reset(self):
        super(NormalizedHistogram, self).reset()
        self._weight[:] = 0.

    @property
    def values_y(self):
        return_hist = self._histogram.copy()
        return_hist[self._weight > 0.] /= self._weight[self._weight > 0.]
        return return_hist
            
class PlotWindow(DataWindow, Ui_plotWindow):
    """Window to display 2D plots"""
    acceptable_data_types = ['scalar', 'vector', 'tuple', 'triple', 'running_hist', 'histogram' , 'normalized_histogram']

    def __init__(self, parent=None):
        DataWindow.__init__(self, parent)
        self.plot = pyqtgraph.PlotWidget(self.plotFrame, antialiasing=True)
        self.plot.hideAxis('bottom')
        self.legend = self.plot.addLegend()
        self.legend.hide()
        self._finish_layout()
        self.actionLegend_Box.triggered.connect(self.on_view_legend_box)
        self.actionX_axis.triggered.connect(self.on_view_x_axis)
        self.actionY_axis.triggered.connect(self.on_view_y_axis)
        self.exclusive_source = False
        self.line_colors = [(252, 175, 62), (114, 159, 207), (255, 255, 255),
                            (239, 41, 41), (138, 226, 52), (173, 127, 168)]
        self.colorbar = None
        self.colormap = None
        self.current_index = -1
        self.last_vector_y = {}
        self.last_vector_x = None
        self.hline = None
        self.vline = None
        self.hline_color = (0,204,0)
        self.vline_color = (204,0,0)
        self._settings_diag = LinePlotSettings(self)
        self._histograms = {}
        self._normalized_histograms = {}
        self.updateFonts()

        self.plot.scene().sigMouseMoved.connect(self._onMouseMoved)

        # Make sure menubar is attached to the main window
        self.menubar = self.menuBar()
        self.menubar.setNativeMenuBar(False)
        self.time_on_x_axis = False
        self.time_axis = DateAxisItem(orientation='bottom')

    def on_view_legend_box(self):
        """Show/hide legend box"""
        action = self.sender()
        if(action.isChecked()):
            self.legend.show()
        else:
            self.legend.hide()

    def on_view_x_axis(self):
        """Show/hide X axis"""
        action = self.sender()
        if(action.isChecked()):
            self.plot.showAxis('bottom')
        else:
            self.plot.hideAxis('bottom')

    def on_view_y_axis(self):
        """Show/hide Y axis"""
        action = self.sender()
        if(action.isChecked()):
            self.plot.showAxis('left')
        else:
            self.plot.hideAxis('left')

    def _on_plot_settings(self):
        """Show the plot settings dialog"""
        self._settings_diag.histAutorange.toggled.connect(self._on_histogram_autorange)
        if(self._settings_diag.exec_()):
            self._settings_diag._read_bg_file()
            # Show changes immediately
            self.replot()

    def _on_histogram_autorange(self, checked):
        if checked:
            self._settings_diag.histMin.setEnabled(False)
            self._settings_diag.histMax.setEnabled(False)
        else:
            self._settings_diag.histMin.setEnabled(True)
            self._settings_diag.histMax.setEnabled(True)

    def get_time(self, index=None):
        """Returns the time of the given index, or the time of the last data point"""
        if index is None:
            index = self.current_index
        # Check if we have last_vector
        if (self.last_vector_x is not None):
            dt = datetime.datetime.fromtimestamp(self.last_vector_x[index])
            return dt

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
            
    def _configure_axis(self, source, title, hist=False):
        """Configures the x and y axis of the plot, according to the
        source/title configuration and content type"""
        conf = source.conf[title]
        if(self.actionX_axis.isChecked()):
            if 'xlabel' in conf and self._settings_diag.x_auto.isChecked():
                self._settings_diag.x_label.setText(conf['xlabel'])
            if hist:
                self.plot.setLabel('bottom', self._settings_diag.y_label.text())
            else:
                self.plot.setLabel('bottom', self._settings_diag.x_label.text())
        if(self.actionY_axis.isChecked()):
            if 'ylabel' in conf and self._settings_diag.y_auto.isChecked():
                self._settings_diag.y_label.setText(conf['ylabel'])
            if hist:
                self.plot.setLabel('left', 'Counts')
            else:
                self.plot.setLabel('left', self._settings_diag.y_label.text())

    def _set_manual_range(self):
        if not self._settings_diag.xlimits_auto.isChecked():
            try:
                xmin = float(str(self._settings_diag.xmin.text()))
            except ValueError:
                pass
            try:
                xmax = float(str(self._settings_diag.xmax.text()))
            except ValueError:
                pass
            if (xmax - xmin) == 0.:
                xmin -= 0.1
                xmax += 0.1
            self.plot.setXRange(xmin, xmax)
        if not self._settings_diag.ylimits_auto.isChecked():
            try:
                ymin = float(str(self._settings_diag.ymin.text()))
            except ValueError:
                pass
            try:
                ymax = float(str(self._settings_diag.ymax.text()))
            except ValueError:
                pass
            if (ymax - ymin) == 0.:
                ymin -= 0.1
                ymax += 0.1
            self.plot.setYRange(ymin, ymax)
            
    def replot(self):
        """Replot data"""
        self.plot.clear()

        # Init background if defined in a data source
        if self._settings_diag.bg is None:
            alert_flag = False
            for source, title in self.source_and_titles():
                conf = source.conf[title]
                if "bg_filename" in conf:
                    conf_bg = {}
                    for k,v in conf.items():
                        if k.startswith("bg_"):
                            conf_bg[k] = v
                    self._settings_diag._configure_bg(**conf_bg)
                    # Use only first if there are many
                    break

        alert_flag = False
        for source, title in self.source_and_titles():
            conf = source.conf[title]
            if "alert" in conf and self.actionToggleAlert.isChecked() and conf['alert']:
                alert_flag = True

        if alert_flag:
            cwd = os.path.dirname(os.path.abspath(__file__))
            os.system('afplay -v %f %s/sounds/%s.wav &' %(self.volume, cwd, self.sound))
            if not self.alertBlinkTimer.isActive():
                self.alertBlinkTimer.start()
        else:
            if self.alertBlinkTimer.isActive():
                self.alertBlinkTimer.stop()
                self.setStyleSheet("")



        # Load background if configured
        self._update_bg()
            
        color_index = 0
        titlebar = []
        self.plot.plotItem.legend.items = []

        xmins = []
        xmaxs = []
        ymins = []
        ymaxs = []
        
        for source, title in self.source_and_titles():
            
            if(title not in source.plotdata or source.plotdata[title].y is None):
                continue
            pd = source.plotdata[title]
            titlebar.append(pd.title)

            conf = source.conf[title]

            color = self.line_colors[color_index % len(self.line_colors)]
            pen = None
            symbol = None
            symbol_pen = None
            symbol_brush = None
            symbol_size = None
            histoangle = 0

            if(self.actionLines.isChecked()):
                pen = color
            if(self.actionPoints.isChecked()):
                symbol = 'o'
                symbol_pen = color
                symbol_brush = color
                symbol_size = 3
            
            if(source.data_type[title] == 'scalar') or (source.data_type[title] == 'running_hist'):
                y = numpy.array(pd.y, copy=False)
                self.last_vector_y = {}
                self.last_vector_x = None
            elif(source.data_type[title] == 'tuple'):
                y = pd.y[:,1]
                symbol_brush = (255,255,255,120)
                symbol_pen = None
                symbol_size = 8
            elif(source.data_type[title] == 'triple'):
                if self.colormap is None:
                    vmin, vmax = (0,1)
                    if 'vmin' in conf:
                        vmin = conf['vmin']
                    if 'vmax' in conf:
                        vmax = conf['vmax']
                    stops = numpy.r_[vmin, vmax]
                    colors = numpy.array([[0, 0, 1, 0.7], [1, 0, 0, 1.0]])
                    self.colormap = pyqtgraph.ColorMap(stops, colors)
                if 'zlabel' in conf:
                    zlabel = conf['zlabel']
                else:
                    zlabel = 'z'
                if self.colorbar is not None:
                    self.plot.scene().removeItem(self.colorbar)
                self.colorbar = ColorBar(self.colormap, 10, 200, label=zlabel)
                self.plot.scene().addItem(self.colorbar)
                self.actionPoints.setChecked(1)
                self.actionLines.setChecked(0)
                self.colorbar.translate(self.geometry().width() - self.colorbar.zone[2], 20.0)
                y = pd.y[:,1]
                z = pd.y[:,2]
                symbol_brush = self.colormap.map(z, 'qcolor')
                symbol_pen   = None
                symbol_size  = 8
            elif source.data_type[title] == 'vector':
                if(self.current_index == -1):
                    y = numpy.array(pd.y[self.current_index % pd.y.shape[0]], copy=False)
                    self.last_vector_y[title] = numpy.array(pd.y)
                    self.last_vector_x = numpy.array(pd.x)
                else:
                    y = self.last_vector_y[title][self.current_index % self.last_vector_y[title].shape[0]]
            elif source.data_type[title] == 'histogram':
                if title not in self._histograms:
                    self._histograms[title] = Histogram(conf["hmin"], conf["hmax"], conf["bins"])
                x = self._histograms[title].values_x
                y = self._histograms[title].values_y
            elif source.data_type[title] == 'normalized_histogram':
                if title not in self._normalized_histograms:
                    self._normalized_histograms[title] = NormalizedHistogram(conf["hmin"], conf["hmax"],
                                                                    conf["bins"])
                x = self._normalized_histograms[title].values_x
                y = self._normalized_histograms[title].values_y
                
            x = None
            if(source.data_type[title] == 'scalar') or (source.data_type[title] == 'running_hist'):
                x = numpy.array(pd.x, copy=False)
                sorted_x = numpy.argsort(x)
                x = x[sorted_x]
                y = y[sorted_x]
                if self._settings_diag.showTrendScalar.isChecked():
                    wl = int(self._settings_diag.windowLength.text())
                    y = utils.array.runningMean(y, min(y.size-1,wl))
                    x = x[-y.size:]
            elif(source.data_type[title] == 'tuple') or (source.data_type[title] == 'triple'):
                x = pd.y[:,0]
            elif(source.data_type[title] == 'vector'):
                if len(y.shape) == 2:
                    x = y[0,:]
                    y = y[1,:]
                else:
                    if 'xmin' in conf and 'xmax' in conf:
                        xmin = conf['xmin']
                        xmax = conf['xmax']
                    else:
                        xmin = 0
                        xmax = source.plotdata[title].y.shape[-1] + xmin
                    x = numpy.linspace(xmin,xmax, y.shape[-1])
            if(self._settings_diag.histogram.isChecked()):
                bins = int(self._settings_diag.histBins.text())
                histMode = self._settings_diag.histMode.currentText()
                if (self._settings_diag.histAutorange.isChecked()):
                    hmin, hmax = y.min(), y.max()
                    self._settings_diag.histMin.setText("%.2f"%hmin)
                    self._settings_diag.histMax.setText("%.2f"%hmax)
                else:
                    hmin = float(self._settings_diag.histMin.text())
                    hmax = float(self._settings_diag.histMax.text())
                if histMode == 'count':
                    y,x = numpy.histogram(y, range=(hmin, hmax), bins=bins)
                elif histMode == 'mean':
                    num,x = numpy.histogram(y, range=(hmin, hmax), bins=bins, weights=x)
                    den,x = numpy.histogram(y, range=(hmin, hmax), bins=bins)
                    y = num/(den+1e-20)
                x = (x[:-1]+x[1:])/2.0
                histoangle = 90
                self._configure_axis(source, title, hist=True)
            elif(source.data_type[title] == "histogram"):
                ringbuffer = pd.y
                # Clear histogram if asked for
                if pd.clear_histogram:
                    self._histograms[title].reset()
                    pd.clear_histogram = False
                self._histograms[title].add_values_from_ringbuffer(ringbuffer)
                x = self._histograms[title].values_x
                y = self._histograms[title].values_y
            elif(source.data_type[title] == "normalized_histogram"):
                ringbuffer = pd.y
                # Clear histogram if asked for
                print("clear_histograms = {0}".format(pd.clear_histograms))
                if pd.clear_histograms:
                    self._histograms[title].reset()
                    pd.clear_histograms = False
                self._normalized_histograms[title].add_values_from_ringbuffer(ringbuffer)
                x = self._normalized_histograms[title].values_x
                y = self._normalized_histograms[title].values_y
            else:
                self._configure_axis(source, title)
            self.plot.setLogMode(x=self._settings_diag.logx.isChecked(),
                                 y=self._settings_diag.logy.isChecked())

            if self._settings_diag.showMainLine.isChecked():
                plt = self.plot.plot(x=x, y=y, clear=False, pen=pen, symbol=symbol,
                                 symbolPen=symbol_pen, symbolBrush=symbol_brush, symbolSize=symbol_size)
                self.legend.addItem(plt, pd.title)

            if 'hline' in conf and conf['hline'] is not None:
                self.plot.getPlotItem().removeItem(self.hline)
                self.hline = pyqtgraph.InfiniteLine(angle=0 + histoangle, movable=False, pen=self.hline_color)
                self.plot.getPlotItem().addItem(self.hline)
                self.hline.setPos(conf['hline'])

            if 'vline' in conf and conf['vline'] is not None:
                self.plot.getPlotItem().removeItem(self.vline)
                self.vline = pyqtgraph.InfiniteLine(angle=90 + histoangle, movable=False, pen=self.vline_color)
                self.plot.getPlotItem().addItem(self.vline)
                self.vline.setPos(conf['vline'])

            xmins.append(x.min())
            xmaxs.append(x.max())
            ymins.append(y.min())
            ymaxs.append(y.max())

            if(x.dtype.metadata is not None and
               'units' in x.dtype.metadata and
               x.dtype.metadata['units'] == 's'):
                if(self.time_on_x_axis == False):
                    self.time_on_x_axis = True
                    self.time_axis.attachToPlotItem(self.plot.getPlotItem())

            else:
                if(self.time_on_x_axis == True):
                    self.time_on_x_axis = False
                    self.time_axis.detachFromPlotItem()
            
            color_index += 1
            
            if (source.data_type[title] == 'vector') and (self._settings_diag.showTrendVector.isChecked()):
                for trend in ['mean', 'median', 'std', 'min', 'max']:
                    if eval('self._settings_diag.trendVector_%s.isChecked()' %trend):
                        _trend = getattr(numpy, trend)
                        if len(pd.y.shape) == 3:
                            ytrend = _trend(numpy.array(pd.y[:,1,:], copy=False), axis=0)
                        else:
                            ytrend = _trend(numpy.array(pd.y, copy=False), axis=0)
                        plt_trend = self.plot.plot(x=x, y=ytrend, clear=False, pen=self.line_colors[color_index % len(self.line_colors)], symbol=symbol,
                                                   symbolPen=symbol_pen, symbolBrush=symbol_brush, symbolSize=symbol_size)
                        self.legend.addItem(plt_trend, trend)
                        color_index += 1


        self.setWindowTitle(", ".join(titlebar))
        dt = self.get_time()
        # Round to miliseconds
        self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
        self.dateLabel.setText(str(dt.date()))

        # Set ranges
        if len(xmins) > 0:
            self._set_manual_range()
        
        # Various options
        if self._settings_diag.aspect_locked.isChecked():
            self.plot.getViewBox().setAspectLocked()
        if self._settings_diag.flip_x.isChecked():
            self.plot.getViewBox().invertX()
        if self._settings_diag.flip_y.isChecked():
            self.plot.getViewBox().invertY()

    def _change_index_by(self, amount):
        """Changes the history index when displaying a vector"""
        if self.last_vector_x is None:
            return
        self.current_index += amount
        if(self.current_index > -1):
            self.current_index = -1
        if(self.current_index < -len(self.last_vector_x)):
            self.current_index = -len(self.last_vector_x)

    def keyPressEvent(self, event):
        """Handle key presses"""
        key = event.key()
        if key == QtCore.Qt.Key_Right:
            self._change_index_by(1)
            self.replot()
        elif key == QtCore.Qt.Key_Left:
            self._change_index_by(-1)
            self.replot()

    def get_state(self, _settings = None):
        """Returns settings that can be used to restore the widget to the current state"""
        settings = _settings or {}
        settings['window_type'] = 'PlotWindow'
        settings['viewbox'] = self.plot.getViewBox().getState()
        settings['x_view'] = self.actionX_axis.isChecked()
        settings['y_view'] = self.actionY_axis.isChecked()
        settings['lines'] = self.actionLines.isChecked()
        settings['points'] = self.actionPoints.isChecked()
        settings['legend'] = self.actionLegend_Box.isChecked()
        plot_item = self.plot.getPlotItem()
        settings['grid_x'] = plot_item.ctrl.xGridCheck.isChecked()
        settings['grid_y'] = plot_item.ctrl.yGridCheck.isChecked()
        settings['grid_alpha'] = plot_item.ctrl.gridAlphaSlider.value()
        settings = self._settings_diag.get_state(settings)
        return DataWindow.get_state(self, settings)

    def restore_from_state(self, settings, data_sources):
        self._settings_diag.restore_from_state(settings)
        self.plot.getViewBox().setState(settings['viewbox'])
        self.actionX_axis.setChecked(settings['x_view'])
        self.actionX_axis.triggered.emit(settings['x_view'])
        self.actionY_axis.setChecked(settings['y_view'])
        self.actionY_axis.triggered.emit(settings['y_view'])
        self.actionLines.setChecked(settings['lines'])
        self.actionPoints.setChecked(settings['points'])
        self.actionLegend_Box.setChecked(settings['legend'])
        self.actionLegend_Box.triggered.emit(settings['legend'])
        plot_item = self.plot.getPlotItem()
        plot_item.ctrl.xGridCheck.setChecked(settings['grid_x'])
        plot_item.ctrl.xGridCheck.toggled.emit(settings['grid_x'])
        plot_item.ctrl.yGridCheck.setChecked(settings['grid_y'])
        plot_item.ctrl.yGridCheck.toggled.emit(settings['grid_y'])
        plot_item.ctrl.gridAlphaSlider.setValue(settings['grid_alpha'])
        return DataWindow.restore_from_state(self, settings, data_sources)
    
    def _update_bg(self):
        if self._settings_diag.bg is not None:
            VB = self.plot.getViewBox()
            B = pyqtgraph.ImageItem(image=self._settings_diag.bg, autoLevels=True)
            xmin = float(self._settings_diag.bg_xmin.text())
            ymin = float(self._settings_diag.bg_xmin.text())
            width  = float(self._settings_diag.bg_xmax.text()) - xmin
            height = float(self._settings_diag.bg_ymax.text()) - ymin
            rect = QtCore.QRectF(xmin, ymin, width, height)
            B.setRect(rect)
            VB.addItem(B, ignoreBounds=True)


    def updateFonts(self):
        f = self.title.font()
        size = int(self.settings.value("plotFontSize"))
        f.setPointSize(size)
        self.title.setFont(f)

        f = QtGui.QFont()
        f.setPointSize(size)
        ax = self.plot.getAxis('left')
        ax.setTickFont(f)
        ax = self.plot.getAxis('bottom')
        ax.setTickFont(f)

    def _onMouseMoved(self, pos):
        view = self.plot
        xy = view.mapToView(pos)
        x = xy.x()
        y = xy.y()
        self.xLabel.setText("%f" % (x))
        self.yLabel.setText("%f" % (y))
