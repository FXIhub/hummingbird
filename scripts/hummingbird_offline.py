#!/usr/bin/env python

import sys, os
import argparse

def parse_cmdline_args():
    parser = argparse.ArgumentParser(description='Hummingbird extraction script - '
                                     'Analysing run data offline')

    parser.add_argument('-b', '--backend', metavar='conf.py', nargs='?',
                       help="start the backend with given configuration file",
                       type=str)

    parser.add_argument('-r', '--run-number', metavar='run_number', nargs='?',
                       help="run number",
                       type=int)

    parser.add_argument('-f', '--number-of-frames', metavar='number_of_frames', nargs='?',
                        help="number of frames to be processed",
                        type=int)

    parser.add_argument('-n', '--number-of-processes', metavar='number_of_processes', nargs='?',
                       help='number of MPI processes',
                       type=int)
    
    if(len(sys.argv) == 1):
        parser.print_help()
        print "ERROR: Not enough arguments provided."
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_cmdline_args()
    this_dir = os.path.dirname(os.path.realpath(__file__))
    cmd = ""
    cmd += "export HB_RUN=%i; " % args.run_number
    if args.number_of_frames is not None:
        cmd += "export HB_NUMBER_OF_FRAMES=%i; " % args.number_of_frames
    else:
        cmd += "export HB_NUMBER_OF_FRAMES=-1; "
    cmd += "mpiexec -n %i %s/../hummingbird.py -b %s" % (args.number_of_processes, this_dir, args.backend)
    print cmd
    os.system(cmd)
