# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""A plotting module for correlations and maps"""
import numpy as np
from scipy.sparse import lil_matrix

from hummingbird import ipc
from hummingbird.backend import Record

_existingPlots = {}

# Private classes / helper functions
# ----------------------------------
class _MeanMap:
    def __init__(self, name, xmin, xmax, ymin, ymax, step, localRadius, overviewStep, xlabel, ylabel, group=None):

        # Initialize local map
        self.localRadius = localRadius / float(step)
        self.step = step
        self.xrange = np.linspace(xmin, xmax, (xmax-xmin)/float(step)+1)
        self.yrange = np.linspace(ymin, ymax, (ymax-ymin)/float(step)+1)
        self.Nx = self.xrange.shape[0]
        self.Ny = self.yrange.shape[0]
        self.localXmin = self.xrange[self.Nx/2-self.localRadius]
        self.localXmax = self.xrange[self.Nx/2+self.localRadius]
        self.localYmin = self.yrange[self.Ny/2-self.localRadius]
        self.localYmax = self.yrange[self.Ny/2+self.localRadius]
        self.sparseSum  = lil_matrix((self.Ny, self.Nx), dtype=np.float32)
        self.sparseNorm = lil_matrix((self.Ny, self.Nx), dtype=np.float32)
        self.localMap   = np.zeros((2*self.localRadius+1, 2*self.localRadius+1))

        # Initialize overview map
        self.overviewXrange = np.linspace(xmin, xmax, (xmax-xmin)/float(overviewStep))
        self.overviewYrange = np.linspace(ymin, ymax, (ymax-ymin)/float(overviewStep))
        overviewNx = self.overviewXrange.shape[0]
        overviewNy = self.overviewYrange.shape[0]
        self.overviewMap = np.zeros((overviewNy, overviewNx))

        # Initialize plots
        self.counter = 0
        ipc.broadcast.init_data(name+' -> Overview', data_type='image', history_length=1, flipy=True, \
                                xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, xlabel=xlabel, ylabel=ylabel, group=group)
        ipc.broadcast.init_data(name+' -> Local',    data_type='image', history_length=1, flipy=True, \
                                xmin=self.localXmin, xmax=self.localXmax, \
                                ymin=self.localYmin, ymax=self.localYmax, xlabel=xlabel, ylabel=ylabel, group=group)

    def append(self, X, Y, Z, N):
        try:
            N = N.data
        except AttributeError:
            pass
        self.sparseSum[abs(self.yrange - Y.data).argmin(), abs(self.xrange - X.data).argmin()] += Z.data
        self.sparseNorm[abs(self.yrange - Y.data).argmin(), abs(self.xrange - X.data).argmin()] += N
        self.overviewMap[abs(self.overviewYrange - Y.data).argmin(), abs(self.overviewXrange - X.data).argmin()] += 1
        self.counter += 1

    def updateCenter(self, X, Y):
        self.center = (abs(self.yrange - Y.data).argmin(), abs(self.xrange - X.data).argmin())

    def updateLocalLimits(self):
        self.localXmin = max(self.xrange[max(self.center[1]-self.localRadius, 0)], self.xrange.min())
        self.localXmax = min(self.xrange[min(self.center[1]+self.localRadius, self.Nx-1)], self.xrange.max())
        self.localYmin = max(self.yrange[max(self.center[0]-self.localRadius, 0)], self.yrange.min())
        self.localYmax = min(self.yrange[min(self.center[0]+self.localRadius, self.Ny-1)], self.yrange.max())

    def gatherSumsAndNorms(self):
        if(ipc.mpi.slaves_comm):
            sparseSums  = ipc.mpi.slaves_comm.gather(self.sparseSum)
            sparseNorms = ipc.mpi.slaves_comm.gather(self.sparseNorm)
            if(ipc.mpi.is_main_slave()):
                self.sparseSum  = sparseSums[0]
                self.sparseNorm = sparseNorms[0]
                for i in sparseSums[1:]:
                    self.sparseSum  += i
                for n in sparseNorms[1:]:
                    self.sparseNorm += n

    def gatherOverview(self):
        ipc.mpi.sum(self.overviewMap)
                    
    def updateLocalMap(self):
        r = int(self.localRadius)
        c = self.center
        self.localSum  = self.sparseSum[c[0]-r: c[0]+r+1, c[1]-r:c[1]+r+1].toarray()
        self.localNorm = self.sparseNorm[c[0]-r: c[0]+r+1, c[1]-r:c[1]+r+1].toarray()
        visited = self.localNorm != 0
        self.localMap[visited] = self.localSum[visited] / self.localNorm[visited]

    def updateOverviewMap(self, X,Y):
        current = (abs(self.overviewYrange - Y.data).argmin(), abs(self.overviewXrange - X.data).argmin())
        visited = self.overviewMap[()] != 0
        self.overviewMap[visited] = 1
        self.overviewMap[current] = 2


# Public Plotting functions - Put new plotting functions here!
# ------------------------------------------------------------
#meanMaps = {}
def plotMeanMapDynamic(X, Y, Z, norm=1., msg='', update=100, xmin=0, xmax=100, ymin=0, ymax=100, step=10, \
                       localRadius=100, overviewStep=100, xlabel=None, ylabel=None, name=None, group=None):
    """Plotting the mean of parameter Z as a function of parameters X and Y.
    (Using a buffer in the backend).

    Args:
       :X(Record):     An event parameter e.g. Motor position in X
       :Y(Record):     An event parameter e.g. Motor position in Y
       :Z(Record):     An event parameter e.g. Intensity

    Kwargs:
        :norm(int):    Z is normalized by a given value, e.g. gmd (default = 1)
        :msg (str):    A message to be displayed in the plot
        :update (int): After how many new data points, an update is send to the frontend (default = 100)
        :xmin (int):   (default = 0)
        :xmax (int):   (default = 100)
        :ymin (int):   (default = 0)
        :ymax (int):   (default = 100)
        :step (int):   The resolution of the map in units of x,y (default = 10)
        :xlabel (str): (default = X.name) 
        :ylabel (str): (default = Y.name)
        :localRadius (int):  The radius of a square neighborehood around the current position (X.data, Y.data) (default = 100)
        :overviewStep (int): The resolution of the overiew map (default = 100)
    """
    if name is None:
        name = "%s(%s,%s)" %(Z.name, X.name, Y.name)
    if (not name in _existingPlots):
        if xlabel is None: xlabel = X.name
        if ylabel is None: ylabel = Y.name
        _existingPlots[name] = _MeanMap(name, xmin, xmax, ymin, ymax, step, localRadius, overviewStep, xlabel, ylabel, group=group)
    m = existingPlots[name]
    m.append(X, Y, Z, norm)
    if(not m.counter % update):
        m.gatherSumsAndNorms()
        m.gatherOverview()
        if(ipc.mpi.is_main_event_reader()):
            m.updateCenter(X, Y)
            m.updateLocalLimits()
            m.updateLocalMap()
            m.updateOverviewMap(X,Y)
            ipc.new_data(name+' -> Local', m.localMap, msg=msg, \
                         xmin=m.localXmin, xmax=m.localXmax, ymin=m.localYmin, ymax=m.localYmax)
            ipc.new_data(name+' -> Overview', m.overviewMap) 



correlations = {}
xArray = []
yArray = []
def plotCorrelation(X, Y, history=10000, name=None, group=None):
    """Plotting the correlation of two parameters X and Y over time.
    (Using a buffer in the backend).
    
    Args:
        :X(Record): An event parameter, e.g. hit rate
        :Y(Record): An event parameter, e.g. some motor position
    Kwargs: 
        :history(int): Buffer length
    """
    if name is None:
        name = "Corr(%s,%s)" %(X.name, Y.name)
    if (not name in _existingPlots):
        ipc.broadcast.init_data(name, history_length=100, group=group)
        _existingPlots[name] = True
    x,y = (X.data, Y.data)
    xArray.append(x)
    yArray.append(y)
    correlation = x*y/(np.mean(xArray)*np.mean(yArray))
    ipc.new_data(name, correlation)

def plotHeatmap(X, Y, xmin=0, xmax=1, xbins=10, ymin=0, ymax=1, ybins=10, name=None, group=None):
    """Plotting the heatmap of two parameters X and Y. Has been tested in MPI mode.
    (Using a buffer in the backend).

    Args:
        :X(Record): An event parameter, e.g. hit rate
        :Y(Record): An event parameter, e.g. some motor position
    Kwargs:
        :xmin(int):  default = 0
        :xmax(int):  default = 1
        :xbins(int): default = 10
        :ymin(int):  default = 0
        :ymax(int):  default = 1
        :ybins(int): default = 10
    """
    if name is None:
        name = "Heatmap(%s,%s)" %(X.name, Y.name)
    if not(name in _existingPlots):        
        # initiate (y, x) in 2D array to get correct orientation of image
        _existingPlots[name] = np.zeros((ybins, xbins), dtype=int)
        ipc.broadcast.init_data(name, data_type="image", group=group)
    deltaX = (xmax - float(xmin))/xbins
    deltaY = (ymax - float(ymin))/ybins
    nx = np.ceil((X.data - xmin)/deltaX)
    if (nx < 0):
        nx = 0
    elif (nx >= xbins):
        nx = xbins - 1
    ny = np.ceil((Y.data - ymin)/deltaY)
    if (ny < 0):
        ny = 0
    elif (ny >= ybins):
        ny = ybins - 1
    # assign y to row and x to col in 2D array
    _existingPlots[name][ny, nx] += 1
    current_heatmap = np.copy(heatmaps[name])
    ipc.mpi.sum(current_heatmap)
    if ipc.mpi.is_main_event_reader():
        ipc.new_data(name, current_heatmap[()])


def plotMeanMap(X,Y,Z, xmin=0, xmax=10, xbins=10, ymin=0, ymax=10, ybins=10, xlabel=None, ylabel=None, msg='', dynamic_extent=False, initial_reset=False, name=None, group=None):
    """Plotting the meanmap of Z as a function of two parameters X and Y.
    (No buffer in the backend).

    Args:
        :X(Record,float): An event parameter, e.g. injector position in x
        :Y(Record,float): An event parameter, e.g. injector position in y
        :Z(Record,float): Some metric, e.g. hit rate, size, etc...
    Kwargs:
        :xmin(int):  default = 0
        :xmax(int):  default = 10
        :xbins(int): default = 10
        :ymin(int):  default = 0
        :ymax(int):  default = 10
        :ybins(int): default = 10
        :name(str): The key that appears in the interface (default = MeanMap(X.name, Y.name))
        :xlabel(str): 
        :ylabel(str):
        :msg(msg):   Any message to be displayed in the plot
    """
    if name is None:
        name = "MeanMap(%s,%s,%s)" % (X.name, Y.name, Z.name)
    if (not name in _existingPlots):
        if xlabel is None: xlabel = X.name
        if ylabel is None: ylabel = Y.name
        ipc.broadcast.init_data(name, data_type='triple', history_length=1,
                                xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax,
                                xbins=xbins, ybins=ybins,
                                xlabel=xlabel, ylabel=ylabel, flipy=True,
                                dynamic_extent=dynamic_extent, initial_reset=initial_reset,
                                group=group)
        _existingPlots[name] = True
    x = X if not isinstance(X, Record) else X.data
    y = Y if not isinstance(Y, Record) else Y.data
    z = Z if not isinstance(Z, Record) else Z.data
    ipc.new_data(name, np.array([x, y, z]), msg=msg)

    
def plotScatter(X,Y, name=None, history=10000, xlabel=None, ylabel=None, group=None):
    """Plotting the scatter of two parameters X and Y.
    (No buffer in the backend).

    Args:
        :X(Record): An event parameter, e.g. injector position in x
        :Y(Record): An event parameter, e.g. injector position in y

    Kwargs:
        :name(str): The key that appears in the interface (default = MeanMap(X.name, Y.name))
        :xlabel(str): 
        :ylabel(str):
    """
    if name is None:
        name = "Scatter(%s,%s)" %(X.name, Y.name)
    if (not name in _existingPlots):
        if xlabel is None: xlabel = X.name
        if ylabel is None: ylabel = Y.name
        ipc.broadcast.init_data(name, data_type='tuple', history_length=history,
                                xlabel=xlabel, ylabel=ylabel, group=group)
        _existingPlots[name] = True
    ipc.new_data(name, np.array([X.data, Y.data]))

def plotScatterBg(X,Y, name=None, history=10000, xlabel=None, ylabel=None, bg_filename=None, bg_xmin=0., bg_xmax=1., bg_ymin=0., bg_ymax=0., bg_angle=0., group=None):
    """Plotting the scatter of two parameters X and Y.
    """
    if name is None:
        name = "ScatterBg(%s,%s)" %(X.name, Y.name)
    if (not name in _existingPlots):
        if xlabel is None: xlabel = X.name
        if ylabel is None: ylabel = Y.name
        ipc.broadcast.init_data(name, data_type='tuple', history_length=history,
                                xlabel=xlabel, ylabel=ylabel,
                                bg_filename=bg_filename,
                                bg_xmin=bg_xmin, bg_xmax=bg_xmax,
                                bg_ymin=bg_ymin, bg_ymax=bg_ymax,
                                bg_angle=bg_angle, group=group)
        _existingPlots[name] = True
    ipc.new_data(name, np.array([X.data, Y.data]))
    

def plotScatterColor(X,Y,Z, name=None, history=10000, xlabel=None, ylabel=None, zlabel=None, vmin=None, vmax=None, group=None):
    """Plotting the scatter of two parameters X and Y and use Z for color.
    (No buffer in the backend).

    Args:
        :X(Record): An event parameter, e.g. injector position in x
        :Y(Record): An event parameter, e.g. injector position in y
        :Z(Record): An event parameter, e.g. injector position in z

    Kwargs:
        :name(str): The key that appears in the interface (default = MeanMap(X.name, Y.name))
        :xlabel(str): 
        :ylabel(str):
    """
    if name is None:
        name = "ScatterColor(%s,%s)" %(X.name, Y.name)
    if (not name in _existingPlots):
        if xlabel is None: xlabel = X.name
        if ylabel is None: ylabel = Y.name
        if zlabel is None: zlabel = Z.name
        if vmin is None: vmin = 0
        if vmax is None: vmax = 1
        ipc.broadcast.init_data(name, data_type='triple', history_length=history,
                                xlabel=xlabel, ylabel=ylabel, zlabel=zlabel,
                                vmin=vmin, vmax=vmax, group=group)
        _existingPlots[name] = True
    ipc.new_data(name, np.array([X.data, Y.data, Z.data]))
