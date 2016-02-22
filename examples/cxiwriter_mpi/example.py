from mpi4py import MPI
import numpy
import sys, os
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../../src/analysis")
import cxiwriter
print cxiwriter.__file__

import logging, sys
h = logging.StreamHandler(sys.stdout)
cxiwriter.logger.setLevel("INFO")
cxiwriter.logger.addHandler(h)

W = cxiwriter.CXIWriter('test.cxi', comm=MPI.COMM_WORLD, chunksize=10)

counter = 0

for i in range(5):

    data = numpy.random.rand(4,4)

    if data.mean() > 0.0:

        out = {}
        out["test"] = data

        W.write(out, i=MPI.COMM_WORLD.rank*counter)

        counter += 1
        
W.close()


