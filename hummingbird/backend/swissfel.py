import glob
import os
import time

import h5py
import numpy as np

import sfdata

from hummingbird import ipc
from . import EventTranslator, Worker, add_record, ureg


class SwissFELTranslator(object):
    """Translate between SwissFEL h5 files and Hummingbird events"""
    def __init__(self, state):
        self.library = 'SwissFEL'
        self.state = state
        self.keys = set()
        self.keys.add('analysis')
        self.keys.add('DAQ')
        self.timestamps = None
        self.current_fname = None
        self._last_event_time = -1
        self.data = None

        if 'do_offline' in state:
            self.do_offline = state['do_offline']
        else:
            self.do_offline = False

        

    def next_event(self):
        """Generates and returns the next event"""
        evt = {}

        while(self.data is None):
            self.data = self.new_file_check()
            time.sleep(2)

        self.keys.add('photonPixelDetectors')
        # To workaround a bug in jungfrau_utils use the silly slice syntax
        evt['Jungfrau'] = np.array(self.data['JF15T08V01'][self.num:(self.num+1)])[0]
        self.num += ipc.mpi.nr_workers()
        if self.num >= self.total:
            self.data.close()
            self.data = None
        return EventTranslator(evt, self)

    def new_file_check(self, force=False):
        flist = glob.glob(self.state['SwissFEL/DataGlob'])
        flist.sort()
        if self.do_offline:
            pass
        else:
            i = -1
            while(True):
                latest_fname = sorted(flist, key=os.path.getmtime)[i]
                # Check if we can open the last file otherwise take the file before
                try:
                    h5py.File(latest_fname)
                    break
                except:
                    i -= 1
                    
            file_size = os.path.getsize(latest_fname)
            if ipc.mpi.worker_index() == 0:
                print('Glob latest: %s' % (latest_fname))
                
        
        if latest_fname != self.current_fname:
            self.current_size = file_size
            if file_size < 1024:
                return False
            if ipc.mpi.worker_index() == 0:
                print('Rank found new file', latest_fname, 'size =', self.current_size)
          
            self.data = sfdata.SFDataFiles(latest_fname)
            self.num = ipc.mpi.worker_index()
            self.total = self.data['JF15T08V01'].shape[0]
            self.current_fname = latest_fname
            return self.data
        return None

    def event_id(self, evt):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return time.time()

    def event_id2(self, _):
        """Returns an alternative id, which is jsut a copy of the usual id here"""
        return self.event_id()

    def event_keys(self, _):
        """Returns the translated keys available"""
        return list(self.keys)

    def event_native_keys(self, evt):
        """Returns the native keys available"""
        return evt.keys()

    def translate(self, evt, key):
        """Returns a dict of Records that match a given Humminbird key"""
        values = {}
        if key == 'photonPixelDetectors':
            # Translate pnCCD
            add_record(values, key, 'Jungfrau', evt['Jungfrau'], ureg.ADU)
        elif not key == 'analysis':
            raise RuntimeError('%s not found in event' % key)
        
        return values
