import analysis.event
import analysis.hitfinding
import ipc
import random
from backend import ureg
import numpy

state = {
    'Facility': 'dummy',
    'Dummy': {
        'Repetition Rate' : 1,
        'Data Sources': {
            'CCD': {
                'data': lambda: numpy.random.rand(256,128),
                'unit': ureg.ADU,     
                'type': 'photonPixelDetectors'
            },
            'pulseEnergy1': {
                'data': lambda: random.random(),
                'unit': ureg.mJ,
                'type': 'pulseEnergies'
            }
        }        
    }
}

# PARAMETERS
# ----------
# hitfinding
# ----------
# threshold is expectation value of numpy.random.rand()
aduThreshold = 0.5
# lit pixels are half of total number of pixels
hitscoreMinCount = 16384
# -----------
# correlation
# -----------
correlationMinX = 0.0
correlationMaxX = 1.0
correlationNbinsX = 10
correlationMinY = 16000
correlationMaxY = 16768
correlationNbinsY = 10


def onEvent(evt):
    analysis.event.printKeys(evt)
    print evt['photonPixelDetectors'].keys()
    ipc.new_data('CCD', evt['photonPixelDetectors']['CCD'].data)
    ipc.new_data('PulseEnergy1', evt['pulseEnergies']['pulseEnergy1'].data)
    hit, hitscore = analysis.hitfinding.countLitPixels(evt['photonPixelDetectors']['CCD'], aduThreshold, hitscoreMinCount)
    ipc.new_data("Hitscore", hitscore.data)
    hitCounter = numpy.array(analysis.hitfinding.counting(hit))
    print "%d lit pixels (%d accumulated hits)" % (hitscore.data, hitCounter.sum())
    # correlation normalizes by the mean of the accumulated x/y-arrays, if x or y are zero for the first events you may receive:
    #    RuntimeWarning: invalid value encountered in double_scalars
    correlation = numpy.array(analysis.hitfinding.correlate(evt['pulseEnergies']['pulseEnergy1'].data, hitscore.data))
    ipc.new_data('Correlation', correlation[-1])
    # correlate2D takes arguments x, y in 2D image, and optional arguments for xMin, xMax, xNbins, yMin, yMax, yNbins
    # correlationMinX, correlationMaxX, and correlationNbinsX are equal to default values of xMin, xMax, and xNbins
    #    => only need to set yMin, yMax, yNbins
    correlation2D = analysis.hitfinding.correlate2D(evt['pulseEnergies']['pulseEnergy1'].data, hitscore.data, yMin=correlationMinY, yMax=correlationMaxY, yNbins=correlationNbinsY)
    ipc.new_data("Correlation2D", correlation2D, xlabel='pulseEnergy1 bins', ylabel='Lit pixel bins')
    analysis.event.printProcessingRate()
