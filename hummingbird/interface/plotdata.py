# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Stores the data associated with a given broadcast"""
import numpy

from .ringbuffer import RingBuffer, RingBufferStr


class PlotData(object):
    """Stores the data associated with a given broadcast"""
    def __init__(self, parent, title, maxlen=1000, group=None):
        self._title = title
        self._group = group
        self._y = None # pylint: disable=invalid-name
        self._x = None # pylint: disable=invalid-name
        self._l = None # pylint: disable=invalid-name
        self._parent = parent
        self._maxlen = maxlen
        self.restored = False
        self.ishistory = (title[:7] == 'History')
        self.recordhistory = False
        self.clear_histogram = False
        if title in parent.conf:
            if('history_length' in parent.conf[title]):
                self._maxlen = parent.conf[title]['history_length']

    def append(self, y, x, l):
        """Append the new data to the ringbuffers"""
        if(self._y is None):
            if(isinstance(y, numpy.ndarray)):
                # Make sure the image ringbuffers don't take more than
                # 200 MBs. The factor of 2 takes into account the fact
                # that the buffer is twice as big as its usable size
                self._maxlen = max(1, min(self._maxlen, 1024*1024*200//(2*y.nbytes)))
            self._y = RingBuffer(self._maxlen)
        if(self._x is None):
            self._x = RingBuffer(self._maxlen)
        if(self._l is None):
            self._l = RingBufferStr(self._maxlen)
        self._y.append(y)
        self._x.append(x)
        self._l.append(l)

    def sum_over(self, y, x, l):
        if self._y is None:
            self._y = RingBuffer(1)
            self._x = RingBuffer(1)
            self._l = RingBufferStr(1)
            self._x.append(x)
            self._y.append(y.astype('f8'))
            self._l.append(l)
            self._num = 1.
            self._y._data[0] = y
        else:
            self._num += 1.
            self._y._data[0] = self._y._data[0] * (self._num-1)/self._num + y/self._num

    def resize(self, new_maxlen):
        """Change the capacity of the buffers"""
        if(self._y is not None):
            self._y.resize(new_maxlen)
        if(self._x is not None):
            self._x.resize(new_maxlen)
        if(self._l is not None):
            self._l.resize(new_maxlen)
        self._maxlen = new_maxlen

    def clear(self):
        """Clear the buffers"""
        if(self._y is not None):
            self._y.clear()
            self._y = None
        if(self._x is not None):
            self._x.clear()
        if(self._l is not None):
            self._l.clear()
        self.clear_histogram = True

    @property
    def title(self):
        """Returns the plot data title"""
        return self._title

    @property
    def group(self):
        """Returns the plot group"""
        return self._group

    @property
    def y(self):
        """Gives access to the y buffer"""
        return self._y

    @property
    def x(self):
        """Gives access to the x buffer"""
        return self._x

    @property
    def l(self):
        """Gives access to the l buffer"""
        return self._l

    @property
    def maxlen(self):
        """Gives access to maximum size of the buffers"""
        return self._maxlen

    def __len__(self):
        """Returns the number of elements in the buffers"""
        if(self._y is not None):
            return len(self._y)
        else:
            return 0

    @property
    def nbytes(self):
        """Returns the number of bytes taken by the three buffers"""
        if(self._y is not None):
            return self._y.nbytes + self._x.nbytes + self._y.nbytes
        return 0

    def save_state(self, save_data=False):
        """Return a serialized representation of the PlotData for saving to disk"""
        pds = {}
        pds['data_source'] = [self._parent.hostname, self._parent.port, self._parent.ssh_tunnel]
        if(save_data):
            pds['x'] = self.x.save_state()
            pds['y'] = self.y.save_state()
            pds['l'] = self.l.save_state()
        pds['title'] = self.title
        pds['group'] = self.group
        pds['maxlen'] = self.maxlen
        pds['recordhistory'] = self.recordhistory
        return pds

    def restore_state(self, state, parent):
        """Restore a previous stored state"""
        self.parent = parent
        if 'x' in state:
            self._x = RingBuffer.restore_state(state['x'])
            self._y = RingBuffer.restore_state(state['y'])
            self._l = RingBufferStr.restore_state(state['l'])
            self.restored = True
        self._title = state['title']
        self._maxlen = state['maxlen']
        self.recordhistory = state['recordhistory']
