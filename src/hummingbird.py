#!/usr/bin/env python
print "Launching"

"""Hummingbird main file."""

import sys
import argparse
import logging

def parse_cmdline_args():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description='Hummingbird - '
                                     'the XFEL Online Analysis Framework.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--interface",
                       help="start the control and display interface",
                       action="store_true")
    group.add_argument('-b', '--backend', metavar='conf.py',
                       type=str, help="start the backend with "
                       "given configuration file", nargs='?', const=True)
    group.add_argument('-r', '--reload', help='reloads the backend',
                       action='store_true')
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    parser.add_argument("-d", "--debug", help="output debug messages",
                        action="store_true")
    parser.add_argument("-p", "--profile", help="generate and output profiling information",
                        action="store_true")
    parser.add_argument("--no-restore", help="no restoring of Qsettings",
                        action="store_false")
    
    if(len(sys.argv) == 1):
        parser.print_help()
    return parser.parse_args()

def main():
    """The entry point of the program"""
    args = parse_cmdline_args()
    level = logging.WARNING
    if args.verbose:
        level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    logging.basicConfig(format='%(filename)s:%(lineno)d %(message)s', level=level)

    if(args.backend is not None):
        from backend import Worker
        if(args.backend != True):
            worker = Worker(args.backend)
        else:
            worker = Worker(None)
        if not args.profile:
            worker.start()
        else:
            from pycallgraph import PyCallGraph
            from pycallgraph.output import GraphvizOutput
            with PyCallGraph(output=GraphvizOutput()):
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
