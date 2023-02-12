# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Provides a ring buffer for scalar and numpy data.
It's always possible to retrieve the buffer data as a numpy array in O(1)
This is achieve by always inserting two copies of any appended data, so
it's a bit slower to add data, and it takes twice as much memory as a
regular buffer.
"""

import numpy


class RingBuffer(object):
    """Provides a ring buffer for scalar and numpy data.
    It's always possible to retrieve the buffer data as a numpy array in O(1)
    This is achieve by always inserting two copies of any appended data, so
    it's a bit slower to add data, and it takes twice as much memory as a
    regular buffer.
    """
    def __init__(self, maxlen, data = None, index = 0, length = 0):
        self._index = index
        self._len = length
        self._maxlen = maxlen
        self._data = data
        self._counter = 0
        
    def append(self, x):
        """Append a value to the end of the buffer"""
        if(self._data is None):
            self._init_data(x)
        try:
            self._data[self._index] = x
        except ValueError:
            self._init_data(x)
            self._index = 0
            self._len = 0
            self._data[self._index] = x

        self._data[self._index + self._maxlen] = x
        self._index = (self._index + 1) % self._maxlen
        if(self._len < self._maxlen):
            self._len += 1
        self._counter += 1

    def resize(self, new_maxlen):
        """Change the capacity of the buffers"""
        tmp_data = self._data
        x = self[-1]
        # Initialize new array
        prev_maxlen = self._maxlen
        self._maxlen = new_maxlen
        self._init_data(x)
        # Copy existing data
        self._len = min(self._len,new_maxlen)
        self._data[0:self._len] = tmp_data[prev_maxlen+self._index-self._len:prev_maxlen+self._index]
        self._data[self._maxlen:self._maxlen+self._len] = tmp_data[prev_maxlen+self._index-self._len:prev_maxlen+self._index]
        self._index = self._len % self._maxlen
        # Preserve dtype, otherwise dtype.metadata is lost
        self._data.dtype = tmp_data.dtype

    def _init_data(self, x):
        """Initialize the buffer with the given data"""
        try:
            self._data = numpy.empty(tuple([2*self._maxlen]+list(x.shape)),
                                     x.dtype)
        except AttributeError:
            self._data = numpy.empty([2*self._maxlen], type(x))

    def __array__(self):
        """Return a numpy array with the buffer data"""
        return self._data[self._maxlen+self._index-self._len:self._maxlen+self._index]

    def __len__(self):
        """Return the length of the buffer"""
        return self._len

    def clear(self):
        """Empty the buffer"""
        self._len = 0
        self._index = 0

    @property
    def shape(self):
        """Returns the shape of the buffer, like a numpy array"""
        if(len(self._data.shape) == 1):
            return (self._len,)
        else:
            return (self._len,)+self._data.shape[1:]

    @property
    def max(self):
        """Returns the maximum value in the buffer, like a numpy array"""
        return self.__array__().max()

    @property
    def min(self):
        """Returns the minimum value in the buffer, like a numpy array"""
        return self.__array__().min()
    
    def _convert_dim(self, args):
        """Convert getitem arguments into internal indexes"""
        if(isinstance(args, slice)):
            start = self._maxlen+self._index-self._len
            if(args.start is None):
                if(args.step is not None and args.step < 0):
                    start = self._maxlen+self._index-1
            elif(args.start > 0):
                start += args.start
            elif(args.start < 0):
                start += args.start + self._len

            stop = self._maxlen+self._index
            if(args.stop is None):
                if(args.step is not None and args.step < 0):
                    stop = self._maxlen+self._index-self._len-1
            elif(args.stop > 0):
                stop += args.stop-self._len
            elif(args.stop < 0):
                stop += args.stop
            return slice(start, stop, args.step)
        else:
            if args < 0:
                args = self._len + args
            return self._maxlen+self._index-self._len + args

    def __getitem__(self, args):
        """Returns items from the buffer, just like a numpy array"""
        if(isinstance(args, tuple)):
            args = list(args)
            args[0] = self._convert_dim(args[0])
            return self._data[tuple(args)]
        else:
            return self._data[self._convert_dim(args)]
        
    @property
    def nbytes(self):
        """Returns the number of bytes taken by the buffer"""
        return self._data.nbytes

    def save_state(self):
        """Return a serialized representation of the RingBuffer for saving to disk"""
        rs = {}
        rs['index'] = self._index
        rs['len'] = self._len
        rs['maxlen'] = self._maxlen
        rs['data'] = self._data
        return rs
        
    @staticmethod
    def restore_state(state):
        data = numpy.array(state['data'])
        index = state['index']
        length = state['len']
        maxlen = state['maxlen']
        rb = RingBuffer(maxlen, data = data, index = index, length = length)
        return rb

    @property
    def number_of_added_elements(self):
        return self._counter

        
class RingBufferStr(object):
    """Provides a ring buffer for strings."""
    def __init__(self, maxlen, data = None, index = 0, length = 0):
        self._index = index
        self._len = length
        self._maxlen = maxlen
        self._data = data
        self._counter = 0
        
    def append(self, x):
        """Append a value to the end of the buffer"""
        if(self._data is None):
            self._init_data()
        self._data[self._index] = x
        self._index = (self._index + 1) % self._maxlen
        if(self._len < self._maxlen):
            self._len += 1
        self._counter = 0

    def resize(self, new_maxlen):
        """Change the capacity of the buffers"""
        tmp_data = self._data
        # Initialize new list
        prev_maxlen = self._maxlen
        self._maxlen = new_maxlen
        self._init_data()
        # Copy existing data
        self._len = min(self._len,new_maxlen)
        self._data[:self._len] = tmp_data
        self._index = self._len % self._maxlen

    def _init_data(self):
        """Initialize the buffer with the given data"""
        self._data = [None for i in range(self._maxlen)]
        
    def __len__(self):
        """Return the length of the buffer"""
        return self._len

    def clear(self):
        """Empty the buffer"""
        self._len = 0
        self._index = 0

    def __getitem__(self, index):
        """Returns items from the buffer"""
        if index == (self._len - 1):
            index = self._index - 1
        return self._data[index]
    
    @property
    def nbytes(self):
        """Returns the number of bytes taken by the buffer"""
        return self._data.nbytes

    def save_state(self):
        """Return a serialized representation of the buffer for saving to disk"""
        rs = {}
        rs['index'] = self._index
        rs['len'] = self._len
        rs['maxlen'] = self._maxlen
        rs['data'] = self._data
        return rs
        
    @staticmethod
    def restore_state(state):
        data = state['data']
        index = state['index']
        length = state['len']
        maxlen = state['maxlen']
        rb = RingBufferStr(maxlen, data = data, index = index, length = length)
        return rb
        
    @property
    def number_of_added_elements(self):
        return self._counter
