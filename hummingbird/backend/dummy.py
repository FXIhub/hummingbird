# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Creates Hummingbird events for testing purposes"""
import random
import time

import numpy

from hummingbird import ipc
from . import EventTranslator, Worker, add_record, ureg


class DummyTranslator(object):
    """Creates Hummingbird events for testing purposes"""
    def __init__(self, state):
        self.library = 'dummy'
        self.state = state
        self.keys = set()
        self.keys.add('analysis')
        self._last_event_time = -1
        pass

    def next_event(self):
        """Generates and returns the next event"""
        evt = {}        
        
        # Check if we need to sleep
        if(self._last_event_time > 0):
            rep_rate = 1
            if('Dummy' in self.state and 'Repetition Rate' in self.state['Dummy']):
                rep_rate = self.state['Dummy']['Repetition Rate'] / float(ipc.mpi.nr_workers())
            target_t = self._last_event_time+1.0/rep_rate
            t = time.time()
            if(t < target_t):
                time.sleep(target_t - t)
        self._last_event_time = time.time()

        if('Dummy' not in self.state or 
           'Data Sources' not in self.state['Dummy']):
            # Generate a simple CCD as default
            evt['CCD'] = numpy.random.rand(128, 128)
            self.keys.add('photonPixelDetectors')
            return EventTranslator(evt, self)

        if('Dummy' in self.state and 'Simulation' in self.state['Dummy']):
            self.state['Dummy']['Simulation'].next_event()

        try:
            for ds in self.state['Dummy']['Data Sources']:
                evt[ds] = self.state['Dummy']['Data Sources'][ds]['data']()
                self.keys.add(self.state['Dummy']['Data Sources'][ds]['type'])

        except (IndexError, StopIteration) as e:
            logging.warning('End of Run.')
            if 'end_of_run' in dir(Worker.conf):
                Worker.conf.end_of_run()
            ipc.mpi.slave_done()
            return None

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
                add_record(values, key, 'CCD', evt['CCD'], ureg.ADU)
            if(values == {}):
                raise RuntimeError('%s not found in event' % (key))
            return values
        
        for ds in self.state['Dummy']['Data Sources']:
            if self.state['Dummy']['Data Sources'][ds]['type'] == key:
                # If unit is a string translate into PINT quantity
                u = self.state['Dummy']['Data Sources'][ds]['unit']
                if not isinstance(self.state['Dummy']['Data Sources'][ds]['unit'],ureg.Unit):
                    u = ureg.parse_units(u)
                add_record(values, key, ds, evt[ds], u)
        if(values == {} and not key == 'analysis'):
            raise RuntimeError('%s not found in event' % (key))
        return values

    def init_detectors(self, state):
        """
        A dummy placeholder for the initialization of detector objects, this is the place to switch between different reading modes (e.g. calibrated or raw)
        """
        pass
    
    def event_id(self, _):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return float(time.time())

    def event_id2(self, _):
        """Returns an alternative id, which is jsut a copy of the usual id here"""
        return event_id
