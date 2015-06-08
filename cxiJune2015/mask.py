import sys,argparse
import numpy
import h5py
import scipy.misc

def get_dims(f_name):
    with h5py.File(f_name,"r") as f:
        s = numpy.shape(f["mean"])
    list(s).pop(0)
    return tuple(s)

def get_threshold_mask(f_names, ds_name, threshold):
    d = []
    for fn in f_names:
        with h5py.File(fn, "r") as f:
            d.append(numpy.array(f[ds_name]))
    return (numpy.mean(d,axis=0) < threshold)

def get_badpixelmask(f_name):
    if f_name[-3:] == ".h5":
        with h5py.File(f_name, "r"):
            m = numpy.array(f["/data/data"])
    elif f_name[-4:] == ".png":
        m = scipy.misc.imread(f_name,flatten=True) / 255.
    return m


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hummingbird mask tool')
    parser.add_argument('-m', '--mean-threshold', metavar='mean_threshold', type=float,
                        help="Pixels with mean value above the given threshold are masked out.")
    parser.add_argument('-d', '--median-threshold', metavar='median_threshold', type=float,
                        help="Pixels with median value above the given threshold are masked out.")
    parser.add_argument('-s', '--std-threshold', metavar='std_threshold', type=float,
                        help="Pixels with standard deviation value above the given threshold are masked out.")
    parser.add_argument('-b', '--badpixelmask', metavar='file', type=str,
                        help="If the given file is an H5 file it has to contain the dataset /data/data. Dataset values that equal zero will be masked out. If the file is a PNG file black pixels will be masked out.")    
    parser.add_argument('-p', '--output-png', action='store_true',
                        help="Output also to black and white PNG. Black represent masked out regions.")
    parser.add_argument('files', metavar='file', type=str, 
                        help="H5 files created from stacks in hummingbird.", nargs="+")
    if(len(sys.argv) == 1):
        parser.print_help()
    args = parser.parse_args()

    print args

    s = get_dims(args.files[0])
    mask = numpy.ones(shape=s, dtype="bool")
    print s

    if args.mean_threshold:
        M *= get_threshold_mask(args.files, "mean", args.mean_threshold)
        
    if args.median_threshold:
        M *= get_threshold_mask(args.files, "median", args.median_threshold)

    if args.std_threshold:
        M *= get_threshold_mask(args.files, "std", args.std_threshold)

    if args.badpixelmask:
        M *= get_badpixelmask(args.badpixelmask)

    if args.output_png:
        import matplotlib.pyplot as pypl
        pypl.imsave("mask.png", M, cmap="binary_r", vmin=0, vmax=1)

    with h5py.File("mask.h5", "w") as f:
        f["data/data"] = M
