#!/usr/bin/env python
import sys, os
import argparse
import datetime
import csv
import subprocess

expdir = os.path.dirname(os.path.realpath(__file__)) + '/../'
sys.path.append(expdir)
from params import run_numbers

def parse_cmdline_args():
    parser = argparse.ArgumentParser(description='Hummingbird pre-processing submission script for slurm (Holography)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-r', '--run-number', metavar='run_number', 
                       help="run number, can also be a series of runs, for example: 1,3,5-10,20,22", type=str)
    group.add_argument('-s', '--run-type', metavar='run_type',
                       help='Run type, can be dark, background, cluster, holography', type=str)
    parser.add_argument('-n', '--number-of-frames', metavar='number_of_frames',
                        help="number of frames to be processed (optional)", type=int)
    parser.add_argument('-p', '--number-of-processes', metavar='number_of_processes',
                        help="number of MPI processes to be allocated for job", type=int, default=12)
    parser.add_argument('-e', '--env', metavar='env',
                        help="bash environment file that will be sourced before processing (optional)", type=str)
    parser.add_argument('-l', '--output-level', metavar='output_level',
                        help="output level defines how much data per event will be stored (default=3, 0: no output (\"dry-run\"), 1: only scalar output (hitscores, GMD values, etc.), 2: scalar output and TOF data, 3: scalar output, TOF data and images)", type=int, default=3)
    parser.add_argument('-t', '--hitscore-threshold', metavar='hitscore_threshold',
                        help="Hitscore threshold [if not provided read from CSV file]", type=int)
    parser.add_argument('-m', '--multiscore-threshold', metavar='multiscore_threshold',
                        help="Hitscore threshold [if not provided read from CSV file]", type=int)
    parser.add_argument('--sbatch-exclude', metavar='sbatch_exclude', type=str,
                        help="List of nodes to exclude, for example c001,a001,a003")
    parser.add_argument('--sbatch-partition', metavar='sbatch_exclude', type=str, 
                        help="SLURM partition that shall be used, for example regular")
    parser.add_argument('-x', '--run-locally', dest='run_locally', action='store_true')
    parser.add_argument('-k', '--skip-tof', dest='skip_tof', action='store_true')
    parser.add_argument('-o', '--outdir', metavar='outdir',
                        help="output directory different from default (optional)", type=str)

    
    if(len(sys.argv) == 1):
        parser.print_help()        
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_cmdline_args()

    if args.number_of_processes == 2:
        print "ERROR: The current implementation does not allow the number of processes be two. Change your configuration and try again. Abort."
        sys.exit(1)

    if args.env is None:
        env = "%s/source_this_file" % expdir
        print "WARNING: Using configuration specified in %s" % env
    else:
        env = args.env

    if args.run_type is not None:
        runs = run_numbers(expdir + 'params.csv', args.run_type)
    else:
        tmp = args.run_number
        runs = []
        for s in tmp.split(','):
            if "-" in s:
                rmin, rmax = s.split('-')
                runs += range(int(rmin), int(rmax)+1)
            else:
                runs += [int(s)]

    for run in runs:
        if args.outdir is None:
            # Path to rawdata
            base_path = '/asap3/flash/gpfs/bl1/2017/data/11001733/' 
            l_dir = base_path + "processed/hummingbird/log"
        else:
            l_dir = args.outdir + "/log"
        if not os.path.exists(l_dir):
            os.makedirs(l_dir)

        logfile = "%s/r%04i_ol%i.log" % (l_dir, run, args.output_level)
        slurm   = "%s/r%04i_ol%i.sh" % (l_dir, run, args.output_level)

        s = ""
        s += "#!/bin/sh\n"
        s += "#SBATCH --job-name=r%04i/%i\n" % (run, args.output_level)
        s += "#SBATCH --ntasks=%i\n" % args.number_of_processes
        s += "#SBATCH --ntasks-per-node=%i\n" % args.number_of_processes
        s += "#SBATCH --cpus-per-task=1\n"
        if args.sbatch_exclude is not None:
            s += "#SBATCH --exclude=%s\n" % args.sbatch_exclude
        s += "#SBATCH --exclude=max-p4-002\n"
        if args.sbatch_partition is not None:
            s += "#SBATCH --partition=%s\n" % args.sbatch_partition
        else:
            s += "#SBATCH --partition=all\n"
        s += "#SBATCH --reservation=beamline\n"
        s += "#SBATCH --time=2:00:00\n"
        s += "#SBATCH --output=%s\n" % logfile
        cmd = "cd %s\n" % expdir
        cmd += "source %s; " % env
        cmd += "mpirun -n %i -wd %s " % (args.number_of_processes, expdir)
        cmd += "./hummingbird.py -b conf_offline.py --run-nr %i " % (run)
        if args.hitscore_threshold is not None:
            cmd += " --hitscore-threshold %i" % args.hitscore_threshold
        if args.multiscore_threshold is not None:
            cmd += " --multiscore-threshold %i" % args.multiscore_threshold
        if args.number_of_frames is not None:
            cmd += " --nr-frames %i" %args.number_of_frames
        if args.outdir is not None:
            cmd += " --outdir %s" %args.outdir
        if args.skip_tof:
            cmd += " --skip-tof"
        cmd += " --output-level %i" % args.output_level
        s += cmd + "\n"
        with open(slurm, "w") as f:
            f.writelines(s)
        if not args.run_locally:
            cmd = "sbatch %s" % slurm
        else:
            cmd = "/bin/bash %s" % slurm
        os.system(cmd)
