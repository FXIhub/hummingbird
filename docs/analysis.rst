Contributing Algorithms
=======================

You can find all the analysis algorithms inside the ``src/analysis`` directory and all
plotting functions inside the ``src/plotting`` directory.

To add your own analysis algorithm to Hummingbird first check if there is
already an algorithm that already does, or could be easily extended to do what
you want. If there, then just edit the existing one and submit.

In many cases you will have to start from scratch though. Start by choosing to
what module you should add your algorithm (e.g. ``event.py``), or create a new
module if you think it does not fit in any existing one.

Most algorithms take as argument a ``Record`` (e.g. ``evt['pixel_detectors']['CCD']``) or a dictionary of ``Records``
(e.g. ``evt['pulseEnergies']``), although many also take the entire event
variable. You are free to choose, as long as you document it. 

If you want to keep some result from your algorithm to be used by subsequent
algorithms just return as a ``Record`` object and assign it to a new key of the
event variable in the conf file (e.g. ``examples/dummy/conf.py``)

.. note::

   Algorithms that want to keep results for further processing by other
   algorithms must be able to access the ``evt`` variable, so they must receive
   it as an argument.
   


