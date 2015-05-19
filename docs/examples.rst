More examples
=============

Simulation
----------
For most of the following examples, simulated data provided through `Condor <http://lmb.icm.uu.se/condor/simulation>`_ is used. In order to run these examples on real data, the only thing to change is the ``state[Facility]`` variable and maybe some more lightsource specific configurations. See the basic example in :doc:`Configuration <configuration>`.

The speciman used for the simulation is a icosahedron-shaped virus with a diameter of 60 nm with reasonable conditions for experiments inside the 100nm chamber of the CXI beamline. The full Condor configuration file is located in ``examples/simulation/virus.conf``.

Now, lets have a look at the configuration file, located in ``examples/simulation/conf.py``. First, we are importing the ``simulation`` and the ``analysis.event`` module:

::

   import simulation.simple
   import analysis.event

We load the `Condor <http://lmb.icm.uu.se/condor/simulation>`_ configuration file and specify a hitrate of 10%:

::

   sim = simulation.simple.Simulation("examples/simulation/virus.conf")
   sim.hitrate = 0.1

In the ``state`` variable, it is necessary to provide the simulation ``sim`` and specify the datasets to be extracted:

::

   state = {
       'Facility': 'Dummy',

       'Dummy': {
           'Repetition Rate' : 1,
           'Simulation': sim,
           'Data Sources': {
	       'CCD': {
	           'data': sim.get_pattern,
		   'unit': 'ph',
		   'type': 'photonPixelDetectors'
	       },
               'pulseEnergy': {
	           'data': sim.get_pulse_energy,
                   'unit': 'J',
                   'type': 'pulseEnergies'
	       },
               'inj_x': {
                   'data': sim.get_position_x,
                   'unit': 'm',
                   'type': 'parameters'
		               },
	       'inj_y': {
	           'data': sim.get_position_y,
                   'unit': 'm',
                   'type': 'parameters'
	       },
               'inj_z': {
                   'data': sim.get_position_z,
                    'unit': 'm',
                    'type': 'parameters'
	       }
           }        
       }
   }

Inside the ``onEvent`` function it is possible to apply analsyis algorithms to the simulated datasets and send plots to the frontend, for now some extracted information is printed:

::

   def onEvent(evt):
       analysis.event.printProcessingRate()
       analysis.event.printKeys(evt)
       analysis.event.printKeys(evt, "parameters")

Here is the output of this small simulation example:

::

   $ ./hummingbird.py -b examples/simulation/conf.py
   Starting backend...
   1/1 (1 particle)
   The event has the following keys:  ['pulseEnergies', 'photonPixelDetectors', 'parameters']
   The event dict ''parameters'' has the following keys:  ['inj_y', 'inj_x', 'inj_z']
   1/1 (1 particle)
   Processing Rate 0.86 Hz
   The event has the following keys:  ['pulseEnergies', 'photonPixelDetectors', 'parameters']
   The event dict ''parameters'' has the following keys:  ['inj_y', 'inj_x', 'inj_z']


Detector characteristics
------------------------
In this example it is shown how detector-specific characteristics (histograms, averages, ... ) can be visualized. This is very important for a robust tuning of more advanced analysis (hitfinding, sizing, ...). The configuration file ``examples/detector/conf.py`` is based on the simulation example, but some more modulues need to be imported:

::

   import simulation.simple
   import analysis.event
   import analysis.pixel_detector
   import plotting.line
   import plotting.image
   
In the ``onEvent`` some more lines are added. First, some detector statistics are printed

::

   # Detector statistics
   analysis.pixel_detector.printStatistics(evt["photonPixelDetectors"])


giving the following output:

::

   $ ./hummingbird -b examples/detector/conf.py
   Processing Rate 0.65 Hz
   The event has the following keys:  ['pulseEnergies', 'photonPixelDetectors', 'parameters']
   The event dict ''parameters'' has the following keys:  ['inj_y', 'inj_x', 'inj_z']
   CCD (count): sum=-79.434 mean=-0.000463453 min=-0.412553 max=0.506501 std=0.100154
   1/1 (1 particle)
   Processing Rate 0.65 Hz
   The event has the following keys:  ['pulseEnergies', 'photonPixelDetectors', 'parameters']
   The event dict ''parameters'' has the following keys:  ['inj_y', 'inj_x', 'inj_z']
   CCD (count): sum=-46.7338 mean=-0.000272666 min=-0.456227 max=0.47392 std=0.100047
   1/1 (1 particle)

Then, the total nr. of photons is counted on the CCD pixel detector and the result is being sent to the frontend, so that it is possible to follow the history of the total photon count.

::
   
   # Count Nr. of Photons
   analysis.pixel_detector.totalNrPhotons(evt, evt["photonPixelDetectors"]["CCD"])
   plotting.line.plotHistory(evt["nrPhotons - CCD"], label='Nr of photons / frame', history=50)

On the frontend, this history can be displayed by opening a Line plot and subscribing to the data source ``History(nrPhotons - CCD)``:

.. image:: images/examples/detector/nrphotons.jpg

Inside the ``View`` -> ``Plot settings`` dialog there is an option to display a histogram of the current buffer instead of the updating history:

.. image:: images/examples/detector/nrphotons_hist.jpg
   :align: center
	   
The next useful detector feature to look is a frame histogram of the entrie CCD:

::
   
   # Detector histogram
   plotting.line.plotHistogram(evt["photonPixelDetectors"]["CCD"], **histogramCCD)

The parameters for the histogram plot (as for any other plot) can be given as keyword arguments or defined outside the ``onEvent`` function as a dictionary which is then passed as a whole to the plotting function:

::

   histogramCCD = {
       'hmin': -1,
       'hmax': 19,
       'bins': 100,
       'label': "Nr of photons",
       'history': 50}

   def onEvent(evt):

       ...
       plotting.line.plotHistory(..., history=50)
       plotting.line.plotHistogram(..., **histogramCCD)

Subscribing to the detector histogram ``Hist(CCD)`` in a Line plot, the visual output looks like this:

.. image:: images/examples/detector/histogram_hit.jpg
   :align: center

Subscribing to the same data source in an Image Plot, the output is a history of histograms looking like this:

.. image:: images/examples/detector/histogram_history.jpg
   :align: center
	   
Finally, it is possible to just send every detector frame (or a subset of it based on e.g. hitfinding) as an image

::
   
    # Detector images
    plotting.image.plotImage(evt["photonPixelDetectors"]["CCD"])

and display it on the frontend. Instead displaying only the latest image, it is possible to toggle the visualization of the trend (mean, min, max, std) inside the ``View`` -> ``Plot settings`` dialog:

.. image:: images/examples/detector/buffer.jpg
   :align: center

The latest image of the buffer (50 images) is displayed on the left, the per-pixel maximum of the buffer in the middle and the per-pixel mean on the right.	   
	   

Hitfinding
----------


Sizing
------


Correlations
------------

