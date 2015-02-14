import os
import logging
import imp
import translation
#from mpi4py import MPI

class Backend(object):
    def __init__(self, config_file):
        if(config_file is None):
            # Try to load an example configuration file
            config_file = os.path.abspath(os.path.dirname(__file__)+
                                          "/../examples/cxitut13/conf.py")
            logging.warning("No configuration file given! "
                            "Loading example configuration from %s" % (config_file))
    
            self.backend_conf = imp.load_source('backend_conf', config_file)
            self.translator = translation.init_translator(self.backend_conf.state)
            print 'Starting backend...'

    def mpi_init(self):
        comm = MPI.COMM_WORLD
        self.rank = comm.Get_rank()
        print "MPI rank %d inited" % rank

    def start(self):
        self.backend_conf['_running'] = True
        while(self.backend_conf['_running']):
            evt = self.translator.nextEvent()
            self.backend_conf.onEvent(evt)
            
        
