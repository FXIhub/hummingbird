#!/usr/bin/env python
import sys,argparse
import numpy
import h5py
import matplotlib.image

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hummingbird tool that converts RBG values from PNG to H5 mask. Conversion is done by round((R+G+B)/(255*3)). Black pixels are being masked out.')
    parser.add_argument('file', metavar='file', type=str, 
                        help="PNG file to be used for creating mask.")
    if(len(sys.argv) == 1):
        parser.print_help()
    args = parser.parse_args()

    img = matplotlib.image.imread(args.file)[:,:,:3].sum(2)
    img = numpy.round(img/3.)
    img = numpy.array(img, dtype="int16")
    print "Masking out %i/%i pixels (%.2f %%)." % ((img==0).sum(),img.size,(img==0).sum()/float(img.size)*100)
    
    with h5py.File("./mask_from_png.h5","w") as f:
        f["/data/data"] = img
    

    
