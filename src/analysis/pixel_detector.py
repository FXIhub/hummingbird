from numpy import sum, mean, min, max, std

def printStatistics(detectors):
    for k,r in detectors.iteritems():
        v = r.data
        print "%s: sum=%g mean=%g min=%g max=%g std=%g" % (k, sum(v), mean(v),
                                                           min(v), max(v), std(v))
                                                              
    
    
