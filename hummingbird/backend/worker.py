# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Coordinates data reading, translation and analysis."""
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import imp
import logging
import os
import signal
import time

from hummingbird import ipc


class Worker(object):
    """Coordinates data reading, translation and analysis.

    This is the main class of the backend of Hummingbird. It uses a light source
    dependent translator to read and translate the data into a common format. It
    then runs whatever analysis algorithms are specified in the user provided
    configuration file.

    Args:
        config_file (str): The configuration file to load.
    """
    state = None
    conf = None
    def __init__(self, config_file, port):
        # Save the port as global variable in ipc
        ipc.zmqserver.ipc_port = port
        if(config_file is None):
            # Try to load an example configuration file
            config_file = os.path.abspath(os.path.dirname(__file__)+
                                          "/conf/dummy.py")
            logging.warning("No configuration file given! "
                            "Loading example configuration from %s",
                            (config_file))
        if not os.path.isfile(config_file):
            raise IOError('Could not find backend configuration file %s' % (config_file))
        Worker._config_file = config_file
        signal.signal(signal.SIGUSR1, self.raise_interruption)
        self.oldHandler = signal.signal(signal.SIGINT, self.ctrlcevent)
        self.translator = None
        self.load_conf()
        try:
            Worker.state['_config_file'] = config_file
        except TypeError:
            print()
            print('Failed to load configuration file')
            print()
            raise

        if 'reduce_nr_event_readers' in Worker.conf.state:
            rmin = Worker.conf.state['reduce_nr_event_readers']
        else:
            rmin = 0
            
        ipc.mpi.init_event_reader_comm(rmin)
        
        if ipc.mpi.is_event_reader():
            self.translator = init_translator(Worker.state)
        print("MPI rank %d, pid %d" % (ipc.mpi.rank, os.getpid()))

        if (ipc.mpi.is_zmqserver()):
            try:
                os.environ["OMPI_COMM_WORLD_SIZE"]
                pid = -1
                try:
                    with open('.pid', 'r') as file:
                        pid = int(file.read())
                except:
                    pass
                
                if not check_pid(pid):
                    with open('.pid', 'w') as file: file.write(str(os.getppid()))
            except KeyError:
                with open('.pid', 'w') as file: file.write(str(os.getpid()))
        self.reloadnow = False

    def raise_interruption(self, signum, stack):
        self.reloadnow = True
        
    def load_conf(self):
        """Load or reload the configuration file."""
        try:
            Worker.conf = imp.load_source('backend_conf', self._config_file)
        except Exception as e:
            print("Error reloading conf: %s" %e)
            return
        if self.translator is not None:
            # Not all translators have the init_detectors 
            try:
                self.translator.init_detectors(Worker.conf.state)                
            except AttributeError:
                pass
        if(Worker.state is None):
            Worker.state = Worker.conf.state
        else:
            # Only copy the keys that exist in the newly loaded state
            for k in Worker.conf.state:
                Worker.state[k] = Worker.conf.state[k]
            
    def start(self):
        """Start the event loop."""
        self.state['running'] = True
        if 'beginning_of_run' in dir(Worker.conf) and not ipc.mpi.is_master():
            print('Beginning of run (worker %i/%i) ...' % (ipc.mpi.worker_index()+1, ipc.mpi.nr_workers()))
            Worker.conf.beginning_of_run()
        if ipc.mpi.is_event_reader():
            print('Starting event loop (event reader %i/%i) ...' % (ipc.mpi.event_reader_rank()+1, ipc.mpi.nr_event_readers()))
            self.event_loop()
        elif ipc.mpi.is_master():
            print('Starting master loop ...')
            self.event_loop()            
        if 'end_of_run' in dir(Worker.conf) and not ipc.mpi.is_master():
            print('End of run (worker %i/%i) ...' % (ipc.mpi.worker_index()+1, ipc.mpi.nr_workers()))
            self.conf.end_of_run()
        if not ipc.mpi.is_master():
            ipc.mpi.slave_done()
        
    def ctrlcevent(self, whatSignal, stack):
        self.reloadnow = True
        signal.signal(signal.SIGINT, self.oldHandler)
        
    def event_loop(self):
        """The event loop.

        While ``state['running']`` is True, it will get events
        from the translator and process them as fast as possible.
        """
        while(True):
            try:
                while(Worker.state['running']) and not self.reloadnow:
                    self.reloadnow = self.reloadnow or ipc.mpi.checkreload()
                    if(ipc.mpi.is_master()):
                        is_exiting = ipc.mpi.master_loop()
                        if is_exiting:
                            return
                    else:
                        try:
                            evt = self.translator.next_event()
                            if evt is None:
                                return
                        except RuntimeError as e:
                            logging.warning("Some problem with %s (library used for translation), probably due to reloading the backend. (%s)" % (self.translator.library,e))
                            raise KeyboardInterrupt
                        except AttributeError as e:
                            logging.warning("Attribute error during event translation. Skipping event. (%s)" % e)
                            continue
                        except IndexError:
                            continue
                        ipc.set_current_event(evt)
                        try:
                            Worker.conf.onEvent(evt)
                        except (KeyError, TypeError, AttributeError) as exc:
                            logging.warning("Missing or wrong type of data, probably due to missing event data.", exc_info=True)
                        except (RuntimeError) as e:
                            logging.warning("Some problem with %s (library used for translation), probably due to reloading the backend." % self.translator.library,
                                            exc_info=True)
                        except StopIteration:
                            logging.warning("Stopping iteration.")
                            return
            except KeyboardInterrupt:
                try:
                    print("Hit Ctrl+c again in the next second to quit...")
                    time.sleep(1)
                    self.reloadnow = True
                    signal.signal(signal.SIGINT, self.ctrlcevent)
                except KeyboardInterrupt:
                    print("Exiting...")
                    break
            if self.reloadnow:
                self.reloadnow = False
                print("Reloading configuration file.")
                self.load_conf()
        try:
            Worker.conf.close()
        except:
            pass
        signal.signal(signal.SIGINT, self.oldHandler)


def init_translator(state):
    """Initialize the translator, depending on the state['Facility']."""
    if('Facility' not in state):
        raise ValueError("You need to set the 'Facility' in the configuration")
    elif(state['Facility'].lower() == 'lcls'):
        from .lcls import LCLSTranslator
        return LCLSTranslator(state)
    elif(state['Facility'].lower() == 'dummy'):
        from .dummy import DummyTranslator
        return DummyTranslator(state)
    elif(state['Facility'].lower() == 'flash'):
        from .flash import FLASHTranslator
        return FLASHTranslator(state)
    elif(state['Facility'].lower() == 'euxfel'):
        from .euxfel import EUxfelTrainTranslator
        return EUxfelTrainTranslator(state)
    else:
        raise ValueError('Facility %s not supported' % (state['Facility']))

def check_pid(pid):        
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True
