# Import analysis/plotting modules
import analysis.event
import plotting.image
import plotting.line
import numpy as np
from backend import add_record

# Set new random seed
np.random.seed()

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

# This function is called for every single event
# following the given recipy of analysis
def onEvent(evt):

    # Processin rate [Hz]
    analysis.event.printProcessingRate()

    # Visualize detector image
    plotting.image.plotImage(evt['photonPixelDetectors']['CCD'], send_rate=10)


    # Visualize detector sum
    rowsum_rec = add_record(evt['analysis'], 'analysis', 'row_sum', np.sum(evt['photonPixelDetectors']['CCD'].data,axis=1))
    # Visualize row sum
    plotting.line.plotTrace(rowsum_rec, group='analysis')

    # Visualize detector sum
    sum_rec = add_record(evt['analysis'], 'analysis', 'sum', np.sum(evt['photonPixelDetectors']['CCD'].data))
    plotting.line.plotHistory(sum_rec, group='analysis')
