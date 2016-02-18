import analysis.event
import analysis.hitfinding
import analysis.pixel_detector
import plotting.line
import plotting.image
import utils.reader

state = {}
state['Facility'] = 'LCLS'
state['LCLS/DataSource'] = 'exp=amo15010:dir=/scratch/fhgfs/LCLS/amo/amo15010/xtc/:run=92'
state['indexing'] = True
state['index_offset'] = 2250

# Load dark frame from file
dark = utils.reader.H5Reader('dark_run73.h5', 'mean').dataset

# Parameters
adu_photon = 12
threshold  = 90000
hist_min  = 5
hist_max  = 35
hist_bins = 40

def onEvent(evt):

    # Processing rate
    analysis.event.printProcessingRate()

    try:
        evt['photonPixelDetectors']['pnccdBackfullFrame']
    except KeyError:
        return 

    # Dark calibration
    analysis.pixel_detector.subtractImage(evt, 'photonPixelDetectors', 'pnccdBackfullFrame', 
                                          dark, outkey='pnccdBackSubtracted')
    
    # Common mode correction
    analysis.pixel_detector.commonModePNCCD(evt, 'analysis', 'pnccdBackSubtracted', 
                                            outkey='pnccdBackCorrected')

    # Plot back detector histogram (to figure out ADU/photon -> aduThreshold)
    plotting.line.plotHistogram(evt['analysis']['pnccdBackCorrected'], 
                                hmin=hist_min, hmax=hist_max, bins=hist_bins, vline=adu_photon)

    # Hitfinding
    analysis.hitfinding.countLitPixels(evt, 'analysis', 'pnccdBackCorrected', 
                                       aduThreshold=adu_photon, hitscoreThreshold=threshold)

    # Plot hitscore (to monitor hitfinder -> hitscoreThreshold)
    plotting.line.plotHistory(evt['analysis']['hitscore'], hline=threshold)

    # Plot back detector image for hits only
    if bool(evt['analysis']['isHit'].data):
        plotting.image.plotImage(evt['analysis']['pnccdBackCorrected'], 
                                 log=True, name='pnccdBack - only hits')
