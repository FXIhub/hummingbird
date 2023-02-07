# -*- coding: utf-8 -*-
"""
ImageView.py -  Widget for basic image dispay and analysis
Copyright 2010  Luke Campagnola
Distributed under MIT/X11 license. See license.txt for more infomation.

Widget used for displaying 2D or 3D data. Features:
  - float or int (including 16-bit int) image display via ImageItem
  - zoom/pan via GraphicsView
  - black/white level controls
  - time slider for 3D data sets
  - ROI plotting
  - Image normalization through a variety of methods
"""
import numpy
import pyqtgraph

from ..Qt import QtCore, QtGui, loadUiType
from . import uidir

Ui_Form, base = loadUiType(uidir + '/image_view.ui')


class ImageView(QtGui.QWidget):
    """
    Widget used for display and analysis of image data.
    Implements many features:

    * Displays 2D and 3D image data. For 3D data, a z-axis
      slider is displayed allowing the user to select which frame is displayed.
    * Displays histogram of image data with movable region defining the dark/light levels
    * Editable gradient provides a color lookup table
    * Frame slider may also be moved using left/right arrow keys as well as pgup, pgdn, home, and end.
    * Basic analysis features including:

        * ROI and embedded plot for measuring image values across frames
        * Image normalization / background subtraction

    Basic Usage::

        imv = pg.ImageView()
        imv.show()
        imv.setImage(data)
    """
    sigProcessingChanged = QtCore.Signal(object)
    
    def __init__(self, parent=None, name="ImageView", view=None, imageItem=None, *args):
        """
        By default, this class creates an :class:`ImageItem <pyqtgraph.ImageItem>` to display image data
        and a :class:`ViewBox <pyqtgraph.ViewBox>` to contain the ImageItem. Custom items may be given instead 
        by specifying the *view* and/or *imageItem* arguments.
        """
        QtGui.QWidget.__init__(self, parent, *args)
        self._parent = parent
        self.levelMax = 4096
        self.levelMin = 0
        self.name = name
        self.image = None
        self.axes = {}
        self.imageDisp = None
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.scene = self.ui.graphicsView.scene()
        
        if view is None:
            self.view = pyqtgraph.ViewBox()
        else:
            self.view = view
        self.ui.graphicsView.setCentralItem(self.view)
        self.view.setAspectLocked(True)
        self.view.invertY()
        
        if imageItem is None:
            self.imageItem = pyqtgraph.ImageItem()
        else:
            self.imageItem = imageItem
        self.view.addItem(self.imageItem)
        self.currentIndex = 0
        
        self.ui.histogram.setImageItem(self.imageItem)        

        self.keysPressed = {}
        
        ## wrap functions from view box
        for fn in ['addItem', 'removeItem']:
            setattr(self, fn, getattr(self.view, fn))

        ## wrap functions from histogram
        for fn in ['setHistogramRange', 'autoHistogramRange', 'getLookupTable', 'getLevels']:
            setattr(self, fn, getattr(self.ui.histogram, fn))

        self.noRepeatKeys = [QtCore.Qt.Key_Right, QtCore.Qt.Key_Left, QtCore.Qt.Key_Up, QtCore.Qt.Key_Down, QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown]
        

    def setImage(self, img, autoRange=True, autoLevels=True, levels=None, axes=None, xvals=None, pos=None, scale=None, transform=None, autoHistogramRange=True):
        """
        Set the image to be displayed in the widget.
        
        ================== =======================================================================
        **Arguments:**
        img                (numpy array) the image to be displayed.
        xvals              (numpy array) 1D array of z-axis values corresponding to the third axis
                           in a 3D image. For video, this array should contain the time of each frame.
        autoRange          (bool) whether to scale/pan the view to fit the image.
        autoLevels         (bool) whether to update the white/black levels to fit the image.
        levels             (min, max); the white and black level values to use.
        axes               Dictionary indicating the interpretation for each axis.
                           This is only needed to override the default guess. Format is::
                       
                               {'t':0, 'x':1, 'y':2, 'c':3};
        
        pos                Change the position of the displayed image
        scale              Change the scale of the displayed image
        transform          Set the transform of the displayed image. This option overrides *pos*
                           and *scale*.
        autoHistogramRange If True, the histogram y-range is automatically scaled to fit the
                           image data.
        ================== =======================================================================
        """
        if hasattr(img, 'implements') and img.implements('MetaArray'):
            img = img.asarray()
        
        if not isinstance(img, numpy.ndarray):
            raise Exception("Image must be specified as ndarray.")
        self.image = img
        
        if xvals is not None:
            self.tVals = xvals
        elif hasattr(img, 'xvals'):
            try:
                self.tVals = img.xvals(0)
            except:
                self.tVals = numpy.arange(img.shape[0])
        else:
            self.tVals = numpy.arange(img.shape[0])
        
        if axes is None:
            if img.ndim == 2:
                self.axes = {'t': None, 'x': 0, 'y': 1, 'c': None}
            elif img.ndim == 3:
                if img.shape[2] <= 4:
                    self.axes = {'t': None, 'x': 0, 'y': 1, 'c': 2}
                else:
                    self.axes = {'t': 0, 'x': 1, 'y': 2, 'c': None}
            elif img.ndim == 4:
                self.axes = {'t': 0, 'x': 1, 'y': 2, 'c': 3}
            else:
                raise Exception("Can not interpret image with dimensions %s" % (str(img.shape)))
        elif isinstance(axes, dict):
            self.axes = axes.copy()
        elif isinstance(axes, list) or isinstance(axes, tuple):
            self.axes = {}
            for i in range(len(axes)):
                self.axes[axes[i]] = i
        else:
            raise Exception("Can not interpret axis specification %s. Must be like {'t': 2, 'x': 0, 'y': 1} or ('t', 'x', 'y', 'c')" % (str(axes)))
            
        for x in ['t', 'x', 'y', 'c']:
            self.axes[x] = self.axes.get(x, None)
            
        self.imageDisp = None
        
        self.currentIndex = 0
        self.updateImage(autoHistogramRange=autoHistogramRange)
        if levels is None and autoLevels:
            self.autoLevels()
        if levels is not None:  ## this does nothing since getProcessedImage sets these values again.
            self.setLevels(*levels)
            
        if self.axes['t'] is not None:
            if len(self.tVals) > 1:
                start = self.tVals.min()
                stop = self.tVals.max() + abs(self.tVals[-1] - self.tVals[0]) * 0.02
            elif len(self.tVals) == 1:
                start = self.tVals[0] - 0.5
                stop = self.tVals[0] + 0.5
            else:
                start = 0
                stop = 1
            
        self.imageItem.resetTransform()
        if scale is not None:
            self.imageItem.scale(*scale)
        if pos is not None:
            self.imageItem.setPos(*pos)
        if transform is not None:
            self.imageItem.setTransform(transform)
            
        if autoRange:
            self.autoRange()

    def autoLevels(self):
        """Set the min/max intensity levels automatically to match the image data."""
        self.setLevels(self.levelMin, self.levelMax)

    def setLevels(self, min, max):
        """Set the min/max (bright and dark) levels."""
        self.ui.histogram.setLevels(min, max)

    def autoRange(self):
        """Auto scale and pan the view around the image."""
        image = self.getProcessedImage()
        self.view.autoRange()
        
    def getProcessedImage(self):
        """Returns the image data after it has been processed by any normalization options in use.
        This method also sets the attributes self.levelMin and self.levelMax 
        to indicate the range of data in the image."""
        if self.imageDisp is None:
            image = self.normalize(self.image)
            self.imageDisp = image
            self.levelMin, self.levelMax = list(map(float, ImageView.quickMinMax(self.imageDisp)))
            
        return self.imageDisp
        
        
    def close(self):
        """Closes the widget nicely, making sure to clear the graphics scene and release memory."""
        self.ui.graphicsView.close()
        self.scene.clear()
        del self.image
        del self.imageDisp
        self.setParent(None)
        
    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_Home:
            self.setCurrentIndex(0)
            ev.accept()
        elif ev.key() == QtCore.Qt.Key_End:
            self.setCurrentIndex(self.getProcessedImage().shape[0]-1)
            ev.accept()
        elif ev.key() in self.noRepeatKeys:
            ev.accept()
            if ev.isAutoRepeat():
                return
            self.keysPressed[ev.key()] = 1
            self.evalKeyState()
        else:
            QtGui.QWidget.keyPressEvent(self, ev)

    def keyReleaseEvent(self, ev):
        if ev.key() in [QtCore.Qt.Key_Space, QtCore.Qt.Key_Home, QtCore.Qt.Key_End]:
            ev.accept()
        elif ev.key() in self.noRepeatKeys:
            ev.accept()
            if ev.isAutoRepeat():
                return
            try:
                del self.keysPressed[ev.key()]
            except:
                self.keysPressed = {}
            self.evalKeyState()
        else:
            QtGui.QWidget.keyReleaseEvent(self, ev)


    def evalKeyState(self):
        if len(self.keysPressed) == 1:
            key = list(self.keysPressed.keys())[0]
            if key == QtCore.Qt.Key_Right:
                self.jumpFrames(1)
            elif key == QtCore.Qt.Key_Left:
                self.jumpFrames(-1)
            elif key == QtCore.Qt.Key_Up:
                self.jumpFrames(-10)
            elif key == QtCore.Qt.Key_Down:
                self.jumpFrames(10)
            elif key == QtCore.Qt.Key_PageUp:
                self.jumpFrames(-100)
            elif key == QtCore.Qt.Key_PageDown:
                self.jumpFrames(100)


    def setCurrentIndex(self, ind, autoHistogramRange=True):
        """Set the currently displayed frame index."""
        self.currentIndex = numpy.clip(ind, 0, self.getProcessedImage().shape[0]-1)
        self.updateImage(autoHistogramRange=autoHistogramRange)

    def jumpFrames(self, n):
        """Move video frame ahead n frames (may be negative)"""
        if self.axes['t'] is not None:
            self.setCurrentIndex(self.currentIndex + n)
            self._parent.replot()

    def hasTimeAxis(self):
        return 't' in self.axes and self.axes['t'] is not None

    @staticmethod
    def quickMinMax(data):
        while data.size > 1e6:
            ax = numpy.argmax(data.shape)
            sl = [slice(None)] * data.ndim
            sl[ax] = slice(None, None, 2)
            data = data[tuple(sl)]
        return data.min(), data.max()

    def normalize(self, image):
        return image


    def updateImage(self, autoHistogramRange=True):
        ## Redraw image on screen
        if self.image is None:
            return

        image = self.getProcessedImage()

        if autoHistogramRange:
            self.ui.histogram.setHistogramRange(self.levelMin, self.levelMax)
        if self.axes['t'] is None:
            self.imageItem.updateImage(image)
        else:
            self.imageItem.updateImage(image[self.currentIndex])

    def getView(self):
        """Return the ViewBox (or other compatible object) which displays the ImageItem"""
        return self.view

    def getImageItem(self):
        """Return the ImageItem for this ImageView."""
        return self.imageItem

    def getHistogramWidget(self):
        """Return the HistogramLUTWidget for this ImageView"""
        return self.ui.histogram
