# Import analysis/plotting modules
import analysis.event
import analysis.cxiwriter
import plotting.image
import numpy as np

# Set new random seed
np.random.seed()

import logging, sys
h = logging.StreamHandler(sys.stdout)
analysis.cxiwriter.logger.setLevel("INFO")
analysis.cxiwriter.logger.addHandler(h)

import ipc.mpi
comm = ipc.mpi.slaves_comm
is_slave = ipc.mpi.is_master() == False

i_frame = 0
N_frames = 2

# Specify the facility
state = {}
state['Facility'] = 'Dummy'

# Create a dummy facility
state['Dummy'] = {
    # The event repetition rate of the dummy facility [Hz]
    'Repetition Rate' : 10,
    # Dictionary of data sources
    'Data Sources': {
        # The name of the data source. 
        'CCD': {
            # A function that will generate the data for every event
            'data': lambda: np.random.rand(256,256),
            # The units to be used
            'unit': 'ADU',     
            # The name of the category for this data source.
            # All data sources are aggregated by type, which is the key
            # used when asking for them in the analysis code.
            'type': 'photonPixelDetectors'
        }        
    }
}

if is_slave:
    W = analysis.cxiwriter.CXIWriter("./test_dummy.cxi", chunksize=2, comm=comm)

# This function is called for every single event
# following the given recipy of analysis
def onEvent(evt):

    # Processin rate [Hz]
    analysis.event.printProcessingRate()

    if not is_slave:
        return
    
    global i_frame
    if i_frame >= N_frames:
        raise StopIteration
        return

    data = np.array( evt['photonPixelDetectors']['CCD'].data )

    out = {}
    out["entry_1"] = {}
    out["entry_1"]["data_1"] = {}
    out["entry_1"]["data_1"]["data"] = data

    W.write(out, i=comm.size*i_frame+comm.rank)

    i_frame += 1

def end_of_run():
    W.close()
    
