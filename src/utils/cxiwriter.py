# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
# Code adapted from http://github.com/mhantke/condor
# --------------------------------------------------
import numpy, h5py, os
import time
import log
import logging,inspect
logger = logging.getLogger(__name__)

log_and_raise_error = lambda logger, message: log(logger, message, lvl="ERROR", exception=RuntimeError, rollback=2)
log_warning = lambda logger, message: log(logger, message, lvl="WARNING", exception=None, rollback=2)
log_info = lambda logger, message: log(logger, message, lvl="INFO", exception=None, rollback=2)
log_debug = lambda logger, message: log(logger, message, lvl="DEBUG", exception=None, rollback=2)

def log(logger, message, lvl, exception=None, rollback=1):
    logcalls = {"ERROR": logger.error,
                "WARNING": logger.warning,
                "DEBUG": logger.debug,
                "INFO": logger.info}
    if lvl not in logcalls:
        print "%s is an invalid logger level." % lvl
        sys.exit(1)
    logcall = logcalls[lvl]
    # This should maybe go into a handler
    if (logger.getEffectiveLevel() >= logging.INFO) or rollback is None:
        # Short output
        msg = "%s" % message
    else:
        # Detailed output only in debug mode
        func = inspect.currentframe()
        for r in range(rollback):
            # Rolling back in the stack, otherwise it would be this function
            func = func.f_back
        code = func.f_code
        msg = "%s\n\t=> in \'%s\' function \'%s\' [%s:%i]" % (message,
                                                              func.f_globals["__name__"],
                                                              code.co_name, 
                                                              code.co_filename, 
                                                              code.co_firstlineno)
    logcall("%s:\t%s" % (lvl,msg))
    if exception is not None:
        raise exception(message)

from mpi4py import MPI
MPI_TAG_INIT   = 1 + 4353
MPI_TAG_EXPAND = 2 + 4353
MPI_TAG_READY  = 3 + 4353
MPI_TAG_CLOSE  = 4 + 4353

class CXIWriter:
    def __init__(self, filename, chunksize=2, gzip_compression=False):
        self._filename = os.path.expandvars(filename)
        if os.path.exists(filename):
            log.log_warning(logger, "File %s exists and is being overwritten" % filename)
            os.system("rm %s" % filename)
        self._f = h5py.File(filename, "w")
        self._i = 0
        self._chunksize = chunksize
        self._create_dataset_kwargs = {}
        if gzip_compression:
            self._create_dataset_kwargs["compression"] = "gzip"

    def write(self, D):
        self._write_without_iterate(D)
        self._i += 1
        
    def _write_without_iterate(self, D, group_prefix="/"):
        for k in D.keys():
            if isinstance(D[k],dict):
                group_prefix_new = group_prefix + k + "/"
                log.log_debug(logger, "Writing group %s" % group_prefix_new)
                if k not in self._f[group_prefix]:
                    self._f.create_group(group_prefix_new)
                self._write_without_iterate(D[k], group_prefix_new)
            else:
                name = group_prefix + k
                log.log_debug(logger, "Writing dataset %s" % name)
                data = D[k]
                if k not in self._f[group_prefix]:
                    if numpy.isscalar(data):
                        maxshape = (None,)
                        shape = (self._chunksize,)
                        dtype = numpy.dtype(type(data))
                        if dtype == "S":
                            dtype = h5py.new_vlen(str)
                        axes = "experiment_identifier:value"
                    else:
                        data = numpy.asarray(data)
                        try:
                            h5py.h5t.py_create(data.dtype, logical=1)
                        except TypeError:
                            log.log_warning(logger, "Could not save dataset %s. Conversion to numpy array failed" % name)
                            continue
                        maxshape = tuple([None]+list(data.shape))
                        shape = tuple([self._chunksize]+list(data.shape))
                        dtype = data.dtype
                        ndim = data.ndim
                        axes = "experiment_identifier"
                        if ndim == 1: axes = axes + ":x"
                        elif ndim == 2: axes = axes + ":y:x"
                        elif ndim == 3: axes = axes + ":z:y:x"
                    log.log_debug(logger, "Create dataset %s [shape=%s, dtype=%s]" % (name,str(shape),str(dtype)))
                    self._f.create_dataset(name, shape, maxshape=maxshape, dtype=dtype, **self._create_dataset_kwargs)
                    self._f[name].attrs.modify("axes",[axes])
                if self._f[name].shape[0] <= self._i:
                    if numpy.isscalar(data):
                        data_shape = []
                    else:
                        data_shape = data.shape
                    new_shape = tuple([self._chunksize*(self._i/self._chunksize+1)]+list(data_shape))
                    log.log_debug(logger, "Resize dataset %s [old shape: %s, new shape: %s]" % (name,str(self._f[name].shape),str(new_shape)))
                    self._f[name].resize(new_shape)
                log.log_debug(logger, "Write to dataset %s at stack position %i" % (name, self._i))
                if numpy.isscalar(data):
                    self._f[name][self._i] = data
                else:
                    self._f[name][self._i,:] = data[:]

    def _shrink_stacks(self, group_prefix="/"):
        for k in self._f[group_prefix].keys():
            name = group_prefix + k
            if isinstance(self._f[name], h5py.Dataset):
                log.log_debug(logger, "Shrinking dataset %s to stack length %i" % (name, self._i))
                s = list(self._f[name].shape)
                s.pop(0)
                s.insert(0, self._i)
                s = tuple(s)
                self._f[name].resize(s)
            else:
                self._shrink_stacks(name + "/")
                    
    def close(self):
        self._shrink_stacks()
        log.log_debug(logger, "Closing file %s" % self._filename)
        self._f.close()

class CXIWriter2:
    def __init__(self, filename, chunksize=2, compression=None, comm=None):
        self._ready = False
        self._filename = os.path.expandvars(filename)
        self.comm = comm
        self._rank = -1 if self.comm is None else self.comm.rank
        self._i = -1
        self._i_max = -1
        self._initialised = False
        self._chunksize = chunksize
        self._N = chunksize
        self._create_dataset_kwargs = {}
        if compression is not None:
            self._create_dataset_kwargs["compression"] = compression
        self._fopen()
        self.comm = comm

    def _fopen(self):
        if os.path.exists(self._filename):
            log_warning(logger, "(%i) File %s exists and is being overwritten" % (self._rank, self._filename))
        if self.comm is None:
            self._f = h5py.File(self._filename, "w")
        else:
            self._f = h5py.File(self._filename, "w", driver='mpio', comm=self.comm)

    def _fclose(self):
        if self._f is not None:
            self._f.close()
            
    def write(self, D, i=None, flush=False):
        # NO MPI
        if self.comm is None:
            if not self._initialised:
                self._initialise_tree(D)
                self._initialised = True
            self._i = (self._i + 1) if i is None else i
            if self._i >= (self._N-1):
                self._expand_stacks(self._N * 2)
            self._write_without_iterate(D)
        # WITH MPI
        else:
            if not self._initialised:
                self._initialise_tree(D)
                self._initialised = True
            self._i = (self._i + 1) if i is None else i
            if self._i > (self._N-1):
                while self._i > (self._N-1):
                    self._expand_signal()
                    self._expand_poll()
                    if self._i > (self._N-1):
                        time.sleep(0.1)
            else:
                self._expand_poll()
            self._write_without_iterate(D)
        # NO/WITH MPI
        if self._i > self._i_max:
            self._i_max = self._i
        if flush:
            self._f.flush()
            
    def _expand_signal(self):
        for i in range(self.comm.size):
            # Send out signal
            self.comm.Send([numpy.array(self._i, dtype="i"), MPI.INT], dest=i, tag=MPI_TAG_EXPAND)
            log_debug(logger, "(%i) Send expand signal" % self._rank)

    def _expand_poll(self):
        if self.comm.Iprobe(source=MPI.ANY_SOURCE, tag=MPI_TAG_EXPAND):
            buf = numpy.empty(1, dtype="i")
            self.comm.Recv([buf, MPI.INT], source=MPI.ANY_SOURCE, tag=MPI_TAG_EXPAND)
            # Is expansion still needed or is the signal outdated?
            if buf[0] < self._N:
                return                
            sendbuf = numpy.array(self._i, dtype='i')
            recvbuf = numpy.empty(1, dtype='i')
            self.comm.Allreduce(sendbuf, recvbuf, MPI.MAX)
            i_max = recvbuf[0]
            if i_max >= self._N:
                self._expand_stacks(self._N * 2)

    def _close_signal(self):
        if self._rank == 0:
            self._busy_clients    = [i for i in range(self.comm.size) if i != self._rank]
            self._closing_clients = [i for i in range(self.comm.size) if i != self._rank]
            self._signal_sent     = False
        else:
            self.comm.Isend([numpy.array(self._rank, dtype="i"), MPI.INT], dest=0, tag=MPI_TAG_READY)
            
    def _update_ready(self):
        if self._rank == 0:
            if (len(self._busy_clients) > 0):
                for i in self._busy_clients:
                    if self.comm.Iprobe(source=i, tag=MPI_TAG_READY):
                        self._busy_clients.remove(i)
            else:
                if not self._signal_sent:
                    for i in self._closing_clients:
                        # Send out signal
                        self.comm.Isend([numpy.array(-1, dtype="i"), MPI.INT], dest=i, tag=MPI_TAG_CLOSE)
                    self._signal_sent = True
                # Collect more confirmations
                for i in self._closing_clients:
                    if self.comm.Iprobe(source=i, tag=MPI_TAG_CLOSE):
                        self._closing_clients.remove(i)
            self._ready = len(self._closing_clients) == 0
        else:
            if self.comm.Iprobe(source=0, tag=MPI_TAG_CLOSE):
                self.comm.Isend([numpy.array(1, dtype="i"), MPI.INT], dest=0, tag=MPI_TAG_CLOSE)
                self._ready = True
        log_debug(logger, "(%i) Ready status updated: %i" % (self._rank, self._ready))
        
    def _initialise_tree(self, D, group_prefix="/"):
        keys = D.keys()
        keys.sort()
        for k in keys:
            if isinstance(D[k],dict):
                group_prefix_new = group_prefix + k + "/"
                log_debug(logger, "(%i) Creating group %s" % (self._rank, group_prefix_new))
                self._f.create_group(group_prefix_new)
                self._initialise_tree(D[k], group_prefix=group_prefix_new)
            else:
                name = group_prefix + k
                log_debug(logger, "(%i) Creating dataset %s" % (self._rank, name))
                data = D[k]
                self._create_dataset(data, name)
                    
    def _write_without_iterate(self, D, group_prefix="/"):
        keys = D.keys()
        keys.sort()
        for k in keys:
            if isinstance(D[k],dict):
                group_prefix_new = group_prefix + k + "/"
                log_debug(logger, "(%i) Writing group %s" % (self._rank, group_prefix_new))
                self._write_without_iterate(D[k], group_prefix_new)
            else:
                name = group_prefix + k
                data = D[k]
                log_debug(logger, "(%i) Write to dataset %s at stack position %i" % (self._rank, name, self._i))
                if numpy.isscalar(data):
                    self._f[name][self._i] = data
                    #self._f[name][0] = data
                else:
                    self._f[name][self._i,:] = data[:]
                    #self._f[name][0,:] = data[:]
                log_debug(logger, "(%i) Writing to dataset %s at stack position %i completed" % (self._rank, name, self._i))
                
    def _create_dataset(self, data, name):
        if numpy.isscalar(data):
            maxshape = (None,)
            shape = (self._chunksize,)
            dtype = numpy.dtype(type(data))
            if dtype == "S":
                dtype = h5py.new_vlen(str)
            axes = "experiment_identifier:value"
        else:
            data = numpy.asarray(data)
            try:
                h5py.h5t.py_create(data.dtype, logical=1)
            except TypeError:
                log_warning(logger, "(%i) Could not save dataset %s. Conversion to numpy array failed" % (self._rank, name))
                return 1
            maxshape = tuple([None]+list(data.shape))
            shape = tuple([self._chunksize]+list(data.shape))
            dtype = data.dtype
            ndim = data.ndim
            axes = "experiment_identifier"
            if ndim == 1: axes = axes + ":x"
            elif ndim == 2: axes = axes + ":y:x"
            elif ndim == 3: axes = axes + ":z:y:x"
        log_debug(logger, "(%i) Create dataset %s [shape=%s, dtype=%s]" % (self._rank, name, str(shape), str(dtype)))
        self._f.create_dataset(name, shape, maxshape=maxshape, dtype=dtype, **self._create_dataset_kwargs)
        self._f[name].attrs.modify("axes",[axes])
        return 0
                    
    def _expand_stacks(self, N, group_prefix="/"):
        keys = self._f[group_prefix].keys()
        keys.sort()
        for k in keys:
            name = group_prefix + k
            if isinstance(self._f[name], h5py.Dataset):
                if not (name[1:].startswith("__") and name.endswith("__")):
                    self._expand_stack(N, name)
            else:
                self._expand_stacks(N, name + "/")
            
    def _expand_stack(self, N, name):
        new_shape = list(self._f[name].shape)
        new_shape[0] = N
        new_shape = tuple(new_shape)
        log_info(logger, "(%i) Expand dataset %s [old shape: %s, new shape: %s]" % (self._rank, name, str(self._f[name].shape), str(new_shape)))
        self._f[name].resize(new_shape)
        self._N = N
            
    def _shrink_stacks(self, group_prefix="/"):
        N = self._i_max + 1
        keys = self._f[group_prefix].keys()
        keys.sort()
        for k in keys:
            name = group_prefix + k
            if isinstance(self._f[name], h5py.Dataset):
                if not (name[1:].startswith("__") and name.endswith("__")):
                    if N < 1:
                        log_warning(logger, "(%i) Cannot reduce dataset %s to length %i" % (self._rank, name, N))
                        return
                    log_debug(logger, "(%i) Shrinking dataset %s to stack length %i" % (self._rank, name, N))
                    s = list(self._f[name].shape)
                    s.pop(0)
                    s.insert(0, self._i_max+1)
                    s = tuple(s)
                    self._f[name].resize(s)
            else:
                self._shrink_stacks(name + "/")

    def _update_i_max(self):
        sendbuf = numpy.array(self._i_max, dtype='i')
        recvbuf = numpy.empty(1, dtype='i')
        log_debug(logger, "(%i) Entering allreduce with maximum index %i" % (self._rank, self._i_max))
        self.comm.Allreduce([sendbuf, MPI.INT], [recvbuf, MPI.INT], op=MPI.MAX)
        log_debug(logger, "(%i) Maximum index is %i (A)" % (self._rank, self._i_max))
        self._i_max = recvbuf[0]
        log_debug(logger, "(%i) Maximum index is %i (B)" % (self._rank, self._i_max))
        
    def close(self):
        if self.comm:
            self._close_signal()
            while True:
                log_debug(logger, "(%i) Closing loop (A)" % self._rank)
                self._expand_poll()
                log_debug(logger, "(%i) Closing loop (B)" % self._rank)
                self._update_ready()
                if self._ready:
                    break
                log_debug(logger, "(%i) Closing loop (C)" % self._rank)
                time.sleep(0.1)
            self.comm.Barrier()
            log_debug(logger, "(%i) Sync reduce stack length" % self._rank)
            self._update_i_max()
            log_debug(logger, "(%i) Shrink stacks" % self._rank)
            self.comm.Barrier()
        self._shrink_stacks()
        if self.comm:
            self.comm.Barrier()
        log_debug(logger, "(%i) Closing file %s" % (self._rank, self._filename))
        self._fclose()

        
