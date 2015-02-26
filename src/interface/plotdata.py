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
                        
        
