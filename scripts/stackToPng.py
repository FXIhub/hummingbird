#!/usr/bin/env python
import sys,argparse
import numpy
import h5py
import scipy.misc
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

def get_mean(f_names, ds_name):
    d = []
    for fn in f_names:
        with h5py.File(fn, "r") as f:
            d.append(numpy.array(f[ds_name]))
    return numpy.mean(d,axis=0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hummingbird tool that plots PNGs from stack files')
    parser.add_argument('-n', '--name-prefix', metavar='name-prefix', type=str,
                        help="Filename prefix.")    
    parser.add_argument('-d', '--dataset', metavar='dataset', type=str, 
                        help="Specify dataset if you only want to plot only a particular dataset [mean, median, std, sum]")
    parser.add_argument('-l', '--vmin', metavar='vmin', type=float,
                        help="Lower boundary for color scale")
    parser.add_argument('-u', '--vmax', metavar='vmax', type=float,
                        help="Upper boundary for color scale")    
    parser.add_argument('-p', '--plain', action='store_true',
                        help="Create image without colorbar and labels")    
    parser.add_argument('files', metavar='file', type=str, 
                        help="H5 files with stack data (i.e. mean, median, std, etc.)", nargs="+")
    if(len(sys.argv) == 1):
        parser.print_help()
    args = parser.parse_args()

    if args.dataset:
        outputs = [args.dataset]
    else:
        outputs = ["mean","median","std","sum"]

    if args.name_prefix:
        p = args.name_prefix + "-"
    else:
        p = ""
    
    for o in outputs:
        d = get_mean(args.files, o)
        if args.plain:
            plt.imsave("%s%s.png" % (p,o))
        else:
            fig = plt.figure()
            ax = fig.add_subplot(111,title="%s%s" % (p,o))
            cax = ax.imshow(d, vmin=args.vmin, vmax=args.vmax)
            fn = "%s%s.png" % (p,o)
            fig.colorbar(cax)
            fig.savefig(fn)
            plt.clf()
