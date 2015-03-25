"""Stores the data associated with a given broadcast"""
from interface.ringbuffer import RingBuffer
import numpy

class PlotData(object):
    """Stores the data associated with a given broadcast"""
    def __init__(self, parent, title, maxlen=1000):
        self._title = title
        self._y = None # pylint: disable=invalid-name
        self._x = None # pylint: disable=invalid-name
        self._parent = parent
        self._maxlen = maxlen
        if('history_length' in parent.conf[title]):
            self._maxlen = parent.conf[title]['history_length']

    def set_data(self, y, x):
        """Clear the ringbuffers and fills them with the given data"""
        if(self._y is None):
            self._y = RingBuffer(self._maxlen)
        else:
            self._y.clear()
        for v in y:
            self._y.append(v)
        if(self._x is None):
            self._x = RingBuffer(self._maxlen)
        else:
            self._x.clear()
        for v in x:
            self._x.append(v)

    def append(self, y, x):
        """Append the new data to the ringbuffers"""
        if(self._y is None):
            if(isinstance(y, numpy.ndarray)):
                # Make sure the image ringbuffers don't take more than
                # 200 MBs. The factor of 2 takes into account the fact
                # that the buffer is twice as big as its usable size
                self._maxlen = max(1, min(self._maxlen, 1024*1024*200/(2*y.nbytes)))
            self._y = RingBuffer(self._maxlen)
        if(self._x is None):
            self._x = RingBuffer(self._maxlen)
        self._y.append(y)
        self._x.append(x)

    @property
    def title(self):
        """Returns the plot data title"""
        return self._title

    @property
    def y(self):
        """Gives access to the y buffer"""
        return self._y

    @property
    def x(self):
        """Gives access to the x buffer"""
        return self._x
