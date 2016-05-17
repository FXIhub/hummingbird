# Import analysis/plotting modules
import analysis.event
import plotting.image
import utils.cxiwriter
import numpy as np

# Set new random seed
np.random.seed()

# Logging for the CXI writer
#utils.cxiwriter.logger.setLevel("DEBUG")
utils.cxiwriter.logger.setLevel("INFO")

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

# Initialize CXIWriter (with MPI capabilities if started in MPI mode)
W = utils.cxiwriter.CXIWriter("./test_dummy.cxi", chunksize=100)

# Initialize counter/total frames
counter = 0
total_frames= 2

# This function is called for every single event
# following the given recipy of analysis
def onEvent(evt):

    # Processin rate [Hz]
    analysis.event.printProcessingRate()

    # Stop when counter reaches total number of frames
    global counter
    if counter >= total_frames:
        raise StopIteration
        return

    # Get detector image
    data = np.array(evt['photonPixelDetectors']['CCD'].data)

    # Write detector image into entry_1/data_1/data
    out = {}
    out["entry_1"] = {}
    out["entry_1"]["data_1"] = {}
    out["entry_1"]["data_1"]["data"] = data
    W.write_slice(out)

    # Increment counter
    counter += 1
    
def end_of_run():
    W.close()
    
