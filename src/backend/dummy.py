"""Creates Hummingbird events for testing purposes"""
import time
import random
from backend.event_translator import EventTranslator
from backend.record import add_record
from . import ureg
import numpy

class DummyTranslator(object):
    """Creates Hummingbird events for testing purposes"""
    def __init__(self, state):
        pass

    def next_event(self):
        """Generates and returns the next event"""
        evt = {}
        evt['pr1'] = random.random()
        evt['pr2'] = random.random()
        # CCD data 128px wide, 256px tall
        evt['ccd'] = numpy.zeros((256, 128))
        evt['ccd'][0:128,0:64] = 1
        evt['ccd'][0:128,64:] = 2
        evt['ccd'][128:,0:64] = 3
        
        evt['ccd1'] = numpy.random.rand(128, 256)**3
        evt['tof'] = numpy.random.rand(256)
#        evt['tof'] = numpy.linspace(0,100,256)
        evt['ccd2'] = numpy.identity(4000)
        evt['apX'] = (numpy.random.random() + 2.0) * 2.0
        evt['apY'] = (numpy.random.random() + 2.0) * 2.0
        return EventTranslator(evt, self)

    def event_keys(self, _):
        """Returns the translated keys available"""
        return ['pulseEnergies', 'parameters']

    def event_native_keys(self, evt):
        """Returns the native keys available"""
        return evt.keys()

    def translate(self, evt, key):
        """Returns a dict of Records that match a given Humminbird key"""
        values = {}
        if(key == 'pulseEnergies'):
            add_record(values, 'pulseEnergy1', evt['pr1'], ureg.mJ)
            add_record(values, 'pulseEnergy2', evt['pr2'], ureg.mJ)
        elif(key == 'ionTOFs'):
            add_record(values, 'tof', evt['tof'], ureg.mJ)
        elif(key == 'photonPixelDetectors'):
            add_record(values, 'CCD', evt['ccd'], ureg.ADU)
            add_record(values, 'CCD1', evt['ccd1'], ureg.ADU)
            add_record(values, 'CCD2', evt['ccd2'], ureg.ADU)
        elif(key == 'parameters'):
            add_record(values, 'apertureX', evt['apX'], ureg.mm)
            add_record(values, 'apertureY', evt['apY'], ureg.mm)
        else:
            raise RuntimeError('%s not found in event' % (key))
        return values

    def event_id(self, _):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return float(time.time())
