import os,sys
import numpy
import time
import logging

import analysis.event
import analysis.beamline
import analysis.pixel_detector
import analysis.hitfinding

import utils.cxiwriter

import ipc   
import ipc.mpi

this_dir = os.path.dirname(os.path.realpath(__file__))

# LOGGING
utils.cxiwriter.logger.setLevel("INFO")

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

# OPEN FILE FOR WRITING
outdir = "."
#user = os.environ["USER"]
#outdir = "/scratch/fhgfs/%s" % user
W = utils.cxiwriter.CXIWriter("%s/r%04i.cxi" % (outdir,run_nr), chunksize=100)

t_start = time.time()
    
def onEvent(evt):

    global i_frame
    global i_hit
    
    # Processin rate [Hz]
    analysis.event.printProcessingRate()

    # Simple hitfinding (Count Nr. of lit pixels)
    aduThreshold = 30*16
    hitscoreThreshold = 700
    analysis.hitfinding.countLitPixels(evt, evt[back_type][back_key], aduThreshold=aduThreshold, hitscoreThreshold=hitscoreThreshold)
   
    hit = evt["analysis"]["isHit"].data
    hitscore = evt["analysis"]["hitscore"].data

    hitratio = 100.*i_hit/float(i_frame+1)

    index_str = "%06i" % (i_frame*ipc.mpi.nr_workers()+1)
    if N_frames > 0:
        index_str += "/%06i" % N_frames
    print "(%03i)\t%s\t%.1f %% hits\t%s\tscore=%i" % (ipc.mpi.slave_rank(), index_str, hitratio, "HIT" if hit else "", hitscore)

    if hit:

        output = {}
        output["pnccd_back"] = {}
        output["pnccd_back"]["data"] = numpy.asarray(evt[back_type][back_key].data)

        W.write_slice(output)

        i_hit += 1

    i_frame += 1

def end_of_run():
    W.close()
    dt = time.time()-t_start
    N = (i_frame+1)
    r = N/dt
    print "Finished after %.1f seconds processing of %i frames (%.1f Hz / worker)" % (dt, N, r)
