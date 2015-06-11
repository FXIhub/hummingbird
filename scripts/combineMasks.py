#!/usr/bin/env python
import sys,argparse
import numpy
import h5py
import matplotlib.image

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hummingbird tool that combines two H5 masks.')
    parser.add_argument('files', metavar='file', type=str, nargs="+", 
                        help="H5 files to be used for creating mask.")
    if(len(sys.argv) == 1):
        parser.print_help()
    args = parser.parse_args()

    M = []
    for fn in args.files:
        with h5py.File(fn,"r") as f:
            M.append(numpy.array(f["/data/data"],dtype="int"))
    M = numpy.array(M)
    M = M.min(0)

    with h5py.File("./mask_combined.h5","w") as f:
        f["/data/data"] = M
    

    
