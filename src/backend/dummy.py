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
        self.state = state
        self.keys = set()
        self._last_event_time = -1
        pass

    def next_event(self):
        """Generates and returns the next event"""
        evt = {}        

        # Check if we need to sleep
        if(self._last_event_time > 0):
            rep_rate = 1
            if('Dummy' in self.state and 'Repetition Rate' in self.state['Dummy']):
                rep_rate = self.state['Dummy']['Repetition Rate']
            target_t = self._last_event_time+1.0/rep_rate
            t = time.time()
            if(t < target_t):
                time.sleep(target_t - t)
        self._last_event_time = time.time()

        if('Dummy' not in self.state or 
           'Data Sources' not in self.state['Dummy']):
            # Generate a simple CCD as default
            evt['CCD'] = numpy.random.rand((128, 128))
            self.keys.add('photonPixelDetectors')
            return EventTranslator(evt, self)
            
        for ds in self.state['Dummy']['Data Sources']:
            evt[ds] = self.state['Dummy']['Data Sources'][ds]['data']()
            self.keys.add(self.state['Dummy']['Data Sources'][ds]['type'])
        
        return EventTranslator(evt, self)

    def event_keys(self, _):
        """Returns the translated keys available"""
        return list(self.keys)

    def event_native_keys(self, evt):
        """Returns the native keys available"""
        return evt.keys()

    def translate(self, evt, key):
        """Returns a dict of Records that match a given Humminbird key"""
        values = {}
        if('Dummy' not in self.state or 
           'Data Sources' not in self.state['Dummy']):
            if(key == 'photonPixelDetectors'):
                # Translate default CCD as default
                add_record(values, 'CCD', evt['CCD'], ureg.ADU)
            if(values == {}):
                raise RuntimeError('%s not found in event' % (key))
            return values
        
        for ds in self.state['Dummy']['Data Sources']:
            if self.state['Dummy']['Data Sources'][ds]['type'] == key:
                add_record(values, ds, evt[ds], self.state['Dummy']['Data Sources'][ds]['unit'])
        if(values == {}):
            raise RuntimeError('%s not found in event' % (key))
        return values

    def event_id(self, _):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return float(time.time())
