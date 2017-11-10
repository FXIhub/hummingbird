from test_basics import run_hummingbird
import os, sys
__thisdir__ = os.path.dirname(os.path.realpath(__file__))

# Testing basic examples
def test_dummy_example():
    run_hummingbird(conf=__thisdir__ + '/../examples/basic/dummy.py')
def test_simulation_example():
    run_hummingbird(conf=__thisdir__ + '/../examples/basic/simulation.py')
def test_detector_example():
    run_hummingbird(conf=__thisdir__ + '/../examples/basic/detector.py')
def test_hitfinding_example():
    run_hummingbird(conf=__thisdir__ + '/../examples/basic/hitfinding.py')
def test_correlation_example():
    run_hummingbird(conf=__thisdir__ + '/../examples/basic/correlation.py')
def test_lcls_mimi_dark_example():
    run_hummingbird(conf=__thisdir__ + '/../examples/lcls/mimi_dark.py')
def test_lcls_mimi_hits_example():
    run_hummingbird(conf=__thisdir__ + '/../examples/lcls/mimi_hits.py')
