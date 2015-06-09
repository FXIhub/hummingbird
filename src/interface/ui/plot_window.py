"""Window to display 2D plots"""
from interface.ui import Ui_plotWindow
import pyqtgraph
import numpy
from interface.ui import DataWindow
from interface.Qt import QtCore
import datetime
import utils.array

class PlotWindow(DataWindow, Ui_plotWindow):
    """Window to display 2D plots"""
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
        self.acceptable_data_types = ['scalar', 'vector', 'tuple']
        self.exclusive_source = False
        self.line_colors = [(252, 175, 62), (114, 159, 207), (255, 255, 255),
                            (239, 41, 41), (138, 226, 52), (173, 127, 168)]
        self.current_index = -1
        self.last_vector_y = None
        self.last_vector_x = None
        self._settings_diag = LinePlotSettings(self)
        self.x_auto = True
        self.y_auto = True
        self.x_label = ''
        self.y_label = ''

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
        self._settings_diag.x_auto.setChecked(self.x_auto)
        self._settings_diag.y_auto.setChecked(self.y_auto)
        self._settings_diag.x_label.setText(self.x_label)
        self._settings_diag.y_label.setText(self.y_label)
        self._settings_diag.histAutorange.toggled.connect(self._on_histogram_autorange)
        if(self._settings_diag.exec_()):
            self.x_auto = self._settings_diag.x_auto.isChecked()
            if(self.x_auto is False):
                self.x_label = self._settings_diag.x_label.text()
            self.y_auto = self._settings_diag.y_auto.isChecked()
            if(self.y_auto is False):
                self.y_label = self._settings_diag.y_label.text()
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
        if(self.last_vector_x is not None):
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
            if 'xlabel' in conf and self.x_auto:
                self.x_label = conf['xlabel']
            if hist:
                self.plot.setLabel('bottom', self.y_label)
            else:
                self.plot.setLabel('bottom', self.x_label)
        if(self.actionY_axis.isChecked()):
            if 'ylabel' in conf and self.y_auto:
                self.y_label = conf['ylabel']
            if hist:
                self.plot.setLabel('left', 'Counts')
            else:
                self.plot.setLabel('left', self.y_label)

    def _configure_xlimits(self, source, title):
        conf = source.conf[title]
        xmin = 0
        xmax = source.plotdata[title].y.shape[-1] + xmin
        if 'xmin' in conf and 'xmax' in conf:
            xmin = conf['xmin']
            xmax = conf['xmax']
        return xmin, xmax
            
    def replot(self):
        """Replot data"""
        self.plot.clear()
        color_index = 0
        titlebar = []
        self.plot.plotItem.legend.items = []
        for source, title in self.source_and_titles():
            if(title not in source.plotdata or source.plotdata[title].y is None):
                continue
            pd = source.plotdata[title]
            titlebar.append(pd.title)

            color = self.line_colors[color_index % len(self.line_colors)]
            pen = None
            symbol = None
            symbol_pen = None
            symbol_brush = None
            if(self.actionLines.isChecked()):
                pen = color
            if(self.actionPoints.isChecked()):
                symbol = 'o'
                symbol_pen = color
                symbol_brush = color

            if(source.data_type[title] == 'scalar'):
                y = numpy.array(pd.y, copy=False)
                self.last_vector_y = None
                self.last_vector_x = None
            elif(source.data_type[title] == 'tuple'):
                y = pd.y[:,1]
            elif source.data_type[title] == 'vector':
                if(self.current_index == -1):
                    y = numpy.array(pd.y[self.current_index % pd.y.shape[0]], copy=False)
                    self.last_vector_y = numpy.array(pd.y)
                    self.last_vector_x = numpy.array(pd.x)
                else:
                    y = self.last_vector_y[self.current_index % self.last_vector_y.shape[0]]

            x = None
            if(source.data_type[title] == 'scalar'):
                x = numpy.array(pd.x, copy=False)
                if self._settings_diag.runningMean.isChecked():
                    wl = int(self._settings_diag.window_length.text())
                    y = utils.array.runningMean(y, wl)
                    x = x[::wl][:len(y)]
            elif(source.data_type[title] == 'tuple'):
                x = pd.y[:,0]
            elif(source.data_type[title] == 'vector'):
                if len(y.shape) == 2:
                    x = y[0,:]
                    y = y[1,:]
                else:
                    xmin, xmax = self._configure_xlimits(source, title)
                    x = numpy.linspace(xmin,xmax, y.shape[-1])
            if(self._settings_diag.histogram.isChecked()):
                bins = int(self._settings_diag.histBins.text())
                if (self._settings_diag.histAutorange.isChecked()):
                    hmin, hmax = y.min(), y.max()
                    self._settings_diag.histMin.setText("%.2f"%hmin)
                    self._settings_diag.histMax.setText("%.2f"%hmax)
                else:
                    hmin = float(self._settings_diag.histMin.text())
                    hmax = float(self._settings_diag.histMax.text())
                y,x = numpy.histogram(y, range=(hmin, hmax), bins=bins)
                x = (x[:-1]+x[1:])/2.0
                self._configure_axis(source, title, hist=True)
            else:
                self._configure_axis(source, title)
            self.plot.setLogMode(x=self._settings_diag.logx.isChecked(),
                                 y=self._settings_diag.logy.isChecked())
            plt = self.plot.plot(x=x, y=y, clear=False, pen=pen, symbol=symbol,
                                 symbolPen=symbol_pen, symbolBrush=symbol_brush, symbolSize=3)

            self.legend.addItem(plt, pd.title)
            color_index += 1

        self.setWindowTitle(", ".join(titlebar))
        dt = self.get_time()
        # Round to miliseconds
        self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
        self.dateLabel.setText(str(dt.date()))

    def _change_index_by(self, amount):
        """Changes the history index when displaying a vector"""
        if(self.last_vector_x is None):
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

        return DataWindow.get_state(self, settings)

    def restore_from_state(self, settings, data_sources):
        self.plot.getViewBox().setState(settings['viewbox'])
        self.actionX_axis.setChecked(settings['x_view'])
        self.actionX_axis.triggered.emit(settings['x_view'])
        self.actionY_axis.setChecked(settings['y_view'])
        self.actionY_axis.triggered.emit(settings['y_view'])
        self.actionLines.setChecked(settings['lines'])
        self.actionPoints.setChecked(settings['points'])
        self.actionLegend_Box.setChecked(settings['legend'])
        self.actionLegend_Box.triggered.emit(settings['legend'])
        return DataWindow.restore_from_state(self, settings, data_sources)

from interface.ui import LinePlotSettings
