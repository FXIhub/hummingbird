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
        step = conf["step"]
        radius = conf["radius"]
        self.photonMapX = numpy.linspace(xmin, xmax, (xmax-xmin)/float(step))
        self.photonMapY = numpy.linspace(ymin, ymax, (ymax-ymin)/float(step))
        Nx = self.photonMapX.shape[0]
        Ny = self.photonMapY.shape[0]
        self.photonMap  = lil_matrix((Ny, Nx), dtype=numpy.float32)
        self.gasMap     = lil_matrix((Ny, Nx), dtype=numpy.float32)
        #self.eventMap   = lil_matrix((Ny, Nx), dtype=numpy.bool)
        #self.eventMapDown = np.zeros((100,100)), dtype=numpy.bool)
        self.counter    = 0
        #ipc.broadcast.init_data(key+'overview', data_type='image', xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, xlabel=conf["xlabel"], ylabel=conf["ylabel"], history_length=1)
        #print Nx,Ny
        #print Nx/2-radius, Nx/2+radius
        #print Ny/2-radius, Ny/2+radius
        ipc.broadcast.init_data(key+'local', data_type='image', xmin=self.photonMapX[Nx/2-radius], xmax=self.photonMapX[Nx/2+radius+1], ymin=self.photonMapY[Ny/2-radius], ymax=self.photonMapY[Ny/2+radius+1], xlabel=conf["xlabel"], ylabel=conf["ylabel"], history_length=10)

    def append(self, N, X, Y, G):
        self.photonMap[abs(self.photonMapY - Y.data).argmin(), abs(self.photonMapX - X.data).argmin()] += N
        self.gasMap[abs(self.photonMapY - Y.data).argmin(), abs(self.photonMapX - X.data).argmin()] += G
        #self.eventMap[abs(self.photonMapY - Y.data).argmin(), abs(self.photonMapX - X.data).argmin()] = 1
        #visited = self.eventMap != 0
        #self.meanMap[visited] = self.photonMap[visited] / self.eventMap[visited]
        #self.meanMap[~visited] = 1.1 * self.meanMap[visited].max()
        #self.meanMap[~visited] = 0.0
        self.counter += 1

def grab_array(A, cen, rad):
    return A[cen[0]-rad: cen[0]+rad+1, cen[1]-rad:cen[1]+rad+1].toarray()

photonMaps = {}
def plotMeanPhotonMap(key, conf, nrPhotons, paramX, paramY, pulseEnergy):
    if not key in photonMaps:
        photonMaps[key] = MeanPhotonMap(key,conf)
    m = photonMaps[key]
    m.append(nrPhotons, paramX, paramY, pulseEnergy)
    if(not m.counter % conf["updateRate"]):
        center = (abs(m.photonMapY - paramY.data).argmin(), abs(m.photonMapX - paramX.data).argmin())
        photonMap = grab_array(m.photonMap, center, conf["radius"])
        gasMap = grab_array(m.gasMap, center, conf["radius"])
        visited = gasMap != 0
        meanMap = numpy.zeros(photonMap.shape)
        meanMap[visited] = photonMap[visited] / gasMap[visited]
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
        rad = conf["radius"]
        #print eventMap.shape
        #eventMap = numpy.transpose(numpy.asarray(eventMap))
        #ly, lx = numpy.where(eventMap == 1)
        #print lx,ly,x[lx[0]], y[ly[0]]
        #ly, lx = numpy.where(eventMap.T == 1)
        #print lx,ly,x[lx[0]], y[ly[0]]
        #print type(eventMap)
        #eventMap2 = numpy.zeros(eventMap.shape)
        #eventMap2[:] = eventMap.T
        #ipc.new_data(key+'overview', eventMap.T) 
        ipc.new_data(key+'local', meanMap, xmin=m.photonMapX[center[1]-rad], xmax=m.photonMapX[center[1]+rad+1], ymin=m.photonMapY[center[0]-rad], ymax=m.photonMapY[center[0]+rad+1])
    #minimum = m.meanMap.min()
    #print minimum
    #yopt, xopt = numpy.where(m.meanMap == minimum)
    #print yopt, xopt
    #print "Current aperture position for %s: x=%d, y=%d" %(key, paramX.data, paramY.data)
    #print "Best position for %s: x=%.2f, y=%.2f, mean=%.2f" %(key, m.photonMapX[xopt[0]], m.photonMapY[yopt[0]], minimum)

