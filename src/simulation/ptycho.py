"""
Simulator for Ptychography experiment at LCLS

Some details for AMO:
=====================
dector: distance 731 mm, size (1024x1024)/4 => 512x512
        pixel size 75 um
sample: finest feature .5 um, diameter 200 um
        Si3N4 thickness 1 um Vs structure height 1.6 um +- .016 (i.e. only gold on substrate ??)
energy: ca. .85 keV => (6.6*.3)/(.8*1.6) nm .. ca. 1.5 nm

authors: Simone Sala, Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
"""
import scipy.ndimage as ndi
import PIL.Image as Image
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
from scipy.ndimage import zoom
import h5py
import sys
import condor

h = 6.62606957e-34 #Js
c = 299792458 #m/s
hc = h*c  #Jm 

class Simulation:
    def __init__(self):
        """
        Simulator for Ptychography experimetns at LCLS.
        
        :Authors:
            Simone Sala,
            Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
        """
        self.counter = 0

    def setSource(self, wavelength=1e-10, focus_diameter=4.5e-6, pulse_energy=2e-3, attenuation=1.):
        """
        Specify source parameters.

        :Kwargs:
            :wavelength(float): Photon wavelength given in [m], default=1e-10
            :focus_diameter(float): Diameter of the beam in focus in [m], default = 4.5e-6
            :pulse_energy(float): Pulse energy in the focus in [J], default = 2e-3
            :attenauation(float): Attenuation factor, default = 1 (no attenuation)
        """
        self.wavelength = wavelength
        self.photon_energy = hc / wavelength #[J]
        self.focus_diameter = focus_diameter
        self.pulse_energy = pulse_energy / attenuation

    def setDetector(self, pixelsize=75e-6, nx=512, distance=740e-3):
        """
        Specify detector parameters.

        :Kwargs:
            :pixelsize(float): Size of a detector pixel in [m], default=75e-6
            :nx(int): Side length of the detector in [px], default=512
            :distance(float): Distance to the detector in [m], default=740e-3
        """
        self.det_pixelsize = pixelsize
        self.det_sidelength = nx
        self.det_distance = distance
        self.dx = self.wavelength * distance / (nx * pixelsize)

    def setScan(self, nperpos=10, scanx=4, scany=4, step=200e-9, start=(0,0)):
        """
        Specify the scan procedure.

        Kwargs:
            :nperpos(int): Nr. of shots per scanning position, default=50
            :scanx(int): Nr. of horizontal scanning positions, default=10
            :scany(int): Nr. of vertical scanning positions, default=10
            :step(float): Step size in [m], default=200e-9
            :start(tuple): Starting position in [m] as (x,y) tuple, default=(0,0)
        """
        self.nperpos     = nperpos
        self.scanx       = scanx
        self.scany       = scany
        self.nframes     = nperpos * scanx * scany
        self.positions_x = np.array([start[0] + i*step for i in range(scanx)])
        self.positions_y = np.array([start[1] - i*step for i in range(scany)])

    def setObject(self, sample='xradia_star', size=1e-3, thickness=200e-9, material='gold', filename='./', smooth=2):
        """
        Specify the object.

        Kwargs:
            :sample(str): 'xradia_star' or 'file' (needs filename and smooth to be defined), default = 'xradia_star'
            :size(float): Size of sample in [m], default = 1e-3
            :sample_thickness(float): Thickness of sample in [m], default = 200e-9
            :material(str): Material of the sample, default = 'gold'

        """
        # Contrast
        if sample == 'xradia_star':
            img = self.loadXradiaStar()
        elif sample == 'file':
            img = self.loadFromFile(filename, smooth)
        self.sample_sidelength = np.round(size / self.dx)

        # Refractive index
        if material == 'gold':
            m = condor.utils.material.Material('custom', massdensity=19320, atomic_composition={'Au':1})
            dn = m.get_dn(self.wavelength)
        else:
            print "Material not defined"

        # Complex transmission function
        tr = 2*np.pi*dn*thickness/self.wavelength
        self.obj = np.exp(1j*tr*zoom(img, self.sample_sidelength/img.shape[0]))

    def loadFromFile(self, filename, smooth):
        """
        Loads a binary sample from a given file, assuming squared images.

        Args:
            :filename(str): Sample file to be loaded (.png) 
            :smooth(int):   Std of gaussian filter applied to the image
        """
        with Image.open(filename) as f:
            nr_channels = len(f.mode)
            nx, ny = f.size            
            assert nx == ny, "Can only load square images"
            sample = np.array(f.getdata()).reshape((nx,ny,nr_channels))
            sample = 1-sample[:,:,0]/255.
            sample = ndi.gaussian_filter(sample, smooth)
        return sample

    def loadXradiaStar(self):
        """
        Loads modelled Siemens star patterns (from ptypy.utils)
        """
        try:
            import ptypy
        except ImportError:
            print "Siemens star cannot be loaded with the ptypy package (https://github.com/ptycho/ptypy)"
        sample = ptypy.utils.xradia_star((900, 900),spokes=60,minfeature=1,ringfact=1.8,rings=5)
        #ADD 'cut' spoke .. refine model !!
        return sample

    def setIllumination(self, shape='gaussian'):
        """
        Specify the intensity profile and other parameters of of the illumination.

        Kwargs:
            :shape(str): flat or gaussian (default)
        """
        x = np.arange(-self.det_sidelength/2, self.det_sidelength/2, 1).astype(float)
        y = np.arange(-self.det_sidelength/2, self.det_sidelength/2, 1).astype(float)
        xx, yy = np.meshgrid(x, y)
        rr = np.sqrt(xx**2 + yy**2)

        # Define intensity profile of illumination
        if shape == 'flat':
            self.illumination = np.array(rr<((self.focus_diameter/2.)/self.dx))
        elif shape == 'gaussian':
            sigma = self.focus_diameter / 2.3548 # match focus diameter with FWHM of the Gaussian
            self.illumination = np.exp(-.5*((rr*self.dx)**2)/(sigma**2))
        else:
            print "Shape of illumination has to be of type 'flat' or 'gaussian'"

        # Define amplitude of illumination [ph/m]
        self.illumination = np.sqrt(self.illumination / (self.illumination.sum() * (self.dx*self.det_sidelength)**2) * (self.pulse_energy / self.photon_energy) )

        # Add a phase ramp
        self.illumination = self.getMode(self.illumination, [3,2])

    def getMode(self, I, rampxy=[0,0]):
        """
        Returns the probe with a phase ramp applied. The phase ramp is defined by shifting the probe in fourier space.

        Args:
            :I(array): array of illuminaton

        Kwargs:
            :rampxy: A list with shifts [x,y], default = [0,0]
        """
        return np.fft.ifftn(np.roll(np.roll( np.fft.fftn(I), rampxy[0], axis=0),rampxy[1], axis=1))
                                                                            
    def getRandomMode(self, I, sramp=5.):
        """
        Returns the probe with a randomized phase ramp applied. The phase ramp is defined by shifting the probe in fourier space.

        Args:
            :I(array): array of illuminaton

        Kwargs:
            :sramp: Standard deviation of normal distributation, a random shift is picked based on that distribution, default=5.
        """
        rxy = np.round(np.random.normal(size=(2,), scale=sramp)).astype(int)
        return self.getMode(I, rxy)

    def shoot(self, posx=0, posy=0):
        """
        Shoot the sample on a given position and record diffraction pattern. 
        
        Kwargs:
            :posx(float): Vertical position of the beam relative to the center of the sample in [m] (positive to the right), default = 0
            :posy(float): Vertical position of the beam relative to the center of the sample in [m] (positive is upwards,    default = 0
        """
        # Check if given position is within possible scanning range
        assert abs(posx) < ((self.sample_sidelength//2)*self.dx - (self.det_sidelength//2)*self.dx), "Scan position in x outside possible range"
        assert abs(posy) < ((self.sample_sidelength//2)*self.dx - (self.det_sidelength//2)*self.dx), "Scan position in x outside possible range"

        # Illuminate at given position in x,y
        ytop    = int(self.sample_sidelength//2 - np.round(posy/self.dx) - self.det_sidelength//2)
        ybottom = int(self.sample_sidelength//2 - np.round(posy/self.dx) + self.det_sidelength//2) 
        xleft   = int(self.sample_sidelength//2 + np.round(posx/self.dx) - self.det_sidelength//2)
        xright  = int(self.sample_sidelength//2 + np.round(posx/self.dx) + self.det_sidelength//2)
        self.exitwave = self.obj[ytop:ybottom, xleft:xright] * self.illumination
        #self.exitwave = np.lib.pad(self.exitwave, ((256,256),(256,256)), 'constant', constant_values=((0,0),(0,0)))

        # Propagate to far-field
        self.fourier_pattern = (1./self.wavelength/self.det_distance)*(self.dx**2)*self.det_pixelsize*np.fft.fftshift(np.fft.fft2(self.exitwave))
        self.diffraction_pattern = np.abs(self.fourier_pattern)**2

    def start(self):
        """
        Runs the entire scan at once and saves all diffraction patterns, positions and exitwaves
        """
        self.frames = []
        self.positions = []
        self.exitwaves = []
        for posy in self.positions_y:
            for posx in self.positions_x:
                for i in range(self.nperpos):
                    self.shoot(posx,posy)
                    self.frames.append(self.diffraction_pattern)
                    self.positions.append((posx,posy))
                    self.exitwaves.append(self.exitwave)
        self.frames = np.array(self.frames)
        self.positions = np.array(self.positions)
        self.exitwaves = np.array(self.exitwaves)

    def get_nextframe(self):
        """
        Iterate through pre-determined frames, inrements the counter
        """
        frame = self.frames[self.counter % self.nframes]
        self.counter += 1
        return frame

    def get_exitwave(self):
        """
        Iterate through pre-determined exitwaves, does not increment the counter
        """
        exitwave = self.exitwaves[self.counter % self.nframes]
        return exitwave
        
    def get_illumination(self):
        """
        Iterate through pre-determined illuminations, does not increment the counter
        """
        return self.illumination

    def get_position_x(self):
        """
        Iterate through pre-determined x positions, does not increment the counter
        """
        return self.positions[self.counter % self.nframes, 0]

    def get_position_y(self):
        """
        Iterate through pre-determined y positions, does not increment the counter
        """
        return self.positions[self.counter % self.nframes, 1]

if __name__ == '__main__':
    
    # Simulate the ptychography experiment at AMO
    sim = Simulation()
    sim.setSource(wavelength=0.9918e-9, focus_diameter=1.5e-6, pulse_energy=2e-3, attenuation=1) 
    sim.setDetector(pixelsize=75e-6, nx=512, distance=730e-3)
    sim.setScan(nperpos=10, scanx=20, scany=20, step=500e-9, start=(-8e-6, 8e-6))
    sim.setObject(sample='xradia_star', size=40e-6, thickness=180e-9, material='gold')
    sim.setIllumination(shape='gaussian')
    posx = sim.positions_x[0]
    posy = sim.positions_y[0]
    sim.shoot(posx,posy)
                
    # Plotting the illumination
    fig = plt.figure(figsize=(10,5))
    ax1 = fig.add_subplot(121)
    extent = 2*[-1e6*sim.dx*sim.det_sidelength/2, 1e6*sim.dx*sim.det_sidelength/2]
    ax1.imshow(np.abs(sim.illumination)**2, cmap='gray', interpolation='nearest', extent=extent)
    ax1.set_title('Illumination - Intensity')
    ax1.set_xlabel('[microns]')
    ax1.set_ylabel('[microns]')
    ax2 = fig.add_subplot(122)
    ax2.imshow(np.angle(sim.illumination), cmap='hsv', interpolation='nearest', extent=extent)
    ax2.set_title('Illumination - Phase')
    ax2.set_xlabel('[microns]')
    ax2.set_ylabel('[microns]')

    # Plotting the exitwave 
    fig = plt.figure(figsize=(10,5))
    ax1 = fig.add_subplot(121)
    extent = 2*[-1e6*sim.dx*sim.det_sidelength/2, 1e6*sim.dx*sim.det_sidelength/2]
    ax1.imshow(np.abs(sim.exitwave), cmap='gray', interpolation='nearest', extent=extent)
    ax1.set_title('Exit wave - Amplitude')
    ax1.set_xlabel('[microns]')
    ax1.set_ylabel('[microns]')
    ax2 = fig.add_subplot(122)
    ax2.imshow(np.angle(sim.exitwave), cmap='hsv', interpolation='nearest', extent=extent)
    ax2.set_title('Exit wave - Phase')
    ax2.set_xlabel('[microns]')
    ax2.set_ylabel('[microns]')

    # Plotting the sample
    fig = plt.figure(figsize=(10,5))
    ax1= fig.add_subplot(121)
    extent = 2*[-1e6*sim.dx*sim.sample_sidelength/2, 1e6*sim.dx*sim.sample_sidelength/2]
    ax1.imshow(np.abs(sim.obj), cmap='gray', interpolation='nearest', extent=extent)
    origin = (1e6*(posx-sim.dx*sim.det_sidelength/2),1e6*(posy-sim.dx*sim.det_sidelength/2))
    width  = (1e6*sim.dx*sim.det_sidelength)
    height = (1e6*sim.dx*sim.det_sidelength)
    ax1.add_patch(plt.Rectangle(origin, width, height, facecolor='None', edgecolor='r', linewidth=2, alpha=1))
    ax1.set_title('Object - Amplitude')
    ax1.set_xlabel('[microns]')
    ax1.set_ylabel('[microns]')
    ax2 = fig.add_subplot(122)
    ax2.imshow(np.angle(sim.obj), cmap='hsv', interpolation='nearest', extent=extent)
    ax2.add_patch(plt.Rectangle(origin,width,height, facecolor='None', edgecolor='w', linewidth=2, alpha=1))
    ax2.set_title('Object - Phase')
    ax2.set_xlabel('[microns]')
    ax2.set_ylabel('[microns]')

    # Plotting the exitwave 
    fig = plt.figure(figsize=(14,5))
    ax1 = fig.add_subplot(121)
    im1 = ax1.imshow(sim.diffraction_pattern, cmap='gnuplot', interpolation='nearest', norm=LogNorm(vmin=0.1))
    ax1.set_title('Continuous diffraction pattern')
    ax2 = fig.add_subplot(122)
    im2 = ax2.imshow(np.random.poisson(sim.diffraction_pattern), cmap='gnuplot', interpolation='nearest', norm=LogNorm(vmin=0.1))
    ax2.set_title('Sampled diffraction pattern')
    cb = fig.colorbar(im1)
    plt.show()
    
    

