import numpy
import ipc
from scipy.sparse import lil_matrix

class MeanMap:
    def __init__(self, key, conf):
        xmin, xmax = conf["xmin"],  conf["xmax"]
        ymin, ymax = conf["ymin"],  conf["ymax"]
        step   = conf["step"]
        self.radius = conf["radius"]
        gridstep = conf["gridstep"]
        
        self.xrange = numpy.linspace(xmin, xmax, (xmax-xmin)/float(step))
        self.yrange = numpy.linspace(ymin, ymax, (ymax-ymin)/float(step))
        Nx = self.xrange.shape[0]
        Ny = self.yrange.shape[0]
        self.localXmin = self.xrange[Nx/2-self.radius]
        self.localXmax = self.xrange[Nx/2+self.radius+1]
        self.localYmin = self.yrange[Ny/2-self.radius]
        self.localYmax = self.yrange[Ny/2+self.radius+1]
        self.integralMap  = lil_matrix((Ny, Nx), dtype=numpy.float32)
        self.normMap      = lil_matrix((Ny, Nx), dtype=numpy.float32)
        self.localMeanMap = numpy.zeros((2*self.radius, 2*self.radius))

        self.gridxrange = numpy.linspace(xmin, xmax, (xmax-xmin)/float(gridstep))
        self.gridyrange = numpy.linspace(ymin, ymax, (ymax-ymin)/float(gridstep))
        gridNx = self.gridxrange.shape[0]
        gridNy = self.gridyrange.shape[0]
        #self.gridIntegralMap = numpy.zeros((gridNy, gridNx))
        #self.gridNormMap     = numpy.zeros((gridNy, gridNx))
        self.gridMap = numpy.zeros((gridNy, gridNx))
        
        self.counter    = 0
        ipc.broadcast.init_data(key+'overview', data_type='image', xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, xlabel=conf["xlabel"], ylabel=conf["ylabel"], history_length=1, flipy=True)
        ipc.broadcast.init_data(key+'local', data_type='image', xmin=self.localXmin, xmax=self.localXmax, ymin=self.localYmin, ymax=self.localYmax, xlabel=conf["xlabel"], ylabel=conf["ylabel"], history_length=1, flipy=True)

    def append(self, X, Y, I, N):
        self.integralMap[abs(self.yrange - Y.data).argmin(), abs(self.xrange - X.data).argmin()] += I
        self.normMap[abs(self.yrange - Y.data).argmin(), abs(self.xrange - X.data).argmin()] += N
        #self.gridIntegralMap[abs(self.gridyrange - Y.data).argmin(), abs(self.gridxrange - X.data).argmin()] += I
        #self.gridNormMap[abs(self.gridyrange - Y.data).argmin(), abs(self.gridxrange - X.data).argmin()] += N
        self.gridMap[abs(self.gridyrange - Y.data).argmin(), abs(self.gridxrange - X.data).argmin()] += 1
        self.counter += 1

    def update_center(self, X, Y):
        self.center = (abs(self.yrange - Y.data).argmin(), abs(self.xrange - X.data).argmin())

    def update_local_limits(self):
        self.localXmin = max(self.xrange[self.center[1]-self.radius], self.xrange.min())
        self.localXmax = min(self.xrange[self.center[1]+self.radius+1], self.xrange.max())
        self.localYmin = max(self.yrange[self.center[0]-self.radius], self.yrange.min())
        self.localYmax = min(self.yrange[self.center[0]+self.radius+1], self.yrange.max())

    def update_local_maps(self):
        rad = self.radius
        self.localIntegralMap = self.integralMap[self.center[0]-rad: self.center[0]+rad+1, self.center[1]-rad:self.center[1]+rad+1].toarray()
        self.localNormMap     = self.normMap[self.center[0]-rad: self.center[0]+rad+1, self.center[1]-rad:self.center[1]+rad+1].toarray()
        self.localMeanMap = numpy.zeros(self.localIntegralMap.shape)
        visited = self.localNormMap != 0
        self.localMeanMap[visited] = self.localIntegralMap[visited] / self.localNormMap[visited]

    def update_gridmap(self, X,Y):
        current = (abs(self.gridyrange - Y.data).argmin(), abs(self.gridxrange - X.data).argmin())
        visited = self.gridMap != 0
        self.gridMap[visited] = 1
        self.gridMap[current] = 2

meanMaps = {}
def plotMeanMap(key, conf, paramX, paramY, paramZ, normZ):
    if not key in meanMaps:
        meanMaps[key] = MeanMap(key,conf)
    m = meanMaps[key]
    m.append(paramX, paramY, paramZ, normZ)
    if(not m.counter % conf["updateRate"]):
        m.update_center(paramX, paramY)
        m.update_local_limits()
        m.update_local_maps()
        m.update_gridmap(paramX,paramY)        
        ipc.new_data(key+'overview', m.gridMap) 
        ipc.new_data(key+'local', m.localMeanMap, xmin=m.localXmin, xmax=m.localXmax, ymin=m.localYmin, ymax=m.localYmax)
