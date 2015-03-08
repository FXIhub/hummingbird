import ipc
import numpy
from backend import Backend
from scipy.sparse import lil_matrix
from numpy.linalg import solve, norm

counter = []
def counting(hit):
    if hit: counter.append(True)
    else: counter.append(False)
    return counter

def countLitPixels(image):
    hitscore = (image > Backend.state["aduThreshold"]).sum()
    return hitscore > Backend.state["hitscoreMinCount"], hitscore

def plotHitscore(hitscore):
    ipc.new_data("Hitscore", hitscore)

class MeanPhotonMap:
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
        self.localMeanMap      = numpy.zeros((2*self.radius, 2*self.radius))

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
        self.localXmin = self.xrange[self.center[1]-self.radius]
        self.localXmax = self.xrange[self.center[1]+self.radius+1]
        self.localYmin = self.yrange[self.center[0]-self.radius]
        self.localYmax = self.yrange[self.center[0]+self.radius+1]

    def update_local_maps(self):
        rad = self.radius
        self.localIntegralMap = self.integralMap[self.center[0]-rad: self.center[0]+rad+1, self.center[1]-rad:self.center[1]+rad+1].toarray()
        self.localNormMap     = self.normMap[self.center[0]-rad: self.center[0]+rad+1, self.center[1]-rad:self.center[1]+rad+1].toarray()
        visited = self.localNormMap != 0
        self.localMeanMap[visited] = self.localIntegralMap[visited] / self.localNormMap[visited]

    def update_gridmap(self, X,Y):
        current = (abs(self.gridyrange - Y.data).argmin(), abs(self.gridxrange - X.data).argmin())
        visited = self.gridMap != 0
        self.gridMap[visited] = 1
        self.gridMap[current] = 2

photonMaps = {}
def plotMeanPhotonMap(key, conf, nrPhotons, paramX, paramY, pulseEnergy):
    if not key in photonMaps:
        photonMaps[key] = MeanPhotonMap(key,conf)
    m = photonMaps[key]
    m.append(paramX, paramY, nrPhotons, pulseEnergy)
    if(not m.counter % conf["updateRate"]):
        m.update_center(paramX, paramY)
        m.update_local_limits()
        m.update_local_maps()
        m.update_gridmap(paramX,paramY)
        
        ipc.new_data(key+'overview', m.gridMap) 
        ipc.new_data(key+'local', m.localMeanMap, xmin=m.localXmin, xmax=m.localXmax, ymin=m.localYmin, ymax=m.localYmax)
        

        #center = (abs(m.photonMapY - paramY.data).argmin(), abs(m.photonMapX - paramX.data).argmin())
        #photonMap = grab_array(m.photonMap, center, conf["radius"])
        #gasMap = grab_array(m.gasMap, center, conf["radius"])

        
        
        #meanMap = numpy.zeros(photonMap.shape)
        #meanMap[visited] = photonMap[visited] / gasMap[visited]
        #print m.eventMap.shape
        #Nx = 100
        #Ny = 100
        #N = numpy.prod(m.eventMap.shape)  / ((conf["radius"])**2)
        #print N
        #Nx,Ny = 2*[int(numpy.sqrt(N))]
        #print Nx,Ny
        #print m.photonMapY[center[0]], m.photonMapX[center[1]]
        #print m.eventMap[center[0],center[1]]
        #for j in range(Ny):
        #    for i in range(Nx):
        #        m.eventMapDown[j,i] = self.eventMap[
        #eventMap = (m.eventMap.reshape((Nx*Ny, numpy.prod(m.eventMap.shape)/(Nx*Ny))).sum(axis=1) > 0).reshape((Ny,Nx))
        #x = m.photonMapX.reshape(Nx, conf["radius"]).mean(axis=1)
        #y = m.photonMapY.reshape(Ny, conf["radius"]).mean(axis=1)
        #ly, lx = numpy.where(eventMap == 1)
        #print lx,ly,x[lx[0]], y[ly[0]]
        #ly, lx = numpy.where(eventMap.T == 1)
        #print lx,ly,x[lx[0]], y[ly[0]]
        #rad = conf["radius"]
        #print eventMap.shape
        #eventMap = numpy.transpose(numpy.asarray(eventMap))
        #ly, lx = numpy.where(eventMap == 1)
        #print lx,ly,x[lx[0]], y[ly[0]]
        #ly, lx = numpy.where(eventMap.T == 1)
        #print lx,ly,x[lx[0]], y[ly[0]]
        #print type(eventMap)
        #eventMap2 = numpy.zeros(eventMap.shape)
        #eventMap2[:] = eventMap.T
        
    #minimum = m.meanMap.min()
    #print minimum
    #yopt, xopt = numpy.where(m.meanMap == minimum)
    #print yopt, xopt
    #print "Current aperture position for %s: x=%d, y=%d" %(key, paramX.data, paramY.data)
    #print "Best position for %s: x=%.2f, y=%.2f, mean=%.2f" %(key, m.photonMapX[xopt[0]], m.photonMapY[yopt[0]], minimum)

