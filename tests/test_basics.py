import time
import os, sys
import signal
if sys.version_info[0] == 2:
    import subprocess32 as subprocess # backport of subprocess from python 3 to work with python 2.7
else:
    import subprocess
__thisdir__ = os.path.dirname(os.path.realpath(__file__))

# Helper function for stopping Hummingbird
def stop_hummingbird(proc):
    proc.send_signal(signal.SIGINT)
    time.sleep(200e-3)
    proc.send_signal(signal.SIGINT)
    time.sleep(200e-3)
    proc.send_signal(signal.SIGINT)

# Helper function for reloading Hummingbird
def reload_hummingbird(proc):
    os.kill(proc.pid, signal.SIGINT)

# Helper function for starting Hummingbird
def start_hummingbird(conf=None, options=None, cmd=None):
    if cmd is None:
        cmd = __thisdir__ +  "/../hummingbird.py -b "
    if conf is not None:
        cmd += conf
    if options is not None:
        cmd += options
    print("Running: ", cmd)
    return subprocess.Popen(cmd.split(), shell=False, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

# Template for testing Hummingbird execution
def run_hummingbird(conf=None,cmd=None):
    try:
        p = start_hummingbird(conf=conf, cmd=cmd)
        try:
            output, error = p.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            stop_hummingbird(p)
            output, error = p.communicate()
        ret = p.returncode
        if error:
            has_error = ('error' in error or 'Error' in error)
            if has_error:
                ret = 1
                print(error.strip())
    except OSError as e:
        print(e.errno, e.strerror, e.filename)
    except:
        print(sys.exc_info()[0])
    assert (ret == 0), "Hummingbird %s did not finish successfully!" % (conf)

# Testing default execution of the backend
def test_testing_framework():
    run_hummingbird(cmd='/bin/ls')
def test_script_start():
    run_hummingbird(cmd=__thisdir__ +'/../hummingbird.py')
def test_basic_execution():
    run_hummingbird(conf='')
