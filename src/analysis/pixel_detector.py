from numpy import sum, mean, min, max, std

def printStatistics(detectors):
    for k,r in detectors.iteritems():
        v = r.data
        print "%s (%s): sum=%g mean=%g min=%g max=%g std=%g" % (k, r.unit.units,
                                                                sum(v), mean(v),
                                                                min(v), max(v),
                                                                std(v))
                                                              
    
    
