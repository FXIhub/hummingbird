import analysis.event
import analysis.beamline
import analysis.pixel_detector
   
state = {
    'Facility': 'LCLS',
    'LCLS/DataSource': '/data/rawdata/cxic9714/xtc/e419-r0203-s00-c00.xtc'
}
   
def onEvent(evt):
    analysis.beamline.printPulseEnergy(evt['pulseEnergies'])
    analysis.beamline.printPhotonEnergy(evt['photonEnergies'])
    print "EPICS photon energy = %g eV" %(evt['parameters']['SIOC:SYS0:ML00:AO541'].data)
    analysis.pixel_detector.printStatistics(evt['photonPixelDetectors'])
    analysis.pixel_detector.printStatistics(evt['ionTOFs'])
    analysis.event.printID(evt['eventID'])
    analysis.event.printProcessingRate()
