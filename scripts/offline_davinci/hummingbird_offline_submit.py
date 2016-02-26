#!/usr/bin/env python

import sys, os
import argparse

def parse_cmdline_args():
    parser = argparse.ArgumentParser(description='Hummingbird extraction script - '
                                     'Analysing run data offline')

    parser.add_argument('-b', '--backend', metavar='conf.py', nargs='?',
                        help="start the backend with given configuration file",
                        type=str)

    #parser.add_argument('-o', '--outdir', metavar='./', nargs='?',
    #                    help="output directory",
    #                    type=str)

    parser.add_argument('--lcls-run-number', metavar='lcls_run_number', nargs='?',
                        help="run number",
                        type=int)

    parser.add_argument('--lcls-number-of-frames', metavar='lcls_number_of_frames', nargs='?',
                        help="number of frames to be processed (optional)",
                        type=int)
    
    parser.add_argument('-n', '--number-of-processes', metavar='number_of_processes', nargs='?',
                        help='number of MPI processes', default=1,
                        type=int)
    
    if(len(sys.argv) == 1):
        parser.print_help()
        print "ERROR: Not enough arguments provided."
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_cmdline_args()
    this_dir = os.path.dirname(os.path.realpath(__file__))
    #out_dir = "./" if args.outdir else args.outdir
    run = "r%04i" % args.lcls_run_number
    slurm = "%s/%s.sh" % (this_dir, run)
    output = "%s/%s.out" % (this_dir, run)
    port = 13131 + args.lcls_run_number
    
    s = []
    s += "#!/bin/sh\n"
    s += "#SBATCH --job-name=HB_r%04i\n" % args.lcls_run_number
    s += "#SBATCH --ntasks=%i\n" % args.number_of_processes
    s += "#SBATCH --cpus-per-task=1\n"
    s += "#SBATCH -p regular\n"
    s += "#SBATCH --output=%s\n" % output
    #s += "#SBATCH -w a013,a014,a015,a016\n"
    cmd = "source %s/source_this_on_davinci; " % this_dir
    #cmd += "which mpiexec; which mpirun; " 
    cmd += "mpiexec -n %i " % args.number_of_processes
    #cmd += "mpirun -n %i " % args.number_of_processes
    #cmd += "srun "
    cmd += "%s/../../hummingbird.py -b %s --lcls-run-number %i --port %i" % (this_dir, args.backend, args.lcls_run_number, port)
    if args.lcls_number_of_frames is not None:
        cmd += " --lcls-number-of-frames %i" % args.lcls_number_of_frames
    cmd += "\n"
    s += cmd
    
    with open(slurm, "w") as f:
        f.writelines(s)

    os.system("sbatch %s" % slurm)

    
