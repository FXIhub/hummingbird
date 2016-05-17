#!/usr/bin/env python

import sys, os
import argparse
import datetime

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

    user = os.environ["USER"]
    run = "r%04i" % args.lcls_run_number
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    root_dir = "/scratch/fhgfs/%s/hummingbird" % user
    if not os.path.isdir(root_dir):
        os.system("mkdir -p %s" % root_dir)
    out_dir = "%s/%s_%s" % (root_dir, run, timestamp)
    link_out_dir = "%s/%s_current" % (root_dir, run)

    os.system("mkdir %s" % out_dir)
    os.system("ln -sfn %s_%s %s" % (run, timestamp, link_out_dir))
    
    slurm = "%s/%s.sh" % (out_dir, run)
    output = "%s/%s.out" % (out_dir, run)
    port = int(now.strftime("1%M%S")) + args.lcls_run_number
    
    s = []
    s += "#!/bin/sh\n"
    s += "#SBATCH --job-name=HB_r%04i\n" % args.lcls_run_number
    s += "#SBATCH --ntasks=%i\n" % args.number_of_processes
    s += "#SBATCH --cpus-per-task=1\n"
    s += "#SBATCH -p low\n"
    s += "#SBATCH --output=%s\n" % output
    s += "#SBATCH --exclude=c002\n"
    cmd = "source %s/source_this_on_davinci; " % this_dir
    #cmd += "ulimit -c unlimited; "
    #cmd += "export OMPI_MCA_btl_openib_use_eager_rdma=0; "
    cmd += "mpirun -n %i -wd %s " % (args.number_of_processes, out_dir)
    #cmd += "--mca btl_openib_connect_udcm_timeout 5000000 "
    #cmd += "--mca btl ^openib "
    cmd += "%s/../../hummingbird.py -b %s --lcls-run-number %i --port %i" % (this_dir, args.backend, args.lcls_run_number, port)
    if args.lcls_number_of_frames is not None:
        cmd += " --lcls-number-of-frames %i" % args.lcls_number_of_frames
    cmd += "\n"
    s += cmd
    
    with open(slurm, "w") as f:
        f.writelines(s)
        
    os.system("sbatch %s" % (slurm))

    
