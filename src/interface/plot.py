from ringbuffer import RingBuffer
import pyqtgraph
import numpy
from Qt import QtGui, QtCore

class Plot(object):
    def __init__(self, source_uuid, source_hostname, title, maxlen = 1000, dtype = float):
        self._uuid = source_uuid
        self._hostname = source_hostname
        self._title = title
        self._data = RingBuffer(maxlen, dtype)      
        self._widget = None

    def set_data(self, data):
        self._data.clear()
        for x in data:
            self._data.append(x)

    def append(self, data):      
        for x in data:
            self._data.append(x)

    def _init_widget(self):
        self._widget = pyqtgraph.plot(numpy.array(self._data, copy=False), title=self._title, antialias=True)
        
    def replot(self):
        if(self._widget is None):
            self._init_widget()
        self._widget.plot(numpy.array(self._data, copy=False), clear=True)
            
        
        
