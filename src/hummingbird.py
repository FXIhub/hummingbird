#!/usr/bin/env python
# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""The main hummingbird file."""
import sys
import logging
import socket
import imp

from utils.cmdline_args import argparser
# Leave this for backwards compatibility with old configuration files
parse_cmdline_args = argparser.parse_args

PORT_RANGE = (0, 65535)

<<<<<<< HEAD
def parse_cmdline_args():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description='Hummingbird - '
                                     'Monitoring and Analysing FXI experiments.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--interface",
                       help="start the control and display interface",
                       action="store_true")
    group.add_argument('-b', '--backend', metavar='conf.py',
                       type=str, help="start the backend with "
                       "given configuration file", nargs='?', const=True)
    group.add_argument('-r', '--reload', help='reloads the backend',
                       action='store_true')
    parser.add_argument("-p", "--port",
                        type=int, default=13131, help="overwrites the port, defaults to 13131")
    parser.add_argument("-I", "--influxdb", const="influxdb://localhost/hummingbird",
                        type=str, help="spool all scalar data to the specified InfluxDB instance", nargs = "?")
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    parser.add_argument("-d", "--debug", help="output debug messages",
                        action="store_true")
    parser.add_argument("--profile", help="generate and output profiling information",
                        action="store_true")
    parser.add_argument("--no-restore", help="no restoring of Qsettings",
                        action="store_false")
=======
def main():
    """The entry point of the program"""
>>>>>>> e6dd1a59dac5d539d67f834e800726f2cc29efe0

    if(len(sys.argv) == 1):
        argparser.print_help()

    if "-b" in sys.argv and (sys.argv.index("-b")+1 < len(sys.argv)):
        config_file = sys.argv[sys.argv.index("-b")+1]
        imp.load_source('__config_file', config_file)
        
    args = argparser.parse_args()
    
    level = logging.WARNING
    if args.verbose:
        level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    logging.basicConfig(format='%(filename)s:%(lineno)d %(message)s', level=level)

    if args.port < PORT_RANGE[0] or args.port > PORT_RANGE[1]:
        print "The port must be from {0} to {1}".format(PORT_RANGE[0], PORT_RANGE[1])
        exit(0)

    if(args.backend is not None):
        if (args.influxdb is not None):
            from ipc import influx
            influx.init(args.influxdb)
        from backend import Worker
        if(args.backend != True):
            worker = Worker(args.backend, args.port)
        else:
            worker = Worker(None, args.port)
        if not args.profile:
            worker.start()
        else:
            from pycallgraph import PyCallGraph
            from pycallgraph.output import GraphvizOutput
            import ipc.mpi
            import os
            graphviz = GraphvizOutput()
            graphviz.output_file = 'pycallgraph_%d.png' % (ipc.mpi.rank)
            with PyCallGraph(output=graphviz):
                worker.start()
    elif(args.interface is not False):
        import interface
        interface.start_interface(args.no_restore)
    elif(args.reload is not False):
        import os, signal
        with open('.pid', 'r') as file:
            pid = int(file.read())
        os.kill(pid, signal.SIGUSR1)

if __name__ == "__main__":
    main()
