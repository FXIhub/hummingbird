import struct

import numpy


def lcls2float(t):
   if isinstance(t, numpy.ndarray):
      t0 = numpy.right_shift(t.astype(numpy.uint64), numpy.uint64(32))
   else:
      t0 = numpy.right_shift(numpy.uint64(t), numpy.uint64(32))
   t1 = numpy.bitwise_and(numpy.uint64(t), numpy.uint64(0x00000000fffffffff))
   t2 = t0 + t1*1.e-9
   return t2
