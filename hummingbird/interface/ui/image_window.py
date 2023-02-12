# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Window to display images"""
import datetime
import logging
import os

import numpy
import numpy.random
import pyqtgraph

from hummingbird import utils
from ..Qt import QtCore, QtGui
from . import DataWindow, Ui_imageWindow


class ImageWindow(DataWindow, Ui_imageWindow):
    """Window to display images"""
    acceptable_data_types = ['image', 'vector', 'triple', 'running_hist']

    def __init__(self, parent=None):
        # This also sets up the UI part
        DataWindow.__init__(self, parent)
        # This is imported here to prevent problems with sphinx
        from .image_view import ImageView
        self.plot = ImageView(self, view=pyqtgraph.PlotItem())
        self._finish_layout()
        self.infoLabel.setText('')
        self.exclusive_source = True
        self.meanmap = None
        self.last_x = None
        self.last_y = None
        self.mm_last = None
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

        self.settingsWidget.ui.modelCenterX.setValidator(QtGui.QDoubleValidator())
        self.settingsWidget.ui.modelCenterY.setValidator(QtGui.QDoubleValidator())
        self.settingsWidget.ui.modelDiameter.setValidator(QtGui.QDoubleValidator())
        self.settingsWidget.ui.photonEnergy.setValidator(QtGui.QDoubleValidator())
        self.settingsWidget.ui.detectorGain.setValidator(QtGui.QDoubleValidator())
        self.settingsWidget.ui.detectorDistance.setValidator(QtGui.QDoubleValidator())        
        self.settingsWidget.ui.detectorPixelSize.setValidator(QtGui.QDoubleValidator())
        self.modelParameters = {}

        success, spimage = utils.io.load_spimage()
        if not success:
            # no spimage available, we need to disable the model settings
            #self.settingsWidget.ui.modelTab.setEnabled(False)
            pass
        else:
            self.spimage = spimage

        self.settingsWidget.ui.colormap_max.setValidator(QtGui.QDoubleValidator())

                
        self.plot.getHistogramWidget().region.sigRegionChangeFinished.connect(self.set_colormap_range)
        self.actionPlotSettings.triggered.connect(self.toggle_settings)

        # Make sure to disable native menus
        self.plot.getView().setMenuEnabled(False)
        self.plot.getHistogramWidget().vb.setMenuEnabled(False)
        self.x_axis_name = 'left'
        self.y_axis_name = 'bottom'
        self._set_logscale_lookuptable()

        self.running_hist_initialised = False
        self._has_circular_roi = False
        self._circular_rois = []
        
        self.actionReset_cache.triggered.connect(self.on_reset_cache)

        self.updateFonts()

        # By default do not show x and y axis on images
        self.plot.getView().getAxis('left').setVisible(False)
        self.actionY_axis.setChecked(False)
        self.plot.getView().getAxis('bottom').setVisible(False)
        self.actionX_axis.setChecked(False)

        self.plot.getView().scene().sigMouseMoved.connect(self._onMouseMoved)
        self.plot.getView().scene().sigMouseHover.connect(self._onMouseHover)

        # Make sure menubar is attached to the main window
        self.menubar = self.menuBar()
        self.menubar.setNativeMenuBar(False)
        
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

    def get_time(self, index=None):
        time, msg = self.get_time_and_msg(index)
        return time
        
    def _image_transform(self, img, source, title):
        """Returns the appropriate transform for the content"""
        conf = source.conf[title]
        
        xmin = conf.get('xmin', 0)
        ymin = conf.get('ymin', 0)

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

        
        translate_transform = QtGui.QTransform().translate(ymin, xmin)

        # The order of dimensions in the scale call is (y,x) as in the numpy
        # array the last dimension corresponds to the x.
        scale_transform = QtGui.QTransform().scale((ymax-ymin)/img.shape[-2],
                                                   (xmax-xmin)/img.shape[-1])
        
        #rotate_transform = QtGui.QTransform()
        #if source.data_type[title] == 'image':
        #    if "angle" in conf:
        #        rotate_transform = QtGui.QTransform(numpy.cos(conf["angle"]), numpy.sin(conf["angle"]), -numpy.sin(conf["angle"]), numpy.cos(conf["angle"]), 0, 0)

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
            
        transform = scale_transform * translate_transform * transpose_transform
        #transform = scale_transform * translate_transform * rotate_transform * transpose_transform
        
        # print('|%f %f %f|' % (transform.m11(), transform.m12(), transform.m13()))
        # print('|%f %f %f|' % (transform.m21(), transform.m22(), transform.m23()))
        # print('|%f %f %f|' % (transform.m31(), transform.m32(), transform.m33()))
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
            "flipy" in conf and conf['flipy'] == True)):
            self.plot.getView().invertY(not self.plot.getView().getViewBox().yInverted())
        if(self.settingsWidget.ui.flipx.currentText() == 'Yes' or
           (self.settingsWidget.ui.flipx.currentText() == 'Auto' and
            "flipx" in conf and conf['flipx'] == True)):
            self.plot.getView().invertX(not self.plot.getView().getViewBox().xInverted())

        # Tranpose images to make x (last dimension) horizontal
        axis_labels = ['left', 'bottom']
        xlabel_index = 0
        ylabel_index = 1
        if (source.data_type[title] == 'image') or (source.data_type[title] == 'triple'):
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

    def on_reset_cache(self):
        self._reset_meanmap_cache()

    def _reset_meanmap_cache(self):
        if self.meanmap is not None and self.last_x is not None and self.last_y is not None:
            xmin = self.last_x-self.mm_dx*self.mm_xbins/2.-self.mm_dx/2.
            xmax = self.last_x+self.mm_dx*self.mm_xbins/2.-self.mm_dx/2.
            ymin = self.last_y-self.mm_dy*self.mm_ybins/2.-self.mm_dy/2.
            ymax = self.last_y+self.mm_dy*self.mm_ybins/2.-self.mm_dy/2.
            self._init_meanmap(xmin, xmax, ymin, ymax, self.mm_xbins, self.mm_ybins)
   
    def _init_meanmap(self, xmin, xmax, ymin, ymax, xbins, ybins):
        self.mm_xmin = xmin
        self.mm_xmax = xmax
        self.mm_ymin = ymin
        self.mm_ymax = ymax
        self.mm_xbins = xbins
        self.mm_ybins = ybins
        self.mm_dx = numpy.float(self.mm_xmax - self.mm_xmin)/self.mm_xbins
        self.mm_dy = numpy.float(self.mm_ymax - self.mm_ymin)/self.mm_ybins
        self.meanmap = numpy.zeros((3, self.mm_ybins, self.mm_xbins), dtype=numpy.float64)
        self._update_meanmap_transform()

    def _update_meanmap_transform(self):
        translate_transform = QtGui.QTransform().translate(self.mm_ymin, self.mm_xmin)
        scale_transform = QtGui.QTransform().scale(self.mm_dy, self.mm_dx)
        transpose_transform = QtGui.QTransform()
        transpose_transform *= QtGui.QTransform(0, 1, 0,
                                                1, 0, 0,
                                                0, 0, 1)
        self.meanmap_transform = scale_transform*translate_transform*transpose_transform
        
    def _extend_meanmap(self, x, y):
        ix = numpy.round((x - self.mm_xmin)/self.mm_dx)
        iy = numpy.round((y - self.mm_ymin)/self.mm_dx)
        ix_max = max([self.meanmap.shape[2]-1, ix.max()])
        ix_min = min([0, ix.min()])
        iy_max = max([self.meanmap.shape[1]-1, iy.max()])
        iy_min = min([0, iy.min()])
        xbins = ix_max - ix_min + 1
        ybins = iy_max - iy_min + 1
        if xbins > self.meanmap.shape[2] or ybins > self.meanmap.shape[1]:
            # A little nasty fix - just for now
            if xbins > 5000 or ybins > 5000:
                logging.warning("Too large extent of meanmap (%i, %i) - restting meanmap with new extent centered around corrent position: x=%f, y=%f" % (xbins, ybins, x[-1], y[-1]))
                xbins = 100
                ybins = 100
                xmin = x[-1]-self.mm_dx*xbins/2
                xmax = x[-1]+self.mm_dx*xbins/2
                ymin = y[-1]-self.mm_dy*ybins/2
                ymax = y[-1]+self.mm_dy*ybins/2
                self._init_meanmap(xmin, xmax, ymin, ymax, xbins, ybins)
                self._extend_meanmap(x,y)
                return
            temp = numpy.zeros(shape=(3, ybins, xbins), dtype=self.meanmap.dtype)
            temp[:,
                 -iy_min:-iy_min+self.meanmap.shape[1],
                 -ix_min:-ix_min+self.meanmap.shape[2]] = self.meanmap[:,:,:]
            self.meanmap = temp
            self.mm_xmin = self.mm_xmin + ix_min * self.mm_dx
            self.mm_xmax = self.mm_xmin + (xbins-1) * self.mm_dx
            self.mm_ymin = self.mm_ymin + iy_min * self.mm_dx
            self.mm_ymax = self.mm_ymin + (ybins-1) * self.mm_dx
            self.mm_xbins = xbins
            self.mm_ybins = ybins
            self._update_meanmap_transform()
        
    def _fill_meanmap(self, times, triples, xmin=0, xmax=100, ymin=0, ymax=100, xbins=100, ybins=100, dynamic_extent=False, initial_reset=False):

        triples_new = triples
        if self.meanmap is not None:
            w = numpy.where(self.mm_last==times)
            if len(w) > 0:
                if w[0] > 0:
                    triples_new = triples[:w[0],:]
        x = triples_new[:,0]
        y = triples_new[:,1]
        z = triples_new[:,2]

        self.last_x = x[-1]
        self.last_y = y[-1] 
        
        if self.meanmap is None:
            self._init_meanmap(xmin, xmax, ymin, ymax, xbins, ybins)

        if self.mm_last is None and initial_reset:
            self._reset_meanmap_cache()
            
        self.mm_last = times[0]
            
        if dynamic_extent:
            self._extend_meanmap(triples_new[:,0], triples_new[:,1])                    

        for x,y,z in triples_new:
            
            ix = numpy.round((x - (self.mm_xmin+self.mm_dx/2.))/self.mm_dx).astype(int)
            iy = numpy.round((y - (self.mm_ymin+self.mm_dy/2.))/self.mm_dy).astype(int)
            
            if (ix < 0):                    
                ix = 0
            elif (ix >= self.mm_xbins):
                ix = self.mm_xbins - 1
            if (iy < 0):
                iy = 0
            elif (iy >= self.mm_ybins):
                iy = self.mm_ybins - 1

            self.meanmap[0,iy,ix] += z
            self.meanmap[1,iy,ix] += 1
            self.meanmap[2,iy,ix] = self.meanmap[0,iy,ix]/self.meanmap[1,iy,ix]

        if (self.settingsWidget.ui.show_heatmap.isChecked()):
            return self.meanmap[0], self.meanmap_transform, x, y
        elif (self.settingsWidget.ui.show_visitedmap.isChecked()):
            return self.meanmap[1], self.meanmap_transform, x, y
        else:
            return self.meanmap[2], self.meanmap_transform, x, y

    def _show_circular_rois(self, center=None, diameters=None):
        if (self.actionCircularROI.isChecked()):
            if (center is not None) and (diameters is not None):
                if not self._has_circular_roi:
                    if not isinstance(diameters, list):
                        diameters = list(diameters)
                    for i in range(len(diameters)):
                        roi = pyqtgraph.CircleROI((center[0]-diameters[i]/2, center[1]-diameters[i]/2), diameters[i], movable=False)
                        self._circular_rois.append(roi)
                        self.plot.addItem(roi)
                    self._has_circular_roi = True
        else:
            if self._has_circular_roi:
                for roi in self._circular_rois:
                    self.plot.removeItem(roi)
                self._circular_rois = []
                self._has_circular_roi = False
        
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
            if "alert" in conf and self.actionToggleAlert.isChecked() and conf['alert']:
                cwd = os.path.dirname(os.path.abspath(__file__))
                os.system('afplay -v %f %s/sounds/%s.wav &' %(self.volume, cwd, self.sound))
                if not self.alertBlinkTimer.isActive():
                    self.alertBlinkTimer.start()
            else:
                if self.alertBlinkTimer.isActive():
                    self.alertBlinkTimer.stop()
                    self.setStyleSheet("");
            
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
                if not img.shape[0]:
                    continue
            elif conf["data_type"] == "vector":
                #print(pd.y.shape)
                if len(pd.y.shape) == 3:
                    img = numpy.array(pd.y[:,1,:], copy=False)
                else:
                    img = numpy.array(pd.y[:,:], copy=False)
                #img = numpy.array(pd.y[:,1,:], copy=False)
                bins   = img.shape[1]
                hmin   = 0
                hmax   = img.shape[1]
                length = pd.maxlen
            else:
                img = numpy.array(pd.y, copy=False)
            self._configure_axis(source, title)
            transform = self._image_transform(img, source, title)
            
            if (conf["data_type"] == "running_hist") or (conf["data_type"]=="vector"):
                translate_transform = QtGui.QTransform().translate(0, hmin)
                scale_transform = QtGui.QTransform().scale(3.*float(hmax-hmin)/float(length), float(hmax-hmin)/float(bins))
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
                    triples = numpy.array(pd.y, copy=False)
                    times   = numpy.array(pd.x, copy=False)
                    img, transform, x, y = self._fill_meanmap(times, triples,
                                                              xmin=conf["xmin"], xmax=conf["xmax"], ymin=conf["ymin"], ymax=conf["ymax"],
                                                              ybins=conf["ybins"], xbins=conf["xbins"],
                                                              dynamic_extent=conf.get("dynamic_extent", False),
                                                              initial_reset=conf.get("initial_reset", False),
                    )
                else:
                    x, y = (0,0)
                if (self.settingsWidget.ui.show_trend.isChecked()):
                    _trend = getattr(numpy, str(self.settingsWidget.ui.trend_options.currentText()))
                    img = _trend(img, axis=0)

                if self.settingsWidget.ui.modelVisibility.value() > 0:
                    # We should overwrite part of the image with a model
                    img = self._apply_model_to_img(img)

                if(img.ndim == 3):
                    self.plot.setImage(img,
                                       transform=transform,
                                       autoRange=auto_range, autoLevels=auto_levels,
                                       autoHistogramRange=auto_histogram,
                                       axes={'t': 0, 'x': 1, 'y': 2, 'c': None})
                else:
                    self.plot.setImage(img,
                                       transform=transform,
                                       autoRange=auto_range, autoLevels=auto_levels,
                                       autoHistogramRange=auto_histogram)

                if 'center' in conf and 'diameters' in conf:
                    self._show_circular_rois(conf['center'], conf['diameters'])
                                
                if 'aspect_ratio' in conf and conf['aspect_ratio'] is not None:
                    self.plot.view.setAspectLocked(True, ratio=conf['aspect_ratio'])
                
                self._show_crosshair(x,y)
                if(len(self.plot.image.shape) > 2):
                    # Make sure to go to the last image
                    last_index = self.plot.image.shape[0]-1
                    self.plot.setCurrentIndex(last_index, autoHistogramRange=auto_histogram)
                self._set_logscale(source, title)

            self.setWindowTitle(pd.title)
            dt, msg = self.get_time_and_msg()
            if msg is not None and msg != '':
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

    def _apply_model_to_img(self, img):
        dirty = False
        centerx = float(self.settingsWidget.ui.modelCenterX.text())
        if 'centerx' not in self.modelParameters or centerx != self.modelParameters['centerx']:
            dirty = True
            self.modelParameters['centerx'] = centerx
            
        centery = float(self.settingsWidget.ui.modelCenterY.text())
        if 'centery' not in self.modelParameters or centery != self.modelParameters['centery']:
            dirty = True
            self.modelParameters['centery'] = centery

        diameter = float(self.settingsWidget.ui.modelDiameter.text()) * 1e-9
        if 'diameter' not in self.modelParameters or diameter != self.modelParameters['diameter']:
            dirty = True
            self.modelParameters['diameter'] = diameter

        intensity = float(self.settingsWidget.ui.pulseIntensity.text()) * 1e-3 / 1e-12    
        if 'intensity' not in self.modelParameters or intensity != self.modelParameters['intensity']:
            dirty = True
            self.modelParameters['intensity'] = intensity

        wavelength = 1239.84193/float(self.settingsWidget.ui.photonEnergy.text()) * 1e-9
        if 'wavelength' not in self.modelParameters or wavelength != self.modelParameters['wavelength']:
            dirty = True
            self.modelParameters['wavelength'] = wavelength

        distance = float(self.settingsWidget.ui.detectorDistance.text()) 
        if 'distance' not in self.modelParameters or distance != self.modelParameters['distance']:
            dirty = True
            self.modelParameters['distance'] = distance

        pixelsize = float(self.settingsWidget.ui.detectorPixelSize.text()) * 1e-6
        if 'pixelsize' not in self.modelParameters or pixelsize != self.modelParameters['pixelsize']:
            dirty = True
            self.modelParameters['pixelsize'] = pixelsize

        if dirty:
            material = 'virus'
            quantum_efficiency = 1.0
            adu_per_photon = float(self.settingsWidget.ui.detectorGain.text())/float(self.settingsWidget.ui.photonEnergy.text())*1e3
            self.modelParameters['adu_per_photon'] = adu_per_photon
            size    = self.spimage.sphere_model_convert_diameter_to_size(diameter, wavelength,
                                                                         pixelsize, distance) 
            scaling = self.spimage.sphere_model_convert_intensity_to_scaling(intensity, diameter,
                                                                             wavelength, pixelsize,
                                                                             distance, quantum_efficiency,
                                                                             adu_per_photon, material)
            fit = self.spimage.I_sphere_diffraction(scaling,
                                                    self.spimage.rgrid(img[0].shape, (centerx, centery)),
                                                    size)
            self.modelParameters['fit'] = fit
        else:
            fit = self.modelParameters['fit']
            adu_per_photon = self.modelParameters['adu_per_photon']

        extent = numpy.ceil(img.shape[2]*self.settingsWidget.ui.modelVisibility.value()/100.0)
        if self.settingsWidget.ui.modelPoisson.isChecked():
            fit = numpy.random.poisson(fit[:,:extent]/adu_per_photon)*adu_per_photon
        else:
            fit = fit[:,:extent]

        img[-1,:,:extent] = fit
        return img

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
        settings['flipx'] = self.settingsWidget.ui.flipx.currentText()
        settings['flipy'] = self.settingsWidget.ui.flipy.currentText()
        settings['viewbox'] = self.plot.getView().getViewBox().getState()
        settings['x_view'] = self.actionX_axis.isChecked()
        settings['y_view'] = self.actionY_axis.isChecked()
        settings['histogram_view'] = self.actionHistogram.isChecked()
        settings['crosshair'] = self.actionCrosshair.isChecked()
        settings['circular_roi'] = self.actionCircularROI.isChecked()
        settings['gradient_mode'] = self.plot.getHistogramWidget().item.gradient.saveState()
        
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
        flipx = self.settingsWidget.ui.flipx
        flipx.setCurrentIndex(flipx.findText(settings['flipx']))
        self.plot.getView().getViewBox().setState(settings['viewbox'])
        self.actionX_axis.setChecked(settings['x_view'])
        self.actionX_axis.triggered.emit(settings['x_view'])
        self.actionY_axis.setChecked(settings['y_view'])
        self.actionY_axis.triggered.emit(settings['y_view'])
        self.actionHistogram.setChecked(settings['histogram_view'])
        self.actionHistogram.triggered.emit(settings['histogram_view'])
        self.actionCrosshair.setChecked(settings['crosshair'])
        self.actionCrosshair.triggered.emit(settings['crosshair'])
        self.actionCircularROI.setChecked(settings['circular_roi'])
        self.actionCircularROI.triggered.emit(settings['circular_roi'])

        self.plot.getHistogramWidget().item.gradient.restoreState(settings['gradient_mode'])
        
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
    
    def updateFonts(self):
        f = self.title.font()
        size = int(self.settings.value("plotFontSize"))
        f.setPointSize(size)
        self.title.setFont(f)
        
        f = QtGui.QFont()
        f.setPointSize(size)
        ax = self.plot.getView().getAxis('left')
        ax.setTickFont(f)
        ax = self.plot.getView().getAxis('bottom')
        ax.setTickFont(f)            

    def _onMouseMoved(self, pos):
        view = self.plot.getView()
        xy = view.mapToView(pos)
        T = self.plot.imageItem.transform()
        xy = T.map(xy)
        # For some strange reason the x and y need to be swapped
        y = int(xy.x())
        x = int(xy.y())
        if x < 0 or y < 0:
            return
        try:
            value = self.plot.image[self.plot.currentIndex, y, x]
        except:
            self.infoLabel.setText(None)
            return
        self.infoLabel.setText("(%d,%d) = %f" % (x, y, value))

    def _onMouseHover(self, items):
        if(len(items) < 2):
            self.infoLabel.setText(None)
