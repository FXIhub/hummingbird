"""A plotting module for correlations and maps"""
import numpy as np
import ipc
from scipy.sparse import lil_matrix

# Private classes / helper functions
# ----------------------------------
class _MeanMap:
    def __init__(self, plotid, xmin, xmax, ymin, ymax, step, localRadius, overviewStep, xlabel, ylabel):

        # Initialize local map
        self.localRadius = localRadius
        self.xrange = np.linspace(xmin, xmax, (xmax-xmin)/float(step))
        self.yrange = np.linspace(ymin, ymax, (ymax-ymin)/float(step))
        Nx = self.xrange.shape[0]
        Ny = self.yrange.shape[0]
        self.localXmin = self.xrange[Nx/2-self.localRadius]
        self.localXmax = self.xrange[Nx/2+self.localRadius+1]
        self.localYmin = self.yrange[Ny/2-self.localRadius]
        self.localYmax = self.yrange[Ny/2+self.localRadius+1]
        self.sparseSum  = lil_matrix((Ny, Nx), dtype=np.float32)
        self.sparseNorm = lil_matrix((Ny, Nx), dtype=np.float32)
        self.localMap   = np.zeros((2*self.localRadius, 2*self.localRadius))

        # Initialize overview map
        self.overviewXrange = np.linspace(xmin, xmax, (xmax-xmin)/float(overviewStep))
        self.overviewYrange = np.linspace(ymin, ymax, (ymax-ymin)/float(overviewStep))
        overviewNx = self.overviewXrange.shape[0]
        overviewNy = self.overviewYrange.shape[0]
        self.overviewMap = np.zeros((overviewNy, overviewNx))

        # Initialize plots
        self.counter    = 0
        ipc.broadcast.init_data(plotid+' -> overview', data_type='image', history_length=1, flipy=True, \
                                xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, xlabel=xlabel, ylabel=ylabel)
        ipc.broadcast.init_data(plotid+' -> local',    data_type='image', history_length=1, flipy=True, \
                                xmin=self.localXmin, xmax=self.localXmax, \
                                ymin=self.localYmin, ymax=self.localYmax, xlabel=xlabel, ylabel=ylabel)

    def append(self, X, Y, Z, N):
        self.sparseSum[abs(self.yrange - Y.data).argmin(), abs(self.xrange - X.data).argmin()] += Z
        self.sparseNorm[abs(self.yrange - Y.data).argmin(), abs(self.xrange - X.data).argmin()] += N
        self.overview[abs(self.overviewYrange - Y.data).argmin(), abs(self.overviewXrange - X.data).argmin()] += 1
        self.counter += 1

    def updateCenter(self, X, Y):
        self.center = (abs(self.yrange - Y.data).argmin(), abs(self.xrange - X.data).argmin())

    def updateLocalLimits(self):
        self.localXmin = max(self.xrange[self.center[1]-self.localRadius],   self.xrange.min())
        self.localXmax = min(self.xrange[self.center[1]+self.localRadius+1], self.xrange.max())
        self.localYmin = max(self.yrange[self.center[0]-self.localRadius],   self.yrange.min())
        self.localYmax = min(self.yrange[self.center[0]+self.localRadius+1], self.yrange.max())

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

    def updateLocalMap(self):
        r = self.localRadius
        c = self.center
        self.localSum  = self.sparseSum[c[0]-r: c[0]+r+1, c[1]-r:c[1]+r+1].toarray()
        self.localNorm = self.sparseNorm[c[0]-r: c[0]+r+1, c[1]-r:c[1]+r+1].toarray()
        visited = self.localNorm != 0
        self.localMap[visited] = self.localSum[visited] / self.localNorm[visited]

    def updateOverviewMap(self, X,Y):
        current = (abs(self.overviewYrange - Y.data).argmin(), abs(self.overviewXrange - X.data).argmin())
        visited = self.overviewMap != 0
        self.overviewMap[visited] = 1
        self.overviewMap[current] = 2


# Public Plotting functions - Put new plotting functions here!
# ------------------------------------------------------------
meanMaps = {}
def plotMeanMap(X, Y, Z, norm=1., msg='', update=100, xmin=0, xmax=100, ymin=0, ymax=100, step=10, \
                localRadius=100, overviewStep=100, xlabel=None, ylabel=None):
    """Plotting the mean of parameter Z as a function of parameters X and Y.

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
        :step (int):   The resolution of the map (default = 10)
        :xlabel (str): (default = X.name) 
        :ylabel (str): (default = Y.name)
        :localRadius (int):  The radius of a square neighborehood around the current position (X.data, Y.data) (default = 100)
        :overviewStep (int): The resolution of the overiew map (default = 100)
    """
    plotid = "%s(%s,%s)" %(Z.name, X.name, Y.name)
    if (not plotid in meanMaps):
        if xlabel is None: xlabel = X.name
        if ylabel is None: ylabel = Y.name
        meanMaps[plotid] = _MeanMap(plotid, xmin, xmax, ymin, ymax, xlabel, ylabel, radius, step, gridstep)
    m = meanMaps[plotid]
    m.append(X, Y, Z, norm)
    if(not m.counter % update):
        m.gatherSumsAndNorms()
        if(ipc.mpi.size == 1 or ipc.mpi.is_main_slave()):
            m.updateCenter(X, Y)
            m.updateLocalLimits()
            m.updateLocalMap()
            m.updateOverviewMap(X,Y)
            ipc.new_data(plotid+' -> Local', m.localMap, msg=msg, \
                         xmin=m.localXmin, xmax=m.localXmax, ymin=m.localYmin, ymax=m.localYmax)
            ipc.new_data(plotid+' -> Overview', m.overviewMap) 



correlations = {}
xArray = []
yArray = []
def plotCorrelation(X, Y, history=100):
    """Plotting the correlation of two parameters X and Y over time.
    
    Args:
        :X(Record): An event parameter, e.g. hit rate
        :Y(Record): An event parameter, e.g. some motor position
    Kwargs: 
        :history(int): Buffer length
    """
    plotid = "Corr(%s,%s)" %(X.name, Y.name)
    if (not plotid in correlations):
        ipc.broadcast.init_data(plotid, history_length=100)
        correlations[plotid] = True
    x,y = (X.data, Y.data)
    xArray.append(x)
    yArray.append(y)
    correlation = x*y/(np.mean(xArray)*np.mean(yArray))
    ipc.new_data(plotid, correlation)

heatmaps = {}
def plotHeatmap(X, Y, xmin=0, xmax=1, xbins=10, ymin=0, ymax=1, ybins=10):
    """Plotting the heatmap of two parameters X and Y.

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
    plotid = "Heatmap(%s,%s)" %(X.name, Y.name)
    if not(plotid in heatmaps):        
        # initiate (y, x) in 2D array to get correct orientation of image
        heatmaps[plotid] = np.zeros((ybins, xbins), dtype=int)
        ipc.broadcast.init_data(plotid, data_type="image")
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
    heatmaps[plotid][ny, nx] += 1
    ipc.new_data(plotid, heatmaps[plotid])
