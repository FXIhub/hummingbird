# Import analysis/plotting modules
import analysis.event
import plotting.image
import numpy as np

# Set new random seed
np.random.seed()

# Specify the facility
state = {}
state['Facility'] = 'FLASH'
# Specify folder with frms6 data
state['FLASH/DataSource'] = '/tmp'

# This function is called for every single event
# following the given recipy of analysis
def onEvent(evt):

    # Processin rate [Hz]
    analysis.event.printProcessingRate()
    pass
    # Visualize detector image
    plotting.image.plotImage(evt['photonPixelDetectors']['pnCCD'])
