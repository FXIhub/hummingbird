import struct

def lcls2float(t):
   t0 = t >> 32
   t1 = t & struct.pack('L', 0x00000000fffffffff)
   return t0 + t1*1e-9
