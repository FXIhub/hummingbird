import analysis.event
import analysis.beamline
import analysis.pixel_detector
#import analysis.background
import ipc   

import os,sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import cxiwriter

run = int(os.environ["HUMMINGBIRD_RUN"])

outdir = "/reg/d/psdm/cxi/cxi86715/scratch/hantke"

filename = "%s/camdata_%04i.cxi" % (outdir,run)
W = cxiwriter.CXIWriter(filename)

state = {
    'Facility'       : 'LCLS',
    'LCLS/DataSource': 'exp=cxi86715:run=%i' % run,
    'LCLS/PsanaConf' : 'psana.cfg',
}

p1_type = "parameters"
p1_key = "CXI:SDS:REG:01:PRESS"
p2_type = "parameters"
p2_key = "CXI:SDS:REG:02:PRESS"
cam_type = "camimage"
cam_key  = "Sc2Questar[camimage]"
types = [p1_type, p2_type, cam_type]
keys  = [p1_key, p2_key, cam_key]

i = -1

def onEvent(evt):
    analysis.event.printProcessingRate()
    try:
        evt["camimage"]["Sc2Questar[camimage]"]
        cam = True
    except:
        #print "Camdata is missing for this event"
        cam = False
    if cam:
        global i
        i += 1
        if (i % 10 != 0): return    
        #print "Camdata exists for this event"
        D = {}
        for t,k in zip(types, keys):
            data = evt[t][k].data
            D["%s_%s" % (t,k)] = data
        D["timestamp"] = evt["eventID"]["Timestamp"].timestamp2
        D["fiducial"]  = evt["eventID"]["Timestamp"].fiducials
        W.write(D)  

def close():
    W.close()
        
