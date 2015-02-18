Getting Started
===============

Downloading the Source Code
---------------------------

To be able to use Hummingbird you first need to obtain the code
To do that just clone the git repository:

::

    $ git clone git@bitbucket.org:spinitiative/hummingbird.git

There is no need for any other installation steps.

Running Hummingbird
-------------------

You can run ``./hummingbird.py -h`` to get some information about the
available options of Hummingbird:

::

   $ ./hummingbird.py -h
   usage: hummingbird.py [-h] [-i | -b [conf.py]]

   Hummingbird - the XFEL Online Analysis Framework.

   optional arguments:
     -h, --help            show this help message and exit
     -i, --interface       start the control and display interface
     -b [conf.py], --backend [conf.py]
                           start the backend with given configuration file

You can run Hummingbird in either interface (`-i`) or backend (`-b`) mode.

When running in interface mode the program will wait for connections from
backends and display any data that the backends send to it. 

.. note::
   
   The interface has not yet been implemented.

When running in backend mode the program will read and analyse data according
to the provided configuration file.

Before running you need some lightsource specific setup. For example to be
able to run from LCLS data you need to run ``. /reg/g/psdm/etc/ana_env.sh``,
which makes the `psana` python module available.

.. note::
   
   If you get strange errors running Hummingbird like, syntax errors or
   ``ImportError: No module named psana`` make sure that you have run the setup
   step:

   ``. /reg/g/psdm/etc/ana_env.sh``


When no configuration file is given, the file ``examples/cxitut13/conf.py``, the
default configuration file, will be used. This will print some basic information
which should give you some basic information about the cxitut13 run.
The default configuration file will only work on LCLS machines.


