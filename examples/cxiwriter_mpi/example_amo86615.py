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
user = os.environ["USER"]
run_nr = cmdline_args.lcls_run_number 
N_frames = -1 if cmdline_args.lcls_number_of_frames is None else cmdline_args.lcls_number_of_frames
experiment_dir = '/scratch/fhgfs/LCLS/amo/amo86615'
state = {
    'Facility': 'LCLS',
    'LCLS': {'DataSource': 'exp=amo86615:dir=%s/xtc/' % (experiment_dir),
             'PsanaConf': '%s/psana.cfg' % this_dir,
             'CalibDir': '%s/calib' % experiment_dir,
    },
    'indexing': True,
}

# COUNTERS
i_frame = 0
i_hit   = 0

# PNCCD
# -----
back_type = "image"
back_key  = "pnccdBack[%s]" % back_type

# OPEN FILE FOR WRITING
W = utils.cxiwriter.CXIWriter("/scratch/fhgfs/hantke/r%04i.cxi" % (run_nr), chunksize=100)

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
    #print "[rank=%03i] %05i/%05i - %.1f %% hits - %s (score=%i)" % (rank, i_frame*size+1, N_frames, hitratio, "HIT" if hit else "miss", hitscore)

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
