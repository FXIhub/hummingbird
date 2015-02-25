import time
import analysis.event
import analysis.beamline
import analysis.pixel_detector

state = {
    'Facility': 'LCLS',
    'LCLS/DataSource':'exp=amoc6914:run=215:xtc'   
}

def onEvent(evt):
    analysis.beamline.plotPulseEnergy(evt['pulseEnergies'])
#    analysis.beamline.printPulseEnergy(evt['pulseEnergies'])
#    analysis.beamline.printPhotonEnergy(evt['photonEnergies'])
#    print "EPICS photon energy = %g eV" %(evt['parameters']['SIOC:SYS0:ML00:AO541'].data)
#    analysis.pixel_detector.printStatistics(evt['photonPixelDetectors'])
#    analysis.pixel_detector.printStatistics(evt['ionTOFs'])
    analysis.event.printID(evt['eventID'])
    analysis.event.plotFiducial(evt['eventID'])
    analysis.event.printProcessingRate(evt)
    time.sleep(1)
