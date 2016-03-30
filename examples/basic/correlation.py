# Import analysis/plotting/simulation modules
import analysis.event
import analysis.hitfinding
import analysis.beamline
import plotting.line
import plotting.image
import plotting.correlation
import simulation.base

# Simulate diffraction data  
sim = simulation.base.Simulation()
sim.hitrate = 0.5
sim.sigma = 1

# Specify the facility
state = {}
state['Facility'] = 'Dummy'

# Create a dummy facility
state['Dummy'] = {
    # The event repetition rate of the dummy facility [Hz]
    'Repetition Rate' : 10,
    # Specify simulation
    'Simulation': sim,
    # Dictionary of data sources
    'Data Sources': {
        # Data from a virtual diffraction detector
        'CCD': {
            # Fetch diffraction data from the simulation
            'data': sim.get_pattern,
            'unit': 'ADU',
            'type': 'photonPixelDetectors'
        },
        # Data from a virutal pulse energy detector
        'pulseEnergy': {
            # Fetch pulse energy valus from the simulation
            'data': sim.get_pulse_energy,
            'unit': 'J',
            'type': 'pulseEnergies'
        },
        # Data from a virutal injector motor
        'injectorX': {
            # Fetch injector motor valus (x) from the simulation
            'data': sim.get_injector_x,
            'unit': 'm',
            'type': 'parameters'
        },
        # Data from a virutal injector motor
        'injectorY': {
            # Fetch injector motor valus (y) from the simulation
            'data': sim.get_injector_y,
            'unit': 'm',
            'type': 'parameters'
        }
    }
}

# Configuration for hitrate meanmap plot
hitmapParams = {
    'xmin':0,
    'xmax':1e-6,
    'ymin':0,
    'ymax':1e-6,
    'xbins':10,
    'ybins':10
}

# This function is called for every single event
# following the given recipy of analysis
def onEvent(evt):
    
    # Processing rate [Hz]
    analysis.event.printProcessingRate()

    # Simple hit finding (counting the number of lit pixels)
    analysis.hitfinding.countLitPixels(evt, evt["photonPixelDetectors"]["CCD"],
                                       aduThreshold=10, hitscoreThreshold=100)

    #analysis.beamline.averagePulseEnergy(evt, evt["pulseEnergies"])
    
    # Extract boolean (hit or miss)
    hit = evt["analysis"]["litpixel: isHit"].data
    
    # Compute the hitrate
    analysis.hitfinding.hitrate(evt, hit, history=1000)

    # Plot history of pulse energy
    plotting.line.plotHistory(evt['pulseEnergies']['pulseEnergy'])
        
    # Plot scatter of pulse energy vs. hitscore
    plotting.correlation.plotScatter(evt['pulseEnergies']['pulseEnergy'],
                                     evt["analysis"]["litpixel: hitscore"],
                                     xlabel='Pulse energy [J]', ylabel='Hitscore')

    # Plot heat map of hitrate as function of injector position
    plotting.correlation.plotMeanMap(evt["parameters"]['injectorX'], evt["parameters"]['injectorY'],
                                     evt["analysis"]["hitrate"].data, name='hitrateMeanMap', **hitmapParams)
