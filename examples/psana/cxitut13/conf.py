import analysis.event
import analysis.beamline
import ipc

state = {
    'Facility': 'LCLS',
    'LCLS/DataSource': ipc.mpi.get_source(['exp=XCS/xcstut13:run=15', 'shmem2'])
}

def onEvent(evt):
    analysis.event.printKeys(evt)
    analysis.event.printNativeKeys(evt)
    analysis.beamline.printPulseEnergy(evt['pulseEnergies'])
    analysis.beamline.printPhotonEnergy(evt['photonEnergies'])
    analysis.event.printProcessingRate()


