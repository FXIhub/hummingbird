#!/usr/bin/env python
# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""The main hummingbird file."""
import sys
import argparse
import logging
import socket

import backend.lcls

PORT_RANGE = (0, 65535)

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
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    parser.add_argument("-d", "--debug", help="output debug messages",
                        action="store_true")
    parser.add_argument("--profile", help="generate and output profiling information",
                        action="store_true")
    parser.add_argument("--no-restore", help="no restoring of Qsettings",
                        action="store_false")
    
    parser = backend.lcls.add_cmdline_args(parser)
    
    if(len(sys.argv) == 1):
        parser.print_help()
    return parser.parse_args()

cmdline_args = None
def main():
    """The entry point of the program"""
    global cmdline_args
    print cmdline_args
    cmdline_args = parse_cmdline_args()
    print cmdline_args
    level = logging.WARNING
    if cmdline_args.verbose:
        level = logging.INFO
    if cmdline_args.debug:
        level = logging.DEBUG
    logging.basicConfig(format='%(filename)s:%(lineno)d %(message)s', level=level)

    if cmdline_args.port < PORT_RANGE[0] or cmdline_args.port > PORT_RANGE[1]:
        print "The port must be from {0} to {1}".format(PORT_RANGE[0], PORT_RANGE[1])
        exit(0)

    if(cmdline_args.backend is not None):
        from backend import Worker
        if(cmdline_args.backend != True):
            worker = Worker(cmdline_args.backend, cmdline_args.port)
        else:
            worker = Worker(None, cmdline_args.port)
        if not cmdline_args.profile:
            worker.start()
        else:
            from pycallgraph import PyCallGraph
            from pycallgraph.output import GraphvizOutput
            with PyCallGraph(output=GraphvizOutput()):
                worker.start()
    elif(cmdline_args.interface is not False):
        import interface
        interface.start_interface(cmdline_args.no_restore)
    elif(cmdline_args.reload is not False):
        import os, signal
        with open('.pid', 'r') as file:
            pid = int(file.read())
        os.kill(pid, signal.SIGUSR1)

if __name__ == "__main__":
    main()
