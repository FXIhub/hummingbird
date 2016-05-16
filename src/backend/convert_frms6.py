import struct
import numpy as np
import h5py
import sys
import os
import argparse

class Frms6_file_header():
    def __init__(self, length=1024):
        self.fmt = '2H4B80s2H932s'
        self.length = 1024
    
    def parse(self, fp):
        self.my_length, self.fh_length, self.nCCDs, self.width, self.max_height, \
            self.version, self.dataSetID, self.the_width, self.the_max_height, self.fill \
            = struct.unpack(self.fmt, fp.read(self.length))
        
        if self.my_length != self.length:
            print 'Non-standard header length:', self.my_length
            fp.seek(-self.length, 1)
            self.length = self.my_length
            self.fmt = self.fmt[:-4]+str(self.length-92)+'s'
            self.parse(fp)
        
        if not self.fill:
            return 1
        else:
            return 0
    
    def dump(self):
        print 'my_length', self.my_length
        print 'fh_length', self.fh_length
        print 'nCCDs', self.nCCDs
        print 'width', self.width
        print 'max_height', self.max_height
        print 'version', self.version
        print 'dataSetID', self.dataSetID
        print 'the_width', self.the_width
        print 'the_max_height', self.the_max_height

class Frms6_frame_header():
    def __init__(self, length=64):
        self.fmt = '4B3Id2HIL24s'
        self.length = length
        if length != 64:
            self.fmt = self.fmt[:-3]+str(length-40)+'s'
    
    def parse(self, fp):
        headstr = fp.read(self.length)
        if len(headstr) < self.length:
            return 1
        self.start, self.info, self.id, self.height, self.tv_sec, \
            self.tv_usec, self.index, self.temp, self.the_start, \
            self.the_height, self.external_id, self.bunch_id, self.fill \
            = struct.unpack(self.fmt, headstr)
        return 0
    
    def dump(self):
        print 'start',self.start
        print 'info',self.info
        print 'id',self.id
        print 'height',self.height
        print 'tv_sec',self.tv_sec
        print 'tv_usec',self.tv_usec
        print 'index',self.index
        print 'temp',self.temp
        print 'the_start',self.the_start
        print 'the_height',self.the_height
        print 'external_id',self.external_id
        print 'bunch_id',self.bunch_id

class Frms6_reader():
    def __init__(self, fname, shape_str='assem', offset=None):
        self.f = open(fname, 'rb')
        if shape_str == 'assem':
            self.shape_arg = 0
        elif shape_str == 'psana':
            self.shape_arg = 1
        elif shape_str == 'native':
            self.shape_arg = 2
        else:
            sys.stderr.write('Unknown shape_str, %s. Defaulting to native shape')
            self.shape_arg = 2
        
        self.file_header = Frms6_file_header()
        self.file_header.parse(self.f)
        self.nx = self.file_header.the_width
        self.ny = self.file_header.the_max_height
        print 'nx ny =', self.nx, self.ny
        if offset is None:
            self.offset = self.arg_reshape(np.zeros((self.nx, self.ny)))
        else:
            self.offset = offset
    
    def parse_frames(self, start_num=0, num_frames=-1):
        self.f.seek(self.file_header.my_length + start_num*(self.file_header.fh_length + self.nx*self.ny*2))
        self.frame_headers = []
        self.frames = []
        i = 0
        if num_frames == 0:
            return
        
        while True:
            self.frame_headers.append(Frms6_frame_header(length=self.file_header.fh_length))
            ret = self.frame_headers[-1].parse(self.f)
            if ret != 0:
                self.frame_headers = self.frame_headers[:-1]
                break
            self.frames.append(self.arg_reshape(np.fromfile(self.f, '=i2', count=self.nx*self.ny))-self.offset)
            i += 1
            #sys.stderr.write('\rParsed %d frames' % i)
            if num_frames > 0 and i >= num_frames:
                break
        #sys.stderr.write('\n')

    def frms6_to_psana(self, a):
        return a.reshape(512,4,512).transpose(1,0,2)
    
    def psana_to_assem(self, a):
        return np.concatenate((np.concatenate((a[0],np.rot90(a[1],2))),np.concatenate((a[3],np.rot90(a[2],2)))),axis=1)
    
    def arg_reshape(self, a):
        a = a.reshape(self.nx, self.ny)
        if self.shape_arg == 2:
            return a
        elif self.shape_arg == 1:
            return self.frms_to_psana(a)
        elif self.shape_arg == 0:
            return self.psana_to_assem(self.frms6_to_psana(a))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert frms6 file to h5')
    parser.add_argument('fname', help='Path to frms6 file to be converted')
    parser.add_argument('-n', '--num_frames', help='Number of frames to parse. Default=-1 (all)', type=int, default=-1)
    parser.add_argument('-s', '--start_num', help='Start from frame number. Default=0', type=int, default=0)
    parser.add_argument('-o', '--output_fname', help='Path to output h5 file. Default=<fname_without_ext>.h5')
    args = parser.parse_args()
    
    if args.output_fname is None:
        args.output_fname = os.path.splitext(os.path.basename(args.fname))[0]+'.h5'
    
    reader = Frms6_reader(args.fname, num_frames=args.num_frames, start_num=args.start_num)
    reader.parse_frames(num_frames=args.num_frames, start_num=args.start_num)
    reader.f.close()
    
    print 'Writing to', args.output_fname
    with h5py.File(args.output_fname, 'w') as hf:
        hf['data/data'] = np.array(reader.frames)
        hf['meta/external_id'] = np.array([h.external_id for h in reader.frame_headers])
        hf['meta/tv_sec'] = np.array([h.tv_sec for h in reader.frame_headers])
        hf['meta/tv_usec'] = np.array([h.tv_usec for h in reader.frame_headers])
        hf['meta/temp'] = np.array([h.temp for h in reader.frame_headers])
        hf['meta/dataSetID'] = np.string_(reader.file_header.dataSetID.rstrip('\0'))

