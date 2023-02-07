# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Dialog to change the line plot settings"""
import numpy

from ..Qt import QtCore, QtGui
from . import Ui_linePlotSettings


class LinePlotSettings(QtGui.QDialog, Ui_linePlotSettings):
    """Dialog to change the line plot settings"""
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)

        self.bg = None
        self.bg_filename = None
        self.bg_filename_loaded = None
        self.bg_angle_loaded = None
        self.bg_file.released.connect(self._on_bg_file)
        
    def get_state(self, _settings = None):
        settings = _settings or {}
        settings["xmin"] = self.xmin.text()
        settings["xmax"] = self.xmax.text()
        settings["ymin"] = self.ymin.text()
        settings["ymax"] = self.ymax.text()
        settings["xlimits_auto"] = self.xlimits_auto.isChecked()
        settings["ylimits_auto"] = self.ylimits_auto.isChecked()
        settings["bg_filename"] = self.bg_filename
        settings["bg_xmin"] = self.bg_xmin.text()
        settings["bg_xmax"] = self.bg_xmax.text()
        settings["bg_ymin"] = self.bg_ymin.text()
        settings["bg_ymax"] = self.bg_ymax.text()        
        settings["bg_angle"] = self.bg_angle.text()
        settings["histogram"] = self.histogram.isChecked()
        settings["histAutorange"] = self.histAutorange.isChecked()
        settings["histBins"] = self.histBins.text()
        settings["histMin"] = self.histMin.text()
        settings["histMax"] = self.histMax.text()
        settings["histMode"] = self.histMode.currentText()
        #settings["x_label"] = self.x_label.text()
        #settings["y_label"] = self.y_label.text()
        #settings["x_auto"] = self.x_auto.isChecked()
        #settings["y_auto"] = self.y_auto.isChecked()
        settings["logx"] = self.logx.isChecked()
        settings["logy"] = self.logy.isChecked()
        settings["showTrendScalar"] = self.showTrendScalar.isChecked()
        settings["windowLength"] = self.windowLength.text()
        settings["showTrendVector"] = self.showTrendVector.isChecked()
        settings["showMainLine"] = self.showMainLine.isChecked()
        settings["trendVector_min"] = self.trendVector_min.isChecked()
        settings["trendVector_max"] = self.trendVector_max.isChecked()
        settings["trendVector_std"] = self.trendVector_std.isChecked()
        settings["trendVector_mean"] = self.trendVector_mean.isChecked()
        settings["trendVector_median"] = self.trendVector_median.isChecked()     
        settings["aspect_locked"] = self.aspect_locked.isChecked()
        settings["flip_x"] = self.flip_x.isChecked()
        settings["flip_y"] = self.flip_y.isChecked()
        return settings
        
    def restore_from_state(self, settings):
        if "xmin" not in settings:
            return
        self.xmin.setText(settings["xmin"])
        self.xmax.setText(settings["xmax"])
        self.ymin.setText(settings["ymin"])
        self.ymax.setText(settings["ymax"])
        self.xlimits_auto.setChecked(settings["xlimits_auto"])
        self.ylimits_auto.setChecked(settings["ylimits_auto"])
        self.bg_filename = settings["bg_filename"]
        self.bg_xmin.setText(settings["bg_xmin"])
        self.bg_xmax.setText(settings["bg_xmax"])
        self.bg_ymin.setText(settings["bg_ymin"])
        self.bg_ymax.setText(settings["bg_ymax"])
        self.bg_angle.setText(settings["bg_angle"])
        if settings["bg_filename"] is not None:
            self._read_bg_file()
        self.histogram.setChecked(settings["histogram"])
        self.histAutorange.setChecked(settings["histAutorange"])
        self.histBins.setText(settings["histBins"])
        self.histMin.setText(settings["histMin"])
        self.histMax.setText(settings["histMax"])
        self.histMode.setCurrentIndex(self.histMode.findText(settings["histMode"]))
        #self.x_label.setText(settings["x_label"])
        #self.y_label.setText(settings["y_label"])
        #self.x_auto.setChecked(settings["x_auto"])
        #self.y_auto.setChecked(settings["y_auto"])
        self.logx.setChecked(settings["logx"])
        self.logy.setChecked(settings["logy"])
        self.showTrendScalar.setChecked(settings["showTrendScalar"])
        self.windowLength.setText(settings["windowLength"])
        self.showTrendVector.setChecked(settings["showTrendVector"])
        self.showMainLine.setChecked(settings["showMainLine"])
        self.trendVector_min.setChecked(settings["trendVector_min"])
        self.trendVector_max.setChecked(settings["trendVector_max"])
        self.trendVector_std.setChecked(settings["trendVector_std"])
        self.trendVector_mean.setChecked(settings["trendVector_mean"])
        self.trendVector_median.setChecked(settings["trendVector_median"])
        self.aspect_locked.setChecked(settings["aspect_locked"])
        self.flip_x.setChecked(settings["flip_x"])
        self.flip_y.setChecked(settings["flip_y"])
        
    def _configure_limits(self, xmin=0., xmax=1., ymin=0., ymax=1., xlimits_auto=True, ylimits_auto=True):
        self.xmin.setText("%e" % xmin)
        self.xmax.setText("%e" % xmax)
        self.xlimits_auto.setChecked(xlimits_auto)

        self.ymin.setText("%e" % ymin)
        self.ymax.setText("%e" % ymax)
        self.ylimits_auto.setChecked(ylimits_auto)        
        
    def _configure_bg(self, bg_xmin=0., bg_xmax=1., bg_ymin=0., bg_ymax=1., bg_angle=0., bg_filename=None):

        self.bg_xmin.setText("%e" % bg_xmin)
        self.bg_xmax.setText("%e" % bg_xmax)
        self.bg_ymin.setText("%e" % bg_ymin)
        self.bg_ymax.setText("%e" % bg_ymax)
        self.bg_angle.setText("%f" % bg_angle)

        self.bg_filename = bg_filename
        self.bg = None
        
        if bg_filename is not None:
            self._read_bg_file()
        
    def _on_bg_file(self):
        fname = QtGui.QFileDialog.getOpenFileName(self, "Load Background Image", filter="NPY Files (*.npy)",
                                                  options=QtGui.QFileDialog.DontUseNativeDialog)
        if(fname):
            self.bg_filename = fname
            self._read_bg_file()

    def _read_bg_file(self):
        if self.bg_filename is None:
            return
        if self.bg_filename_loaded == self.bg_filename and self.bg_angle_loaded == self.bg_angle.text():
            return
        print("Reading background image from file (%s) ..." % self.bg_filename)
        self.bg = numpy.load(self.bg_filename)
        self.bg = numpy.array(self.bg, dtype=numpy.float64)
        print("... done")
        a = float(self.bg_angle.text())
        if a != 0.:
            # Interpolate image with on roateted grid
            print("Interpolating rotated background image ...")
            from scipy.interpolate import griddata
            X,Y = numpy.meshgrid(numpy.arange(self.bg.shape[1]), numpy.arange(self.bg.shape[0]))
            X = X - (X.shape[1]-1)/2.
            Y = Y - (Y.shape[0]-1)/2.
            points = numpy.asarray([[xi,yi] for xi,yi in zip(X.flat,Y.flat)])
            X2 = X*numpy.cos(a) - Y*numpy.sin(a)
            Y2 = X*numpy.sin(a) + Y*numpy.cos(a)
            self.bg = griddata(points, self.bg.flat, (X2, Y2), method='nearest')
            print("... done")
        self.bg_filename_loaded = self.bg_filename
        self.bg_angle_loaded = self.bg_angle.text()
