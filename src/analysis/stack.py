import collections
import ipc
import numpy
from numpy import abs
import h5py
import time

class Stack:
    def __init__(self,name="stack",maxLen=100,rank=0):
        self._rank = rank
        self._maxLen = maxLen
        self._name = name
        self.clear()
    def clear(self):
        self._buffer = None
        self._currentIndex = 0
        self.last_std    = None
        self.last_mean   = None
        self.last_sum    = None
        self.last_median = None
    def filled(self):
        return self._currentIndex > self._maxLen
    def add(self,data):
        if self._buffer is None:
            s = tuple([self._maxLen] + list(data.shape))
            self._buffer = numpy.zeros(shape=s, dtype=data.dtype)
        self._buffer[self._currentIndex % self._maxLen,:] = data[:]
        self._currentIndex += 1
    def _getData(self):
        if self.filled():
            return self._buffer
        else:
            return self._buffer[:self._currentIndex]
    def std(self):
        self.last_std = self._getData().std(axis=0)
        return self.last_std
    def mean(self):
        self.last_mean = self._getData().mean(axis=0)
        return self.last_mean
    def sum(self):
        self.last_sum = self._getData().sum(axis=0)
        return self.last_sum
    def median(self):
        self.last_median = numpy.median(self._getData(),axis=0)
        return self.last_median
    def write(self,evt,directory=".",outputs=None,png=False,interval=None,verbose=True):
        if interval is not None:
            if (self._currentIndex % interval) != 0:
                return
        if outputs is None:
            outputs = ["std","mean","sum","median"]
        try:
            dt = evt["eventID"]["Timestamp"].datetime64
        except:
            dt = ""
        try:
            fid = evt["eventID"]["Timestamp"].fiducials
        except:
            fid = 0
        fn = "%s/%s-%s-%s-rank%i.h5" % (directory,self._name, dt, fid, self._rank)
        if verbose:
            print "Writing stack to %s" % fn
        with h5py.File(fn,"w") as f:
            for o in outputs:
                exec "%s = self.%s()" % (o,o)
                exec "f[\"%s\"] = %s" % (o,o)
        if png:
            import matplotlib as mpl
            mpl.use('Agg')
            import matplotlib.pyplot as plt
            for o in outputs:
                fig = plt.figure()
                ax = fig.add_subplot(111,title="%s %s (%i)" % (o,self._name,evt.event_id()))
                exec "cax = ax.imshow(%s)" % o
                fn = "%s/%s-%s-%i-%i.png" % (directory,o,self._name, evt.event_id(), self._rank) 
                fig.colorbar(cax)
                fig.savefig(fn)
                plt.clf()
                
