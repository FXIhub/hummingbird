# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import collections
import datetime

import numpy as np

from hummingbird import ipc
from hummingbird.backend import EventTranslator

#processingTimes = collections.deque([], 1000)
processingTimesDict = {}

def processingRate(pulses_per_event=1, label="Processing Rate"):
    """Returns the processing rate of events"""
    if label not in processingTimesDict:
        processingTimesDict[label] = collections.deque([], 100)
    processingTimes = processingTimesDict[label]
    for i in range(pulses_per_event):
        processingTimes.appendleft(datetime.datetime.now())
    if(len(processingTimes) < 2):
        return None
    dt = processingTimes[0] - processingTimes[-1]
    proc_rate = np.array((len(processingTimes)-1)/dt.total_seconds())
    # ipc.mpi.sum("processingRate", proc_rate)
    ipc.mpi.sum(label, proc_rate)
    proc_rate = proc_rate[()]
    return proc_rate

def printProcessingRate(pulses_per_event=1, label="Processing Rate"):
    """Prints processing rate to screen"""
    proc_rate = processingRate(pulses_per_event, label)
    if(ipc.mpi.is_main_event_reader() and proc_rate is not None):
        print('{} {:.2f} Hz'.format(label, proc_rate))
        return proc_rate
    return None

def printKeys(evt, group=None):
    """prints available keys of Hummingbird events"""
    if isinstance(evt, EventTranslator) and group is None:
        print("The event has the following keys: ", evt.keys())
    elif isinstance(evt, EventTranslator) and group:
        print("The dict of %s records has the following keys: " %(group), evt[group].keys())
    else:
        print(evt.keys())

def printNativeKeys(evt):
    """prints available keys of Native event"""
    print(evt.native_keys())
