import analysis.event
import analysis.beamline
import analysis.pixel_detector
import plotting.image
import ipc
import numpy
import numpy.random
from backend import add_record

numpy.random.seed()

state = {
    'Facility': 'HDF5',

    'Dummy': {
        # The event repetition rate of the facility 
        'Repetition Rate' : 5,
        # Dictionary of data sources
        'Data Sources': {
            # The name of the data source. This is the key under which it will be found
            # when iterating over members of its type.
            # It's also the native key that will be used
            'CCD': {
                # A function that will generate the data for every event
                'data': lambda: numpy.random.rand(256,256),
                # The units to be used
                'unit': 'ADU',     
                # The name of the category for this data source.
                # All data sources are aggregated by type, which is the key
                # used when asking for them in the analysis code.
                'type': 'photonPixelDetectors'
            }
        }        
    }
}



def onEvent(evt):

    # 
    analysis.event.printProcessingRate()


    analysis.pixel_detector.radial(evt, 'photonPixelDetectors', 'CCD')
    
    ipc.broadcast.init_data('CCD', xmin=10,ymin=10)
    for k,v in evt['photonPixelDetectors'].iteritems():
        plotting.image.plotImage(v)

    
