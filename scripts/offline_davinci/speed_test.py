#!/usr/bin/env python
import psana

import time

ds = psana.DataSource("exp=amo86615:run=195:dir=/scratch/fhgfs/LCLS/amo/amo86615/xtc/")
evts = ds.events()

evt = evts.next()
evt_key = evt.keys()[1]
evts = ds.events()

while True:
    t0 = time.time()
    evt = evts.next()
    #print evt.keys()
    #print evt.get("psana.PNCCD.FullFrameV1", "DetInfo(Camp.0:pnCCD.0)", "")
    D = evt.get(evt_key.type(), evt_key.src(), evt_key.key())
    print D.data() 
    t1 = time.time()
    f = 1./(t1-t0)
    print "Data rate %.3f Hz" % f
