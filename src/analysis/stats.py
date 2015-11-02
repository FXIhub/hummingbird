import numpy

class DataStatistics:
    def __init__(self, length = 100):
        self._buffer = None
        self._n = 0.0
        self._len = length
        self._lambda = numpy.log(2)/(self._len/2)

    def add(self, data):
        if self._n == 0.0:
            self._mean = numpy.copy(data)
            self._min = numpy.copy(data)
            self._min_index = numpy.zeros(data.shape,dtype=numpy.int32)
            self._max = numpy.copy(data)
            self._max_index = numpy.zeros(data.shape,dtype=numpy.int32)
        else:
            self._mean = (1-self._lambda)*self._mean + self._lambda*data
            # "Wear out" old minimas
            self._min += abs(self._min)*(self._lambda)
            self._min = numpy.minimum(self._min, data)
            # "Wear out" old maximums
            self._max -= abs(self._max)*(self._lambda)
            self._max = numpy.maximum(self._max, data)
        self._n += 1.0

    def mean(self):
        return self._mean

    def min(self):
        return self._min

    def max(self):
        return self._max        
        
