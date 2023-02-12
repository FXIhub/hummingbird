try:
    import h5writer
except ImportError:
    print(100*"*")
    print("ERROR: For using the utils.cxiwriter.CXIWriter class please install the package \'h5writer\'.")
    print("\t $ pip install h5writer")
    print("\t (Github repository: https://github.com/mhantke/h5writer)")
    print(100*"*")
    exit(1)
    
from hummingbird import ipc

logger = h5writer.logger

if ipc.mpi.size <= 2:
    CXIWriter = h5writer.H5Writer
else:
    class CXIWriter(h5writer.H5WriterMPISW):
        def __init__(self, filename, chunksize=100, compression=None):
            h5writer.H5WriterMPISW.__init__(self, filename=filename, chunksize=chunksize, compression=compression, comm=ipc.mpi.slaves_comm)
