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
    if(len(sys.argv) == 1):
        parser.print_help()
    return parser.parse_args()

def main():
    """The entry point of the program"""
    logging.basicConfig(format='%(filename)s:%(lineno)d %(message)s')
    args = parse_cmdline_args()
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
