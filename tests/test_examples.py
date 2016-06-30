import time
import os, sys
import signal
import subprocess32 as subprocess # backport of subprocess from python 3 to work with python 2.7

__thisdir__ = os.path.dirname(os.path.realpath(__file__))

def stop_example(proc):
    proc.send_signal(signal.SIGINT)
    #os.kill(proc.pid, signal.SIGINT)
    time.sleep(200e-3)
    proc.send_signal(signal.SIGINT)
    #os.kill(proc.pid, signal.SIGINT)
    time.sleep(200e-3)
    proc.send_signal(signal.SIGINT)
    #os.kill(proc.pid, signal.SIGINT)

def reload_example(proc):
    os.kill(proc.pid, signal.SIGINT)
    
def start_example(filename='', options=None):
    cmd = '/bin/ls'
    if filename is not None:
        cmd = __thisdir__ +  "/../hummingbird.py -b "
        cmd += filename
    if options is not None:
        cmd += options
    print "Running: ", cmd
    return subprocess.Popen(cmd.split(), shell=False, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

def run_example(example=''):
    try:
        p = start_example(example)
        try:
            output, error = p.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            stop_example(p)
            output, error = p.communicate()
        ret = p.returncode
        if error:
            has_error = ('error' in error or 'Error' in error)
            if has_error:
                ret = 1
                print error.strip()
    except OSError as e:
        print e.errno, e.strerror, e.filename
    except:
        print sys.exc_info()[0]
    assert (ret == 0), "Example %s did not finish successfully!" %example
        
# Testing default execution of backend
def test_testing_framework():
    run_example(None)

def test_basic_execution():
    run_example()

# Testing basic examples
def test_dummy_example():
    run_example(__thisdir__ + '/../examples/basic/dummy.py')
def test_simulation_example():
    run_example(__thisdir__ + '/../examples/basic/simulation.py')
def test_detector_example():
    run_example(__thisdir__ + '/../examples/basic/detector.py')
def test_hitfinding_example():
    run_example(__thisdir__ + '/../examples/basic/hitfinding.py')
def test_correlation_example():
    run_example(__thisdir__ + '/../examples/basic/correlation.py')

if __name__ == '__main__':
    #test_detector_example()
    test_hitfinding_example()
