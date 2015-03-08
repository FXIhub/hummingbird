"""Coordinates data reading, translation and analysis.
"""

import os
import logging
import imp
import ipc
import time 

class Backend(object):
    state = None
    conf = None
    """Coordinates data reading, translation and analysis.
    
    This is the main class of the backend of Hummingbird. It uses a light source
    dependent translator to read and translate the data into a common format. It
    then runs whatever analysis algorithms are specified in the user provided
    configuration file.
    
    Args:
        config_file (str): The configuration file to load.        
    """
    def __init__(self, config_file):
        if(config_file is None):
            # Try to load an example configuration file
            config_file = os.path.abspath(os.path.dirname(__file__)+
                                          "/../../examples/cxitut13/conf.py")
            logging.warning("No configuration file given! "
                            "Loading example configuration from %s" % (config_file))
    
        self._config_file = config_file
        # self.backend_conf = imp.load_source('backend_conf', config_file)
        self.load_conf()
        Backend.state['_config_file'] = config_file
        Backend.state['_config_dir'] = os.path.dirname(config_file)
        if(not ipc.mpi.is_master()):
            self.translator = init_translator(Backend.state)
        print 'Starting backend...'

    def load_conf(self):        
        Backend.conf = imp.load_source('backend_conf', self._config_file)        
        if(Backend.state is None):
            Backend.state = Backend.conf.state
        else:
            # Only copy the keys that exist in the newly loaded state
            for k in Backend.conf.state:
                Backend.state[k] = Backend.conf.state[k]

    def start(self):
        """Start the event loop.
        
        Sets ``state['running']`` to True. While ``state['running']`` is True, it will
        get events from the translator and process them as fast as possible.
        """
        Backend.state['running'] = True
        self.event_loop()

    def event_loop(self):
        while(True):
            try:
                while(Backend.state['running']):
                    if(ipc.mpi.is_master()):
                        ipc.mpi.master_loop()
                    else:
                        evt = self.translator.nextEvent()
                        ipc.set_current_event(evt)
                        Backend.conf.onEvent(evt)
            except KeyboardInterrupt:  
                try:
                    print "Hit Ctrl+c again in the next second to quit..."
                    time.sleep(1)
                    print "Reloading configuration file."                
                    self.load_conf()
                except KeyboardInterrupt:  
                    print "Exiting..."
                    break

        
def init_translator(state):
    if('Facility' not in state):
        raise ValueError("You need to set the 'Facility' in the configuration")
    elif(state['Facility'] == 'LCLS'):
        from lcls import LCLSTranslator
        return LCLSTranslator(state)
    elif(state['Facility'] == 'dummy'):
        from dummy import DummyTranslator
        return DummyTranslator(state)
    else:
        raise ValueError('Facility %s not supported' % (state['Facility']))
