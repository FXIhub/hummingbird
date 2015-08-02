import os
import collections
import ipc
import numpy
from numpy import abs
import h5py
import time, datetime
from datetime import datetime as DT
import pytz
import logging

class Stack:
    def __init__(self,name="stack",maxLen=100,reducePeriod=None,outPeriod=None, outputs=None):
        self._maxLen = maxLen
        self._outPeriod = outPeriod
        self._reducePeriod = reducePeriod
        self._name = name
        self.clear()
        if outputs is None:
            self._outputs = ["std","mean","sum","median","min","max"]
        else:
            self._outputs = outputs
        
    def clear(self):
        self._buffer = None
        self._currentIndex = 0
        n = ipc.mpi.nr_workers()
        if n > 1 and self._outPeriod is not None:
            self._outIndex = int(float(ipc.mpi.rank) / float(n-1) * (self._outPeriod-1))
        else:
            self._outIndex = 0
        if n > 1 and self._reducePeriod is not None:
            self._reduceIndex = int(float(ipc.mpi.rank) / float(n-1) * (self._reducePeriod-1))
        else:
            self._reduceIndex = 0
        self.last_std    = None
        self.last_mean   = None
        self.last_sum    = None
        self.last_median = None
        self.last_min    = None
        self.last_max    = None
        self._reduced     = False

    def filled(self):
        return self._currentIndex >= self._maxLen
    
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
    
    def min(self):
        self.last_min = self._getData().min(axis=0)
        return self.last_min

    def max(self):
        self.last_max = self._getData().max(axis=0)
        return self.last_max

    def reduce(self):
        if self._reducePeriod is not None:
            if (self._currentIndex % self._reducePeriod) != self._outIndex:
                return
        if not self.filled():
            return
        logging.debug('Reducing Stack %s' % (self._name))
        for o in self._outputs:
            exec "self.%s()" % o
        self._reduced = True

    def write(self,evt, directory=".", verbose=True):
        # Postpone writing?
        if self._outPeriod is not None:
            if (self._currentIndex % self._outPeriod) != self._outIndex:
                return
        if not self._reduced:
            if verbose:
                print "Postponing writing stack to file because stack is not reduced yet. Fill status %i/%i." % (self._currentIndex+1, self._maxLen)
            return
        # Timestamp for filename
        dt = evt["eventID"]["Timestamp"].data
        fid = evt["eventID"]["Timestamp"].fiducials
        ts = dt.strftime("%Y%m%d-%H%M%S-%f")
        fn = "%s/%s-%s-fid%s-rk%i.h5" % (directory,self._name, ts, fid, ipc.mpi.rank)
        # Write to H5
        if verbose:
            print "Writing stack to %s" % fn
        d = os.path.dirname(os.path.realpath(fn))
        if not os.path.isdir(d):
            os.makedirs(d)
        with h5py.File(fn,"w") as f:
            for o in self._outputs:
                exec "f[\"%s\"] = self.last_%s" % (o,o)
