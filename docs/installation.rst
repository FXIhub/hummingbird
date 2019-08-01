Installation
============

Supported Operating Systems
---------------------------

* Linux
* MacOS

Requirements
------------

* `Python 2.7 or 3.4 <http://python.org>`_ 
* `PyQt4, PyQt5 <https://riverbankcomputing.com/software/pyqt/intro>`_ or `PySide <https://wiki.qt.io/PySide>`_
* `PyQtGraph <http://www.pyqtgraph.org/>`_ >= 0.10
* `Numpy <http://www.numpy.org>`_
* `Scipy <http://www.scipy.org>`_
* `PyZMQ <http://zeromq.org/bindings:python>`_
* `pexpect <https://pypi.python.org/pypi/pexpect/>`_
* `mpi4py <http://pythonhosted.org/mpi4py/>`_
* `h5py <http://h5py.org>`_
* `h5writer <https://pypi.python.org/pypi/h5writer>`_
* `pint <http://pint.readthedocs.io/en/latest/>`_

Requirements for testing
------------------------
* `subprocess32 <https://pypi.python.org/pypi/subprocess32>`_ (only for python 2.7)
* `pytest <https://pypi.python.org/pypi/pytest>`_

Some of the `more advanced examples <advanced_examples.html>`_ require an installation of `libspimage <https://github.com/FXIhub/libspimage>`_ and/or `condor <https://github.com/FXIhub/condor>`_.

Downloading the Source Code
---------------------------

To be able to use Hummingbird you first need to obtain the code
To do that just clone the git repository:

::

   $ git clone https://github.com/FXIhub/hummingbird.git

There is no need for any other installation steps.

Installing the requirements
---------------------------

The simplest way to install the requirements is to use `pip`:

::

   $ pip install -r requirements.txt

After this command executes successfully, you will be able to start `hummingbird.py`

