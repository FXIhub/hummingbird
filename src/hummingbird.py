#!/usr/bin/env python
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
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    parser.add_argument("-d", "--debug", help="output debug messages",
                        action="store_true")
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
        worker.start()
    elif(args.interface is not False):
        import interface
        interface.start_interface()

if __name__ == "__main__":
    main()
