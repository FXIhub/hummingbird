More examples
=============

Simulation
----------
For most of our examples, we are using simulated data which is provided through `Condor <http://lmb.icm.uu.se/condor/simulation>`_. If you want to know how to run these examples on real data, checkout the basic example in :doc:`Configuration <configuration>`.

We are simulating a icosahedron-shaped virus with a diameter of 60 nm under reasonable experimental conditions at the CXI beamline. The full **Condor** configuration file is located in ``examples/simulation/virus.conf``.

Now, lets have a look at the **Hummingbird** configuration file (located in ``examples/simulation/conf.py``). First, we are importing ``analysis`` and  ``plotting`` modules as well as a ``simulation`` module:

::

   import simulation.simple
   import analysis.event
   import analysis.beamline
   import analysis.background
   import analysis.pixel_detector
   import plotting.image
   import plotting.line
   import plotting.correlation

We load the `Condor <http://lmb.icm.uu.se/condor/simulation>`_ configuration file and specify a repetion rate of 120 Hz and a hitrate of 10%:

::

   sim = simulation.simple.Simulation("examples/simulation/virus.conf")
   sim.reprate = 120.
   sim.hitrate = 0.1

.. note::

   With a reprate of 120 and a hitrate of 10%, we basically define that every 12th given dataset will be a hit, independent of the real processing speed of the simulation


In the ``state`` variable, we need to provide the simulation ``sim`` and specify the datasets we want to extract:

::

   state = {
       'Facility': 'Dummy',

       'Dummy': {
           'Repetition Rate' : 120,
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

Inside the ``onEvent`` function we can now run algorithms on our simulated datasets and send plots to the frontend, for now we are just printing some extracted information:

::

   def onEvent(evt):
       analysis.event.printProcessingRate()
       analysis.event.printKeys(evt)
       analysis.event.printKeys(evt, "parameters")

Lets run our small simulation example:

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


