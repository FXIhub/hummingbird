Installation
============

**From PyPi** - The simplest is to install hummingbird directly from pypi:

::
   
      $ pip install hummingbird


**From Source** - If you wish to install from source, you can do so by cloning the git repository:

::

   $ git clone https://github.com/FXIhub/hummingbird.git

And then use `pip` from inside the cloned directory:

::

   $ pip install -e .


**Running Hummingbird** - After a successful installation, you will be able to start `hummingbird` from anywhere on your system, e.g.:

::

   $ hummingbird -i

Supported Operating Systems
---------------------------

* Linux
* MacOS

Requirements
------------

* `Python <http://python.org>`_  >= 3.8
* `PyQt5 <https://riverbankcomputing.com/software/pyqt/>`_
* `PyQtGraph <http://www.pyqtgraph.org/>`_ >= 0.10
* `Numpy <http://www.numpy.org>`_
* `Scipy <http://www.scipy.org>`_
* `PyZMQ <http://zeromq.org/bindings:python>`_
* `pexpect <https://pypi.python.org/pypi/pexpect/>`_
* `mpi4py <http://pythonhosted.org/mpi4py/>`_
* `h5py <http://h5py.org>`_
* `h5writer <https://pypi.python.org/pypi/h5writer>`_
* `pint <http://pint.readthedocs.io/en/latest/>`_
* `pytz <https://github.com/stub42/pytz/>`_


Requirements for testing
------------------------
* `pytest <https://pypi.python.org/pypi/pytest>`_

Some of the `more advanced examples <advanced_examples.html>`_ require an installation of `libspimage <https://github.com/FXIhub/libspimage>`_ and/or `condor <https://github.com/FXIhub/condor>`_.
