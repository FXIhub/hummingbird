import os, sys
import warnings
__thisdir__ = os.path.dirname(os.path.realpath(__file__))

# Testing for broken MPI installation
def test_import_mpi4py():
    try:
        from mpi4py import MPI
    except ImportError:
        warnings.warn(UserWarning("MPI for python could not be imported"))
        assert(1 == 1)
    sys.path.pop(0)

# Testing the import of the ipc module
def test_import_ipc_module():
    sys.path.insert(0, __thisdir__ + "/../src")
    try:
        import ipc
    except ImportError:
        assert (1 == 0), "The ipc module could not be imported"
    sys.path.pop(0)

# Testing the import of the Qt modules QtGui and QtCore
def test_import_qt_modules():
    sys.path.insert(0, __thisdir__ + "/../src")
    try:
        from interface.Qt import QtGui, QtCore
    except ImportError:
        assert (1 == 0), "The Qt modules QtGui and QtCore could not be imported"
    sys.path.pop(0)
    
# Testimg the import of the interface module
# BD: Need to install PyQt on travis before we can test
def test_import_interface_module():
    sys.path.insert(0, __thisdir__ + "/../src")
    try:
        import interface
    except ImportError:
        assert (1 == 0), "The interface module could not be imported"
    sys.path.pop(0)

# Testing the import of the pyqtgraph module
def test_import_pyqtgraph_module():
    try:
        import pyqtgraph
    except ImportError:
        assert (1 == 0), "The pyqtgraph module could not be imported"
    sys.path.pop(0)

# Testing the import of the plotting module
def test_import_plotting_module():
    sys.path.insert(0, __thisdir__ + "/../src")
    try:
        import plotting
    except ImportError:
        assert (1 == 0), "The plotting module could not be imported"
    sys.path.pop(0)

# Testing the import of the analysis module
def test_import_analysis_module():
    sys.path.insert(0, __thisdir__ + "/../src")
    try:
        import analysis
    except:
        assert (1 == 0), "The analysis module could not be imported"
    sys.path.pop(0)

# Testing the import of the simulation module
def test_import_simulation_module():
    sys.path.insert(0, __thisdir__ + "/../src")
    try:
        import simulation
    except:
        assert (1 == 0), "The simulation module could not be imported"
    sys.path.pop(0)

# Testing the import of the utils module
def test_import_utils_module():
    sys.path.insert(0, __thisdir__ + "/../src")
    try:
        import utils
    except:
        assert (1 == 0), "The utils module could not be imported"
    sys.path.pop(0)
    
# Testing if LCLS backend is imported properly
def test_import_backend_lcls():
    sys.path.insert(0, __thisdir__ + "/../src")
    try:
        import backend.lcls
    except ImportError:
        warnings.warn(UserWarning("The LCLS backend could not be imported"))
        assert(1 == 1)
    sys.path.pop(0)

