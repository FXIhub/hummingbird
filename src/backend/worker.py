"""Coordinates data reading, translation and analysis.
"""
import os
import logging
import imp
import ipc
import time
import signal
import psutil

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
    def __init__(self, config_file):
        if(config_file is None):
            # Try to load an example configuration file
            config_file = os.path.abspath(os.path.dirname(__file__)+
                                          "/../../examples/psana/cxitut13/conf.py")
            logging.warning("No configuration file given! "
                            "Loading example configuration from %s",
                            (config_file))
        self._config_file = config_file
        # self.backend_conf = imp.load_source('backend_conf', config_file)
        signal.signal(signal.SIGUSR1, self.raise_interruption)
        
        self.load_conf()
        Worker.state['_config_file'] = config_file
        Worker.state['_config_dir'] = os.path.dirname(config_file)

        if(not ipc.mpi.is_master()):
            self.translator = init_translator(Worker.state)

        if (ipc.mpi.is_zmqserver()):
            try:
                os.environ["OMPI_COMM_WORLD_SIZE"]
                pid = -1
                try:
                    with open('.pid', 'r') as file:
                        pid = int(file.read())
                except:
                    pass
                
                if not psutil.pid_exists(pid):
                    with open('.pid', 'w') as file: file.write(str(os.getppid()))
            except KeyError:
                with open('.pid', 'w') as file: file.write(str(os.getpid()))
        self.reloadnow = False
        print 'Starting backend...'

    def raise_interruption(self, signum, stack):
        print "Raising interrupt"
        raise KeyboardInterrupt
        
    def load_conf(self):
        """Load or reload the configuration file."""
        Worker.conf = imp.load_source('backend_conf', self._config_file)
        if(Worker.state is None):
            Worker.state = Worker.conf.state
        else:
            # Only copy the keys that exist in the newly loaded state
            for k in Worker.conf.state:
                Worker.state[k] = Worker.conf.state[k]

    def start(self):
        """Start the event loop."""
        Worker.state['running'] = True
        self.event_loop()

    def ctrlcevent(self, whatSignal, stack):
        self.reloadnow = True
        signal.signal(signal.SIGINT, self.oldHandler)

    def event_loop(self):
        """The event loop.

        While ``state['running']`` is True, it will get events
        from the translator and process them as fast as possible.
        """
        self.oldHandler = signal.signal(signal.SIGINT, self.ctrlcevent)
        while(True):
            try:
                while(Worker.state['running']):
                    if(ipc.mpi.is_master()):
                        ipc.mpi.master_loop()
                    else:
                        try:
                            evt = self.translator.next_event()
                        except (RuntimeError) as e:
                            logging.warning("Some problem with psana, probably due to reloading the backend. (%s)" % e)
                            raise KeyboardInterrupt
                        ipc.set_current_event(evt)
                        try:
                            Worker.conf.onEvent(evt)
                        except (KeyError, TypeError) as exc:
                            logging.warning("Missing or wrong type of data, probably due to missing event data.", exc_info = True)
                        except (RuntimeError) as e:
                            logging.warning("Some problem with psana, probably due to reloading the backend.", exc_info=True)
                            
                    if self.reloadnow == True:
                        self.reloadnow = False
                        raise KeyboardInterrupt()
            except KeyboardInterrupt:
                try:
                    print "Hit Ctrl+c again in the next second to quit..."
                    time.sleep(1)
                    print "Reloading configuration file."
                    self.load_conf()
                    self.oldHandler = signal.signal(signal.SIGINT, self.ctrlcevent)
                except KeyboardInterrupt:
                    print "Exiting..."
                    break
        signal.signal(signal.SIGINT, self.oldHandler)


def init_translator(state):
    """Initialize the translator, depending on the state['Facility']."""
    if('Facility' not in state):
        raise ValueError("You need to set the 'Facility' in the configuration")
    elif(state['Facility'].lower() == 'lcls'):
        from backend.lcls import LCLSTranslator
        return LCLSTranslator(state)
    elif(state['Facility'].lower() == 'dummy'):
        from backend.dummy import DummyTranslator
        return DummyTranslator(state)
    else:
        raise ValueError('Facility %s not supported' % (state['Facility']))
