Configuration
=============

The backend of Hummingbird uses a configuration file written in Python. 
This gives the user immense flexibility and power, with the responsability that
carries.


Learning by Example
-------------------

Here is an example of a configuration file used to gather some basic statistics
about a run stored in an XTC file:

::

   import analysis.event
   import analysis.beamline
   import analysis.pixel_detector
   
   state = {
       'Facility': 'LCLS',
       'LCLS/DataSource': '/data/rawdata/LCLS/cxi/cxic9714/xtc/e419-r0203-s01-c00.xtc'
   }
   
   def onEvent(evt):
       analysis.beamline.printPulseEnergy(evt['pulseEnergies'])
       analysis.beamline.printPhotonEnergy(evt['photonEnergies'])
       print "EPICS photon energy = %g eV" %(evt['parameters']['SIOC:SYS0:ML00:AO541'].data)
       analysis.pixel_detector.printStatistics(evt['photonPixelDetectors'])
       analysis.pixel_detector.printStatistics(evt['ionTOFs'])
       analysis.event.printID(evt['eventID'])
       analysis.event.printProcessingRate()

One can divide in three sections. In the first one the necessary analysis
modules are imported:

::

   import analysis.event
   import analysis.beamline
   import analysis.pixel_detector

In this case three modules are imported. You can find what modules are available
by peeking into the ``src/analysis`` and ``src/plotting`` directory or by browsing the 
:doc:`API documentation <API/modules>`.



In the second section of the configuration file the global options for the program are set:

::

   state = {
       'Facility': 'LCLS',
       'LCLS/DataSource': '/data/rawdata/LCLS/cxi/cxic9714/xtc/e419-r0203-s01-c00.xtc'
   }

The global options must always called ``state``. In this particular example
first the ``Facility`` is set to LCLS, the only supported option at the moment.
The following line defines where data is read from. It accepts any format that
``psana`` accepts (e.g. an XTC filename, an exp/run pair like
``exp=XCS/xcstut13:run=15``, or a shared memory string like
``shmem=0_21_psana_AMO.0:stop=no``.

In the third and final section of the configuration file the algorithms that are
run on each of the events are defined:

::

   def onEvent(evt):
       analysis.beamline.printPulseEnergy(evt['pulseEnergies'])
       analysis.beamline.printPhotonEnergy(evt['photonEnergies'])
       print "EPICS photon energy = %g eV" %(evt['parameters']['SIOC:SYS0:ML00:AO541'].data)
       analysis.pixel_detector.printStatistics(evt['photonPixelDetectors'])
       analysis.pixel_detector.printStatistics(evt['ionTOFs'])
       analysis.event.printID(evt['eventID'])
       analysis.event.printProcessingRate()

The list of algorithms to run must always be defined inside the ``onEvent``
function, which must take exactly one argument, named ``evt`` in this case. 

This is a function that is called once for every event. The argument is a
dictionary containing the measurements in each event. For example in this case
``evt['pulseEnergies']`` is a dictionary with 4 entries, corresponding to the 4
gas monitor detector at LCLS. Each of the entries is a ``Record`` class containing at
least ``name``, ``data`` and often ``unit`` attributes.

.. tip::

   To see a list of the available keys inside the ``evt`` simply run ``evt.keys()``.

Using the ``evt`` variable one can pass data to multiple analysis algorithms.
These algorithms will do the required analysis, communicate the results with the
interface, and store any eventual output back onto the ``evt`` dictionary, using a
new key. That way future analysis can use the output of previous ones.

For a list of available analysis algorithms please check the relevant :doc:`API documentation <API/analysis>`.

This example is ``examples/psana/xtc/conf.py``. You can find more example configurations inside the directories in ``examples`` and explained in :doc:`More examples <examples>`.
