from ringbuffer import RingBuffer
import pyqtgraph
import numpy
from Qt import QtGui, QtCore
from ui import PlotWindow

class PlotData(QtCore.QObject):
    def __init__(self, parent, source_uuid, source_hostname, title, maxlen = 1000):
        QtCore.QObject.__init__(self,parent)
        self._uuid = source_uuid
        self._hostname = source_hostname
        self._title = title
        self._y = None
        self._x = None
        self._widget = None
        self._maxlen = maxlen
        self._parent = parent

    def set_data(self, yy):
        if(self._y is None):
            self._y = RingBuffer(self._maxlen, type(yy))
        else:
            self._y.clear()
        for y in yy:
            self._y.append(y)

    def append(self, yy, xx):
        if(self._y is None):
            self._y = RingBuffer(self._maxlen, type(yy)) 
        if(self._x is None):
            self._x = RingBuffer(self._maxlen, type(xx)) 

        for y in yy:
            self._y.append(y)

        for x in xx:
            self._x.append(x)

    def _init_widget(self):
        if(self._x is not None):
            self._widget = pyqtgraph.plot(x = numpy.array(self._x, copy=False), 
                                          y = numpy.array(self._y, copy=False),
                                          title=self._title, antialias=True)
            self._pw = PlotWindow(self._parent)
        else:
            self._widget = pyqtgraph.plot(y = numpy.array(self._y, copy=False),
                                          title=self._title, antialias=True)
            self._pw = PlotWindow(self._parent)

        self._pw.show()
        self._widget.hideAxis('bottom')

    def replot(self):
        if(self._y is None or len(self._y) < 2):
            return
        if(self._widget is None):
            self._init_widget()
        if(self._x is not None):
            self._widget.plot(x=numpy.array(self._x, copy=False),
                              y=numpy.array(self._y, copy=False), clear=True)
        else:
            self._widget.plot(numpy.array(self._y, copy=False), clear=True)
                        
        
