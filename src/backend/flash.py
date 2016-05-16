# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Creates Hummingbird events for testing purposes"""
import time
import random
from backend.event_translator import EventTranslator
from backend.record import add_record
from backend import Worker
from . import ureg
import numpy
import ipc
import backend.convert_frms6 as convert
import glob

class FLASHTranslator(object):
    """Creates Hummingbird events for testing purposes"""
    def __init__(self, state):
        self.library = 'FLASH'
        self.state = state
        self.keys = set()
        self.keys.add('analysis')
        self._last_event_time = -1
        flist = glob.glob(state['FLASH/DataSource'] + '/*.frms6')
        self.reader = convert.Frms6_reader(flist[0])
        self.num = 0

    def next_event(self):
        """Generates and returns the next event"""
        evt = {}        
        
        # Check for new file
        # If yes, grab first designated image in that file
        #   and set num=0
        # If no grab num+1'th file in the same frame
        # Data type 'photonPixelDetectors', ds='pnCCD'
        '''
        # Check if we need to sleep
        if(self._last_event_time > 0):
            rep_rate = 1e9
            if('Dummy' in self.state and 'Repetition Rate' in self.state['Dummy']):
                rep_rate = self.state['Dummy']['Repetition Rate'] / float(ipc.mpi.nr_workers())
            target_t = self._last_event_time+1.0/rep_rate
            t = time.time()
            if(t < target_t):
                time.sleep(target_t - t)
        self._last_event_time = time.time()
        '''
        
        # Generate a simple CCD as default
        #evt['pnCCD'] = numpy.random.rand(128, 128)
        self.reader.parse_frames(start_num=ipc.mpi.slave_rank()+self.num*(ipc.mpi.size-1), num_frames=1)
        self.num += 1
        if len(self.reader.frames) > 0:
            evt['pnCCD'] = self.reader.frames[0]
            self.keys.add('photonPixelDetectors')
        '''
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

        '''
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
                add_record(values, key, 'pnCCD', evt['pnCCD'], ureg.ADU)
            if(values == {}):
                raise RuntimeError('%s not found in event' % (key))
            return values
        
        for ds in self.state['Dummy']['Data Sources']:
            if self.state['Dummy']['Data Sources'][ds]['type'] == key:
                # If unit is a string translate into PINT quantity
                u = self.state['Dummy']['Data Sources'][ds]['unit']
                if not isinstance(self.state['Dummy']['Data Sources'][ds]['unit'],ureg.Quantity):
                    u = ureg.parse_expression(u)
                add_record(values, key, ds, evt[ds], u)
        if(values == {} and not key == 'analysis'):
            raise RuntimeError('%s not found in event' % (key))
        return values

    def event_id(self, _):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return float(time.time())

    def event_id2(self, _):
        """Returns an alternative id, which is jsut a copy of the usual id here"""
        return event_id
