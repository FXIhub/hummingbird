import time
import random
from event_translator import EventTranslator
from record import addRecord, Record
from . import ureg
import numpy

class DummyTranslator(object):    
    def __init__(self, state):
        pass

    def nextEvent(self):
        evt = {}
        evt['pr1'] = random.random()
        evt['pr2'] = random.random()
        # CCD data 128px wide, 256px tall
        evt['ccd'] = numpy.random.rand(256,128)
        return EventTranslator(evt,self)
        
    def eventKeys(self, evt):
        return ['pulseEnergies']
        
    def eventNativeKeys(self, evt):
        return evt.keys()
        
    def translate(self, evt, key):
        values = {}
        if(key == 'pulseEnergies'):            
            addRecord(values, 'pulseEnergy1', evt['pr1'], ureg.mJ)
            addRecord(values, 'pulseEnergy2', evt['pr2'], ureg.mJ)
        elif(key == 'photonPixelDetectors'):            
            addRecord(values, 'CCD', evt['ccd'], ureg.ADU)
        else:
            raise RuntimeError('%s not found in event' % (key))
        return values

    def id(self, evt):
        return float(time.time())
