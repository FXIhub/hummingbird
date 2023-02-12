from test_basics import run_hummingbird
from test_imports import test_import_backend_lcls
import os, sys, warnings
__thisdir__ = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Testing basic examples
def test_dummy_example():
    run_hummingbird(conf=__thisdir__ + '/examples/basic/dummy.py')
def test_simulation_example():
    run_hummingbird(conf=__thisdir__ + '/examples/basic/simulation.py')
def test_detector_example():
    run_hummingbird(conf=__thisdir__ + '/examples/basic/detector.py')
def test_hitfinding_example():
    run_hummingbird(conf=__thisdir__ + '/examples/basic/hitfinding.py')
def test_correlation_example():
    run_hummingbird(conf=__thisdir__ + '/examples/basic/correlation.py')
def test_lcls_mimi_dark_example():
    if test_import_backend_lcls():
        run_hummingbird(conf=__thisdir__ + '/examples/lcls/mimi_dark.py')
    else:
        warnings.warn(UserWarning("The LCLS backend is not available and can therefore not be tested..."))
def test_lcls_mimi_hits_example():
    if test_import_backend_lcls():
        run_hummingbird(conf=__thisdir__ + '/examples/lcls/mimi_hits.py')
    else:
        warnings.warn(UserWarning("The LCLS backend is not available and can therefore not be tested..."))
