import numpy

class RingBuffer(object):
    def __init__(self, maxlen, dtype=float, order='C'):
        self._data = numpy.empty((2*maxlen), dtype, order)
        self._index = 0
        self._len = 0
        self._maxlen = maxlen

    def append(self, x):
        self._data[self._index] = x
        self._data[self._index + self._maxlen] = x
        self._index = (self._index + 1) % self._maxlen
        if(self._len < self._maxlen):
            self._len += 1
        
    def __array__(self):
        return self._data[self._maxlen+self._index-self._len:self._maxlen+self._index]

    def __len__(self):
        return self._len

    def clear(self):
        self._len = 0
        self._index = 0

    @property
    def shape(self):
        return (self._len)        

    def __getitem__(self, args):
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
            return self._data[start:stop:args.step]
        else:
            return self._data[args+self._maxlen+self._index-self._len]



