import numpy as np
import h5py
import os, sys

root_dir = os.path.abspath(".") + "/../"
sys.path.append(root_dir)
import params

this_folder = os.path.dirname(os.path.realpath(__file__))
params_fn = "%s/../params.csv" % (this_folder)
data_folder_default = "/Users/hantke/flash_mnt/asap3/flash/gpfs/bl1/2017/data/11001733/processed"
#data_folder = "/Users/hantke/Work/Beamtimes/2017_flash/copied_data/"
def get_filename(run_nr, sub_folder, ol, data_folder=data_folder_default):
    return "%s/%s/r%04i_ol%i.h5" % (data_folder, sub_folder, run_nr, ol)

def file_exists(run_nr, sub_folder="hummingbird",ol=1,data_folder=data_folder_default):
    return os.path.exists(get_filename(run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder))

def read_data(name, run_nr, i=None, sub_folder="hummingbird", ol=5, data_folder=data_folder_default):
    if not file_exists(run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder):
        print "WARNING: File does not exist."
        return None
    filename_h5 = get_filename(run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder)
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

def read_keys(group_name, run_nr, sub_folder="hummingbird", ol=1, data_folder=data_folder_default):
    if not file_exists(run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder):
        print "WARNING: File does not exist."
        return None
    filename_h5 = get_filename(run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder)
    with h5py.File(filename_h5, "r") as f:
        if group_name not in f:
            return None
        if isinstance(f[group_name], h5py.Dataset):
            print "WARNING: %s is not an HDF5 group but an HDF5 dataset."
            return None
        return f[group_name].keys()

def get_index_from_bunch_id(bunch_id, run_nr, sub_folder="hummingbird", ol=1, data_folder=data_folder_default):
    bids = read_bunch_id(run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder)
    l = np.where(bids==bunch_id)        
    l = l[0]
    if len(l) == 0:
        return None
    else:
        return l[0]

def read_intensities(run_nr, i=None, sub_folder="hummingbird", ol=3, data_folder=data_folder_default):
    return read_data(name="/entry_1/data_1/data", run_nr=run_nr, i=i, sub_folder=sub_folder, ol=ol, data_folder=data_folder)

def read_tof(run_nr, i=None, sub_folder="hummingbird", ol=2, data_folder=data_folder_default):
    return read_data(name="/entry_1/data_2/data", run_nr=run_nr, i=i, sub_folder=sub_folder, ol=ol, data_folder=data_folder)

def read_patterson(run_nr, i=None, data_folder=data_folder_default):
    return read_data(name="/entry_1/data_1/patterson", run_nr=run_nr, i=i, sub_folder="hummingbird", data_folder=data_folder)

def read_patterson_mask(run_nr, i=None, data_folder=data_folder_default):
    return read_data(name="/entry_1/data_1/patterson_mask", run_nr=run_nr, i=i, sub_folder="hummingbird", data_folder=data_folder)

def read_hitscores(run_nr, sub_folder="hummingbird", ol=1, data_folder=data_folder_default):
    return read_data(name="/entry_1/result_1/hitscore_litpixel", run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder)

def read_mulscores(run_nr, sub_folder="hummingbird", ol=1, data_folder=data_folder_default):
    return read_data(name="/entry_1/result_1/multiscore_patterson", run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder)

def read_n_frames(run_nr, sub_folder="hummingbird", ol=1, data_folder=data_folder_default):
    d = read_data(name="/entry_1/result_1/hitscore_litpixel", run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder)
    return (None if d is None else len(d))
        
def read_injz(run_nr, sub_folder="hummingbird", ol=1, data_folder=data_folder_default):
    return read_data(name="/entry_1/motors/injectory", run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder)

def read_injx(run_nr, sub_folder="hummingbird", ol=1, data_folder=data_folder_default):
    return read_data(name="/entry_1/motors/injectorx", run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder)

def read_tv(run_nr, ol=1, data_folder=data_folder_default):
    return read_data(name="/entry_1/event/tv_sec", run_nr=run_nr, ol=ol, data_folder=data_folder)

def read_bunch_id(run_nr, sub_folder="hummingbird", ol=1, data_folder=data_folder_default):
    return read_data(name="/entry_1/event/bunch_id", run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder)

def read_gmd(run_nr, sub_folder="hummingbird", ol=1, data_folder=data_folder_default):
    return read_data(name="/entry_1/FEL/gmd", run_nr=run_nr, sub_folder=sub_folder, ol=ol, data_folder=data_folder)

def _calc_rate(mode, run_nr, threshold=None, data_folder=data_folder_default):
    if mode == "hit":
        read_scores = read_hitscores
        threshold_name = 'hitscoreThreshold'
    elif mode == "mul":
        read_scores = read_mulscores
        threshold_name = 'multiscoreThreshold'
    else:
        print "ERROR: illegal mode %s" % mode
        return
    scores = read_scores(run_nr=run_nr, ol=1, data_folder=data_folder)
    if scores is None:
        return None
    else:
        n_frames = len(scores)
        if threshold is None:
            T = params.read_params(params_fn, run_nr)[threshold_name]
        else:
            T = threshold
        n_hits = (scores > T).sum()
        return (float(n_hits)/float(n_frames))

def calc_hitrate(run_nr, threshold=None, ol=1, data_folder=data_folder_default):
    return _calc_rate(mode="hit", run_nr=run_nr, threshold=threshold, data_folder=data_folder)

def calc_mulrate(run_nr, threshold=None, ol=1, data_folder=data_folder_default):
    return _calc_rate(mode="mul", run_nr=run_nr, threshold=threshold, data_folder=data_folder)
