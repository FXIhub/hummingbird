# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
__version__ = "1.3b"

"""The main hummingbird file."""
import importlib
import logging
import socket
import sys

from .utils.cmdline_args import argparser

logging.basicConfig(format='%(filename)s:%(lineno)d %(message)s')


# Leave this for backwards compatibility with old configuration files
parse_cmdline_args = argparser.parse_args

PORT_RANGE = (0, 65535)

def main():
    """The entry point of the program"""

    if(len(sys.argv) == 1):
        argparser.print_help()
        
    args = argparser.parse_args()
    level = logging.WARNING
    if args.verbose:
        level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    logger = logging.getLogger()
    logger.setLevel(level)

    if args.port < PORT_RANGE[0] or args.port > PORT_RANGE[1]:
        print("The port must be from {0} to {1}".format(PORT_RANGE[0], PORT_RANGE[1]))
        exit(0)

    if(args.backend is not None):
        if (args.influxdb is not None):
            from .ipc import influx
            influx.init(args.influxdb)
        from .backend import Worker
        if(args.backend != True):
            worker = Worker(args.backend, args.port)
        else:
            worker = Worker(None, args.port)
        if not args.profile:
            worker.start()
        else:
            from pycallgraph import PyCallGraph
            from pycallgraph.output import GraphvizOutput
            from . import ipc
            import os
            graphviz = GraphvizOutput()
            graphviz.output_file = 'pycallgraph_%d.png' % (ipc.mpi.rank)
            with PyCallGraph(output=graphviz):
                worker.start()
    elif(args.interface is not False):
        from . import interface
        interface.start_interface(args.no_restore)
    elif(args.reload is not False):
        import os, signal
        with open('.pid', 'r') as file:
            pid = int(file.read())
        os.kill(pid, signal.SIGUSR1)

if __name__ == "__main__":
    main()
