from ringbuffer import RingBuffer
import numpy
from Qt import QtGui, QtCore
from ui import PlotWindow

class PlotData(QtCore.QObject):
    def __init__(self, parent, title, maxlen = 1000):
        QtCore.QObject.__init__(self,parent)
        self._title = title
        self._y = None
        self._x = None
        self._widget = None
        self._parent = parent
        self._maxlen = maxlen
        if('history_length' in parent.conf[title]):
            self._maxlen = parent.conf[title]['history_length']

    def set_data(self, yy):
        if(self._y is None):
            self._y = RingBuffer(self._maxlen)
        else:
            self._y.clear()
        for y in yy:
            self._y.append(y)

    def append(self, y, x):
        if(self._y is None):
            if(isinstance(y,numpy.ndarray)):
                # Make sure the image ringbuffers don't take more than
                # 200 MBs. The factor of 2 takes into account the fact
                # that the buffer is twice as big as its usable size
                self._y = RingBuffer(max(1,min(self._maxlen,
                                               1024*1024*200/(2*y.nbytes))))
            else:
                self._y = RingBuffer(self._maxlen) 
        if(self._x is None):
            self._x = RingBuffer(self._y._maxlen)

        self._y.append(y)            
        self._x.append(x)
