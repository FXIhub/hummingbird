import struct
import numpy

def lcls2float(t):
   #if isinstance(t, numpy.number):
   print t, type(t)
   t0 = numpy.right_shift(t, 32)
   #else:
   #   t0 = t >> 32
   t1 = t & 0x00000000fffffffff
   return t0 + t1*1e-9
