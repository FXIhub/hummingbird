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
        evt['ccd1'] = numpy.random.rand(128,256)**3
        evt['tof'] = numpy.random.rand(256)
#        evt['tof'] = numpy.linspace(0,100,256)
        evt['ccd2'] = numpy.identity(4000)
        evt['apX'] = (numpy.random.random() + 2.0) * 2.0
        evt['apY'] = (numpy.random.random() + 2.0) * 2.0
        return EventTranslator(evt,self)
        
    def eventKeys(self, evt):
        return ['pulseEnergies', 'parameters']
        
    def eventNativeKeys(self, evt):
        return evt.keys()
        
    def translate(self, evt, key):
        values = {}
        if(key == 'pulseEnergies'):            
            addRecord(values, 'pulseEnergy1', evt['pr1'], ureg.mJ)
            addRecord(values, 'pulseEnergy2', evt['pr2'], ureg.mJ)
        elif(key == 'ionTOFs'):            
            addRecord(values, 'tof', evt['tof'], ureg.mJ)
        elif(key == 'photonPixelDetectors'):            
            addRecord(values, 'CCD', evt['ccd'], ureg.ADU)
            addRecord(values, 'CCD1', evt['ccd1'], ureg.ADU)
            addRecord(values, 'CCD2', evt['ccd2'], ureg.ADU)
        elif(key == 'parameters'):
            addRecord(values, 'apertureX', evt['apX'], ureg.mm)
            addRecord(values, 'apertureY', evt['apY'], ureg.mm)
        else:
            raise RuntimeError('%s not found in event' % (key))
        return values

    def id(self, evt):
        return float(time.time())
