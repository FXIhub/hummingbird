#!/usr/bin/env python

import sys
import argparse
import logging
from backend import Backend

def parse_cmdline_args():
    parser = argparse.ArgumentParser(description='Hummingbird - the XFEL Online Analysis Framework.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--interface", help="start the control and display interface",
                       action="store_true")
    group.add_argument('-b', '--backend',  metavar='conf.py', 
                       type=str, help="start the backend with "
                       "given configuration file", nargs='?', const=True)
    if(len(sys.argv) == 1):
        parser.print_help()
    return parser.parse_args()

def start_interface():
    print 'Starting interface...'

if __name__ == "__main__":
    logging.basicConfig(format='%(filename)s:%(lineno)d %(message)s')
    args = parse_cmdline_args()
    if(args.backend is not None):
        if(args.backend != True):
            backend = Backend(args.backend)
        else:
            backend = Backend(None)
        backend.start()
    elif(args.interface is not False):
        start_interface()
        
    
