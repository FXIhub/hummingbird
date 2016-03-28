# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
import collections
import datetime
import ipc
import numpy as np
from backend import EventTranslator

processingTimes = collections.deque([], 100)
def printProcessingRate():
    """Prints processing rate to screen"""
    processingTimes.appendleft(datetime.datetime.now())
    if(len(processingTimes) < 2):
        return
    dt = processingTimes[0] - processingTimes[-1]
    proc_inverse = np.array(1.0 / ((len(processingTimes)-1)/dt.total_seconds()))
    ipc.mpi.sum("processingRate", proc_inverse)
    # Square of number of workers due to harmonic mean and total rate over everyone
    proc_rate = ipc.mpi.nr_workers()**2 / proc_inverse[()]
    if(ipc.mpi.is_main_worker()):
        print 'Processing Rate %.2f Hz' % proc_rate

def printKeys(evt, group=None):
    """prints available keys of Hummingbird events"""
    if isinstance(evt, EventTranslator) and group is None:
        print "The event has the following keys: ", evt.keys()
    elif isinstance(evt, EventTranslator) and group:
        print "The dict of %s records has the following keys: " %(group), evt[group].keys()
    else:
        print evt.keys()    

def printNativeKeys(evt):
    """prints available keys of Native event"""
    print evt.native_keys()
