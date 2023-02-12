import time

from hummingbird import analysis, plotting

state = {}
state['Facility'] = 'SwissFEL'
state['SwissFEL/DataGlob'] = '/sf/maloja/data/p19750/raw/run0149/data/acq*JF15T08V01.h5'
adu_photon = 1
threshold=2500

def onEvent(evt):

    # Processing rate
    #analysis.event.printProcessingRate()
    # Hitfinding
    analysis.hitfinding.countLitPixels(evt, evt['photonPixelDetectors']['Jungfrau'], 
                                       aduThreshold=adu_photon, hitscoreThreshold=threshold)
    isHit = evt['analysis']['litpixel: isHit'].data
    # Plot hitscore (to monitor hitfinder -> hitscoreThreshold)
    plotting.line.plotHistory(evt['analysis']['litpixel: hitscore'], hline=threshold)
    plotting.line.plotHistory(evt['analysis']['litpixel: isHit'], history=10000)

    # Plot back detector image for hits only
    if bool(evt['analysis']['litpixel: isHit'].data):
        plotting.image.plotImage(evt['photonPixelDetectors']['Jungfrau'],log=True,
                                 name='Hits')

    return
