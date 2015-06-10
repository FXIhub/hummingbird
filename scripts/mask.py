#!/usr/bin/env python
import sys,argparse
import numpy
import os
import time, datetime
import h5py
import scipy.misc
import configobj

def get_valid_stacks(f_names):
    f_names_valid = []
    for fn in f_names:
        with h5py.File(fn,"r") as f:
            if "mean" in f.keys():
                f_names_valid.append(fn)
    return f_names_valid

def get_dims(f_name):
    with h5py.File(f_name,"r") as f:
        s = numpy.shape(f["mean"])
    list(s).pop(0)
    return tuple(s)

def get_max_mask(f_names, ds_name, threshold):
    d = []
    for fn in f_names:
        with h5py.File(fn, "r") as f:
            d.append(numpy.array(f[ds_name]))
    return (numpy.mean(d,axis=0) < threshold)

def get_min_mask(f_names, ds_name, threshold):
    d = []
    for fn in f_names:
        with h5py.File(fn, "r") as f:
            d.append(numpy.array(f[ds_name]))
    return (numpy.mean(d,axis=0) > threshold)

def get_badpixelmask(f_name):
    if f_name[-3:] == ".h5":
        with h5py.File(f_name, "r"):
            m = numpy.array(f["/data/data"])
    elif f_name[-4:] == ".png":
        m = scipy.misc.imread(f_name,flatten=True) / 255.
    return m


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hummingbird mask tool. Creates mask from stack files in current directory and given configuration file.')
    parser.add_argument('config', type=str,
                        help="Configuration file")
    parser.add_argument('-l', '--link', type=str, help="Creates symbolic link to the H5 mask from given path")
    if(len(sys.argv) == 1):
        parser.print_help()
    args = parser.parse_args()

    C = configobj.ConfigObj(args.config)
    
    files = os.listdir(".")
    files = [f for f in files if len(f) > 3]
    files = [f for f in files if f[-3:] == ".h5"]
    files = get_valid_stacks(files)

    if len(files) == 0:
        sys.exit(0)

    s = get_dims(files[0])
    mask = numpy.ones(shape=s, dtype="bool")

    if C["mean_max"].lower() != 'none':
        mask *= get_max_mask(files, "mean", float(C["mean_max"]))

    if C["std_max"].lower() != 'none':
        mask *= get_max_mask(files, "std", float(C["std_max"]))

    if C["median_max"].lower() != 'none':
        mask *= get_max_mask(files, "median", float(C["median_max"]))

    if C["mean_min"].lower() != 'none':
        mask *= get_min_mask(files, "mean", float(C["mean_min"]))

    if C["std_min"].lower() != 'none':
        mask *= get_min_mask(files, "std", float(C["std_min"]))

    if C["median_min"].lower() != 'none':
        mask *= get_min_mask(files, "median", float(C["median_min"]))

    if C["badpixelmask"].lower() != 'none':
        mask *= get_badpixelmask(C["badpixelmask"])

    fn_root = files[-1].split("/")[-1][:-3]
    outdir = C["outdir"]

    os.system("mkdir -p %s" % outdir)

    if bool(C["output_png"].lower()):
        import matplotlib.pyplot as pypl
        pypl.imsave("%s/mask_%s.png" % (outdir,fn_root), mask, cmap="binary_r", vmin=0, vmax=1)

    with h5py.File("%s/mask_%s.h5" % (outdir,fn_root), "w") as f:
        f["data/data"] = mask

    os.system("cp %s %s/mask_%s.conf" % (args.config,outdir,fn_root))

    if args.link:
        os.system("ln -s -f %s/mask_%s.h5 %s" % (outdir, fn_root, args.link))
