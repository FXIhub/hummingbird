import logging
import os
import sys
import time

import numpy

from hummingbird import analysis, ipc, utils

this_dir = os.path.dirname(os.path.realpath(__file__))

# LOGGING
utils.cxiwriter.logger.setLevel("WARNING")

# CMDLINE ARGS
from hummingbird import parse_cmdline_args

cmdline_args = parse_cmdline_args()

# DATA PARAMS
run_nr = cmdline_args.lcls_run_number 
N_frames = -1 if cmdline_args.lcls_number_of_frames is None else cmdline_args.lcls_number_of_frames
state = {
    'Facility': 'LCLS',
    'LCLS': {
        'DataSource': 'exp=amo86615',
        'PsanaConf': '%s/psana.cfg' % this_dir,
    },
    'indexing': True,
    'reduce_nr_event_readers' : 1 if ipc.mpi.nr_workers() > 1 else 0
}

davinci_experiment_dir = '/scratch/fhgfs/LCLS/amo/amo86615'
if os.path.isdir(davinci_experiment_dir):
    state['LCLS']['DataSource'] += ':dir=%s/xtc/' % (davinci_experiment_dir)
    state['LCLS']['CalibDir'] = '%s/calib' % davinci_experiment_dir
    

# COUNTERS
i_frame = 0
i_hit   = 0

# PNCCD
# -----
back_type = "image"
back_key  = "pnccdBack[%s]" % back_type

t_start = time.time()
W = None

def beginning_of_run():
    # OPEN FILE FOR WRITING
    global W
    w_dir = '/scratch/fhgfs/hantke/'
    W = utils.cxiwriter.CXIWriter(w_dir + "/r%04d.cxi" % run_nr, chunksize=10, compression=None)
    
def onEvent(evt):

    global i_frame
    global i_hit
    
    # Processin rate [Hz]
    analysis.event.printProcessingRate()

    # Simple hitfinding (Count Nr. of lit pixels)
    aduThreshold = 30*16
    hitscoreThreshold = 700
    analysis.hitfinding.countLitPixels(evt, evt[back_type][back_key], aduThreshold=aduThreshold, hitscoreThreshold=hitscoreThreshold)
    
    hit = evt["analysis"]["litpixel: isHit"].data
    hitscore = evt["analysis"]["litpixel: hitscore"].data

    hitratio = 100.*i_hit/float(i_frame+1)

    index_str = "%06i" % (i_frame*ipc.mpi.nr_workers()+1)
    if N_frames > 0:
        index_str += "/%06i" % N_frames
    #print "(%03i)\t%s\t%.1f %% hits\t%s\tscore=%i" % (ipc.mpi.worker_index(), index_str, hitratio, "HIT" if hit else "", hitscore)

    if hit:

        output = {}
        output["pnccd_back"] = {}
        output["pnccd_back"]["data"] = numpy.asarray(evt[back_type][back_key].data)

        W.write_slice(output)

        i_hit += 1

    i_frame += 1

def end_of_run():
    W.close()
    if ipc.mpi.is_event_reader():
        dt = time.time()-t_start
        rw = i_frame/dt
        rt = i_frame*ipc.mpi.nr_event_readers()/dt
        print "Finished after %.1f seconds processing of %i frames (%.1f Hz total, %.1f Hz / worker)" % (dt, i_frame, rt, rw)
