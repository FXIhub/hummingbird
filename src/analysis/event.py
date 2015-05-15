import collections
import datetime
import ipc
import numpy as np

from backend import Record
from backend import EventTranslator

processingTimes = collections.deque([], 100)
def printProcessingRate():
    """Prints processing rate to screen"""
    processingTimes.appendleft(datetime.datetime.now())
    if(len(processingTimes) < 2):
        return
    dt = processingTimes[0] - processingTimes[-1]
    proc_rate = np.array((len(processingTimes)-1)/dt.total_seconds())
    
    ipc.mpi.sum(proc_rate)
    if(ipc.mpi.is_main_worker()):
        print 'Processing Rate %.2f Hz' %proc_rate[()]

        
def printKeys(evt, _type=None):
    """prints available keys of Hummingbird event"""
    if isinstance(evt, EventTranslator) and _type is None:
        print "The event has the following keys: ", evt.keys()
    elif isinstance(evt, EventTranslator) and _type:
        print "The event dict ''%s'' has the following keys: " %(_type), evt[_type].keys()
    else:
        print evt.keys()    

def printNativeKeys(evt):
    """prints available keys of Native event"""
    print evt.native_keys()

#BD: deprecated??
def printID(eventID):
    for k,v in eventID.iteritems():
        print "%s = %s" %(k, v.data)
        try:
            print "datetime64 = %s" %(v.datetime64)
        except AttributeError:
            pass
        try:
            print "fiducials = %s" %(v.fiducials)
        except AttributeError:
            pass
        try:
            print "run = %s" %(v.run)
        except AttributeError:
            pass
        try:
            print "ticks = %s" %(v.ticks)
        except AttributeError:
            pass
        try:
            print "vector = %s" %(v.vector)
        except AttributeError:
            pass
        
