import struct
import numpy as np
import h5py
import sys
import os
import argparse

# Compatibility with python 2 and 3
from __future__ import print_function

class darkcal_reader():
    def __init__(self, fname, shape_str='assem'):
        self.f = open(fname, 'rb')
        self.fname = fname
        self.fmt = 'ddddihh' # Last two bits are padding
        if shape_str == 'assem':
            self.shape_arg = 0
        elif shape_str == 'psana':
            self.shape_arg = 1
        elif shape_str == 'native':
            self.shape_arg = 2
        else:
            sys.stderr.write('Unknown shape_str, %s. Defaulting to native shape')
            self.shape_arg = 2
        
        self.header = self.f.read(24).rstrip('\0')
        self.nx, self.ny, self.n = struct.unpack('III', self.f.read(12))
        self.f.seek(1024, 0)
    
    def parse_stats(self):
        self.sums = np.zeros((self.n,), dtype='f8')
        self.offset = np.zeros((self.n,), dtype='f8')
        self.sigma = np.zeros((self.n,), dtype='f8')
        self.sumSq = np.zeros((self.n,), dtype='f8')
        self.count = np.zeros((self.n,), dtype='i4')
        self.mean = np.zeros((self.n,), dtype='i2')
         
        for i in range(self.n):
            stats = struct.unpack(self.fmt, self.f.read(40))
            self.sums[i] = stats[0]
            self.offset[i] = stats[1]
            self.sigma[i] = stats[2]
            self.sumSq[i] = stats[3]
            self.count[i] = stats[4]
            self.mean[i] = stats[5]
            if i%100 == 0:
                sys.stderr.write('\rWritten pixel %d/%d' % (i+1, self.n))
        sys.stderr.write('\rWritten pixel %d/%d' % (self.n, self.n))
        sys.stderr.write('\n')
        
        self.sums = self.arg_reshape(self.sums.reshape(self.nx,self.ny))
        self.offset = self.arg_reshape(self.offset.reshape(self.nx,self.ny))
        self.sigma = self.arg_reshape(self.sigma.reshape(self.nx,self.ny))
        self.sumSq = self.arg_reshape(self.sumSq.reshape(self.nx,self.ny))
        self.count = self.arg_reshape(self.count.reshape(self.nx,self.ny))
        self.mean = self.arg_reshape(self.mean.reshape(self.nx,self.ny))

    def frms6_to_psana(self, a):
        return a.reshape(512,4,512).transpose(1,0,2)
    
    def psana_to_assem(self, a):
        return np.concatenate((np.concatenate((a[0],np.rot90(a[1],2))),np.concatenate((a[3],np.rot90(a[2],2)))),axis=1)
    
    def arg_reshape(self, a):
        if self.shape_arg == 2:
            return a
        elif self.shape_arg == 1:
            return self.frms_to_psana(a)
        elif self.shape_arg == 0:
            return self.psana_to_assem(self.frms6_to_psana(a))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert frms6 file to h5')
    parser.add_argument('fname', help='Path to darkcal file to be converted')
    parser.add_argument('-o', '--output_fname', help='Path to output h5 file. Default=<fname_without_ext>.h5')
    args = parser.parse_args()
    
    if args.output_fname is None:
        args.output_fname = os.path.basename(args.fname) +'.h5'
    
    reader = darkcal_reader(args.fname)
    reader.parse_stats()
    reader.f.close()

    with h5py.File(args.output_fname, 'w') as f:
        print('Writing dark to', f.filename)
        f['data/sum'] = reader.sums
        f['data/offset'] = reader.offset
        f['data/sigma'] = reader.sigma
        f['data/sumSq'] = reader.sumSq
        f['data/count'] = reader.count
        f['data/mean'] = reader.mean
