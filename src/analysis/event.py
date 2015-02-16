
def printKeys(evt):
    print evt.keys()    

def printNativeKeys(evt):
    print evt.nativeKeys()

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
