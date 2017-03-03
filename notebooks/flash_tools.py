import numpy as np
import h5py
import os, sys

root_dir = os.path.abspath(".") + "/../"
sys.path.append(root_dir)
import params

this_folder = os.path.dirname(os.path.realpath(__file__))
data_folder = "/Users/hantke/flash_mnt/asap3/flash/gpfs/bl1/2017/data/11001733/processed"
def get_filename(run_nr, sub_folder, ol):
    return "%s/%s/r%04i_ol%i.h5" % (data_folder, sub_folder, run_nr, ol)

def file_exists(run_nr, sub_folder="hummingbird",ol=1):
    return os.path.exists(get_filename(run_nr=run_nr, sub_folder=sub_folder, ol=ol))

def read_data(name, run_nr, i=None, sub_folder="hummingbird_multiple", ol=5):
    if not file_exists(run_nr=run_nr, sub_folder=sub_folder, ol=ol):
        print "WARNING: File does not exist."
        return None
    filename_h5 = get_filename(run_nr=run_nr, sub_folder=sub_folder, ol=ol)
    with h5py.File(filename_h5, "r") as f:
        if name not in f:
            return None
        ds = f[name]
        if i is None:
            return np.asarray(ds)
        elif i >= ds.shape[0]:
            return None
        else:
            return np.asarray(ds[i])

def read_intensities(run_nr, i=None, sub_folder="hummingbird_multiple"):
    return read_data(name="/entry_1/data_1/data", run_nr=run_nr, i=i, sub_folder=sub_folder)

def read_patterson(run_nr, i=None):
    return read_data(name="/entry_1/data_1/patterson", run_nr=run_nr, i=i, sub_folder="hummingbird_multiple")

def read_patterson_mask(run_nr, i=None):
    return read_data(name="/entry_1/data_1/patterson_mask", run_nr=run_nr, i=i, sub_folder="hummingbird_multiple")

def read_hitscores(run_nr, sub_folder="hummingbird", ol=1):
    return read_data(name="/entry_1/result_1/hitscore_litpixel", run_nr=run_nr, sub_folder=sub_folder, ol=ol)

def read_mulscores(run_nr, sub_folder="hummingbird", ol=1):
    return read_data(name="/entry_1/result_1/multiscore_patterson", run_nr=run_nr, sub_folder=sub_folder, ol=ol)

def read_n_frames(run_nr, sub_folder="hummingbird", ol=1):
    d = read_data(name="/entry_1/event/bunch_id", run_nr=run_nr, sub_folder=sub_folder, ol=ol)
    return (None if d is None else len(d))
        
def read_injz(run_nr, sub_folder="hummingbird_multiple", ol=1):
    return read_data(name="/entry_1/motors/injectory", run_nr=run_nr, sub_folder=sub_folder, ol=ol)

def read_injx(run_nr, sub_folder="hummingbird_multiple", ol=1):
    return read_data(name="/entry_1/motors/injectorx", run_nr=run_nr, sub_folder=sub_folder, ol=ol)

def read_tv(run_nr):
    return read_data(name="/entry_1/event/tv_sec", run_nr=run_nr, ol=ol)

def _calc_rate(mode, run_nr, threshold=None):
    if mode == "hit":
        read_scores = read_hitscores
        threshold_name = 'hitscoreThreshold'
    elif mode == "mul":
        read_scores = read_mulscores
        threshold_name = 'multiscoreThreshold'
    else:
        print "ERROR: illegal mode %s" % mode
        return
    n_frames = read_n_frames(run_nr=run_nr, ol=1)
    scores = read_scores(run_nr=run_nr, ol=1)
    if n_frames is None or scores is None:
        return None
    else:
        if threshold is None:
            params_fn = "%s/../params.csv" % (this_folder)
            T = params.read_params(params_fn, run_nr)[threshold_name]
        else:
            T = threshold
        n = (scores > T).sum()
        return (float(n)/float(n_frames))

def calc_hitrate(run_nr, threshold=None, ol=1):
    return _calc_rate(mode="hit", run_nr=run_nr, threshold=threshold)

def calc_mulrate(run_nr, threshold=None, ol=1):
    return _calc_rate(mode="mul", run_nr=run_nr, threshold=threshold)
