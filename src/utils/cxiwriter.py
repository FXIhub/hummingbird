# Adapted code from condor (https://github.com/mhantke/condor)
import numpy, os, time
import h5py

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
        msg = message
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

try:
    import mpi4py
    from mpi4py import MPI
    MPI_TAG_INIT   = 1 + 4353
    MPI_TAG_EXPAND = 2 + 4353
    MPI_TAG_READY  = 3 + 4353
    MPI_TAG_CLOSE  = 4 + 4353
    mpi = True
except:
    mpi = False

class CXIWriter:
    def __init__(self, filename, chunksize=2, compression=None, comm=None):
        self.comm = comm
        # This "if" avoids that processes that are not in the communicator (like the master process of hummingbird) interact with the file and block
        if not self._is_active():
            return
        self._ready = False
        self._filename = os.path.expandvars(filename)
        self._rank = -1 if self.comm is None else self.comm.rank
        self._i = -1 if self.comm is None else (self.comm.rank-1)
        self._i_max = -1
        self._initialised = False
        self._chunksize = chunksize
        self._N = chunksize
        self._create_dataset_kwargs = {}
        if compression is not None:
            self._create_dataset_kwargs["compression"] = compression
        self._fopen()

    def _fopen(self):
        if os.path.exists(self._filename):
            log_warning(logger, "(%i) File %s exists and is being overwritten" % (self._rank, self._filename))
        if self.comm is None:
            self._f = h5py.File(self._filename, "w")
        else:
            self._f = h5py.File(self._filename, "w", driver='mpio', comm=self.comm)

    def _fclose(self):
        self._f.close()

    def _is_active(self):
        return (self.comm is None or self.comm.rank != mpi4py.MPI.UNDEFINED)
            
    def write(self, D, i=None, flush=False):
        # WITHOUT MPI
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
                        time.sleep(1)
            else:
                self._expand_poll()
            self._write_without_iterate(D)
        # BOTH WITHOUT AND WITH MPI
        if self._i > self._i_max:
            self._i_max = self._i
        if flush:
            self._f.flush()
            
    def _expand_signal(self):
        log_debug(logger, "(%i) Send expand signal" % self._rank)
        for i in range(self.comm.size):
            self.comm.Send([numpy.array(self._i, dtype="i"), MPI.INT], dest=i, tag=MPI_TAG_EXPAND)

    def _expand_poll(self):
        L = []
        for i in range(self.comm.size): 
            if self.comm.Iprobe(source=i, tag=MPI_TAG_EXPAND):
                buf = numpy.empty(1, dtype="i")
                self.comm.Recv([buf, MPI.INT], source=i, tag=MPI_TAG_EXPAND)
                L.append(buf[0])
        if len(L) > 0:
            i_max = max(L)
            # Is expansion still needed or is the signal outdated?
            if i_max < self._N:
                log_debug(logger, "(%i) Expansion signal no longer needed (%i < %i)" % (self._rank, i_max, self._N))
                return
            # OK - There is a process that needs longer stacks, so we'll actually expand the stacks
            N_new = self._N * 2
            log_debug(logger, "(%i) Start stack expansion (%i >= %i) - new stack length will be %i" % (self._rank, i_max, self._N, N_new))
            self._expand_stacks(N_new)

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
                #log_debug(logger, "(%i) Writing to group %s" % (self._rank, group_prefix_new))
                self._write_without_iterate(D[k], group_prefix_new)
            else:
                name = group_prefix + k
                data = D[k]
                log_debug(logger, "(%i) Write to dataset %s at stack position %i" % (self._rank, name, self._i))
                if numpy.isscalar(data):
                    self._f[name][self._i] = data
                else:
                    self._f[name][self._i,:] = data[:]
                #log_debug(logger, "(%i) Write to dataset %s at stack position %i (completed)" % (self._rank, name, self._i))
                
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

    def _sync_i_max(self):
        sendbuf = numpy.array(self._i_max, dtype='i')
        recvbuf = numpy.empty(1, dtype='i')
        log_debug(logger, "(%i) Entering allreduce with maximum index %i" % (self._rank, self._i_max))
        self.comm.Allreduce([sendbuf, MPI.INT], [recvbuf, MPI.INT], op=MPI.MAX)
        self._i_max = recvbuf[0]
        
    def close(self):
        # This "if" avoids that processes that are not in the communicator (like the master process of hummingbird) interact with the file and block
        if not self._is_active():
            return
        if self.comm:
            if not self._initialised:
                log_and_raise_error(logger, "Cannot close uninitialised file. Every worker has to write at least one frame to file. Reduce your number of workers and try again.")
                exit(1)
            self._close_signal()
            while True:
                log_debug(logger, "(%i) Closing loop" % self._rank)
                self._expand_poll()
                self._update_ready()
                if self._ready:
                    break
                time.sleep(5.)
            self.comm.Barrier()
            log_debug(logger, "(%i) Sync stack length" % self._rank)
            self._sync_i_max()
            log_debug(logger, "(%i) Shrink stacks" % self._rank)
            self.comm.Barrier()
        self._shrink_stacks()
        if self.comm:
            self.comm.Barrier()
        log_debug(logger, "(%i) Closing file %s" % (self._rank, self._filename))
        self._fclose()
        log_info(logger, "(%i) File %s closed" % (self._rank, self._filename))
