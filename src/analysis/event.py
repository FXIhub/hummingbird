import collections
import datetime
import ipc
import numpy as np

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
        print 'Processing Rate', proc_rate[()]

        
def printKeys(evt):
    """prints available keys of Hummingbird event"""
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
        
