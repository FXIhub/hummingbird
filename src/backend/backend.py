"""Coordinates data reading, translation and analysis.
"""

import os
import logging
import imp
from . import init_translator
#from mpi4py import MPI

class Backend(object):
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
        self.backend_conf = imp.load_source('backend_conf', config_file)
        self.translator = init_translator(self.backend_conf.state)
        print 'Starting backend...'

    def mpi_init(self):
        """Initialize MPI"""
        comm = MPI.COMM_WORLD
        self.rank = comm.Get_rank()
        print "MPI rank %d inited" % rank

    def start(self):
        """Start the event loop.
        
        Sets ``state['running']`` to True. While ``state['running']`` is True, it will
        get events from the translator and process them as fast as possible.
        """
        self.backend_conf.state['running'] = True
        while(self.backend_conf.state['running']):
            evt = self.translator.nextEvent()
            self.backend_conf.onEvent(evt)
            
        
