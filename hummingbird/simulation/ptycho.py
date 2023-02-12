# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import print_function  # Compatibility with python 2 and 3

import os
import sys

import h5py
import matplotlib.pyplot as plt
import numpy as np
import PIL.Image as Image
import scipy.ndimage as ndi
from matplotlib.colors import LogNorm
from scipy.ndimage import zoom

from hummingbird import utils

# Physical constants
h = 6.62606957e-34 #[Js]
c = 299792458 #[m/s]
hc = h*c  #[Jm] 

# Loading a test object (binary hummingbird logo)
test_object = np.load(os.path.dirname(os.path.realpath(__file__)) + '/test_object.npy')*1e2

class Simulation:
    def __init__(self):
        """
        Simulator for Ptychography experiments at LCLS.
        
        :Authors:
            Simone Sala,
            Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
        """
        self.counter = 0
        self.endless = False

    def setSource(self, wavelength=1e-10, focus_diameter=4.5e-6, pulse_energy=2e-3, transmission=1.):
        """
        Specify source parameters.

        :Kwargs:
            :wavelength(float): Photon wavelength given in [m], default=1e-10
            :focus_diameter(float): Diameter of the beam in focus in [m], default = 4.5e-6
            :pulse_energy(float): Pulse energy in the focus in [J], default = 2e-3
            :transmission(float): transmission, default = 1 
        """
        self.wavelength = wavelength #[m]
        self.photon_energy = hc / wavelength #[J]
        self.focus_diameter = focus_diameter #[m]
        self.pulse_energy = pulse_energy * transmission #[J]

    def setDetector(self, pixelsize=75e-6, nx=512, distance=740e-3, adus_per_photon=1):
        """
        Specify detector parameters.

        :Kwargs:
            :pixelsize(float): Size of a detector pixel in [m], default=75e-6
            :nx(int): Side length of the detector in [px], default=512
            :distance(float): Distance to the detector in [m], default=740e-3
            :adus_per_photon(float): Nr. of ADUs per pixel, default = 1
        """
        self.det_pixelsize = pixelsize #[m]
        self.det_sidelength = nx #[px]
        self.det_distance = distance #[m]
        self.det_adus_per_photon = adus_per_photon
        self.dx = self.wavelength * distance / (nx * pixelsize) #[m/px]

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
        self.positions_y = np.array([start[1] + i*step for i in range(scany)])

    def setObject(self, sample='default', size=1e-3, thickness=200e-9, material='gold', filename='./', smooth=2):
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
            img = self.loadFromFile(filename)
            img = ndi.gaussian_filter(img, smooth)
        elif sample == 'logo':
            img = test_object
            img = ndi.gaussian_filter(img, smooth)
        elif sample == 'sinus':
            img = self.loadTestObject(np.round(size / self.dx))
        self.sample_sidelength = np.round(size / self.dx)

        # Refractive index
        if material == 'gold':
            success, module = utils.io.load_condor()
            if not success:
                print("Could not lookup refractive index, using values for gold at 6 keV")
                dn = 8.45912218E-05 + 1j* 1.38081241E-05
            else:
                m = module.utils.material.AtomDensityMaterial('custom', massdensity=19320, atomic_composition={'Au':1})
                dn = m.get_dn(self.wavelength)
        else:
            print("Material not defined, use Gold at 6 keV")
            dn = 8.45912218E-05 + 1j* 1.38081241E-05

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
        return sample

    def loadXradiaStar(self):
        """
        Loads modelled Siemens star patterns (from ptypy.utils)
        """
        try:
            import ptypy.utils
        except ImportError:
            print("Siemens star cannot be loaded with the ptypy package (https://github.com/ptycho/ptypy)")
        sample = ptypy.utils.xradia_star((900, 900),spokes=60,minfeature=1,ringfact=1.8,rings=5)
        return sample

    def loadTestObject(self, size):
        """Loads a simple test object.

        Args:
            :size(int): Size of test object in [px].
        """
        [X,Y] = np.meshgrid(np.arange(-np.pi,np.pi,2.0*np.pi/size),
                            np.arange(-np.pi,np.pi,2.0*np.pi/size))
        return np.sin(X)*np.sin(X*Y) * 10.

    def setIllumination(self, shape='gaussian'):
        """
        Specify the intensity profile and other parameters of of the illumination.

        Kwargs:
            :shape(str): flat or gaussian (default)
        """
        # Create cartesian and radial grids
        x = np.arange(-self.det_sidelength/2, self.det_sidelength/2, 1).astype(float)
        y = np.arange(-self.det_sidelength/2, self.det_sidelength/2, 1).astype(float)
        xx, yy = np.meshgrid(x, y)
        rr = np.sqrt(xx**2 + yy**2)

        # Define intensity profile of illumination
        if shape == 'flat':
            self.illumination_intensity = np.array(rr<((self.focus_diameter/2.)/self.dx))
        elif shape == 'gaussian':
            sigma = self.focus_diameter / 2.3548 # match focus diameter with FWHM of the Gaussian
            self.illumination_intensity = np.exp(-.5*((rr*self.dx)**2)/(sigma**2))
        else:
            print("Shape of illumination has to be of type 'flat' or 'gaussian'")

        # Rescale intensity [ph/px]
        self.illumination_intensity = self.illumination_intensity / self.illumination_intensity.sum() * (self.pulse_energy / self.photon_energy)
        
        # Define illumination function, add linear and quadratic phase factors #[sqrt(ph)/px]
        self.illumination = np.sqrt(self.illumination_intensity) * np.exp(2j*np.pi*(xx*self.dx + 2*yy*self.dx)) *  np.exp(1j*(10000*self.dx*(xx**2 + yy**2)))

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
        
        # Propagate to far-field
        self.fourier_pattern = np.flipud(np.fft.fftshift(np.fft.fftn(self.exitwave)) / (self.det_sidelength))
        self.diffraction_pattern = np.abs(self.fourier_pattern)**2 
        
        # Sample photons (and apply detector gain)
        self.diffraction_photons = np.random.poisson(self.diffraction_pattern) * self.det_adus_per_photon
        
        # Apply detector gain to continuos diffraction pattern
        self.diffraction_pattern *= self.det_adus_per_photon
        
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
                    self.frames.append(self.diffraction_photons)
                    self.positions.append((posx,posy))
                    self.exitwaves.append(self.exitwave)
        self.frames = np.array(self.frames)
        self.positions = np.array(self.positions)
        self.exitwaves = np.array(self.exitwaves)

    def get_nextframe(self):
        """Iterate through pre-determined frames, inrements the counter
        """
        self.counter += 1
        frame = self.frames[self.counter % self.nframes - 1]
        if not self.endless and self.get_end_of_scan():
            raise IndexError
            return None
        else:
            return frame

    def get_exitwave(self):
        """Iterate through pre-determined exitwaves, does not increment the counter
        """
        exitwave = self.exitwaves[self.counter % self.nframes - 1]
        return exitwave
        
    def get_illumination(self):
        """Iterate through pre-determined illuminations, does not increment the counter
        """
        return self.illumination

    def get_position_x(self):
        """Iterate through pre-determined x positions, does not increment the counter
        """
        return self.positions[self.counter % self.nframes - 1, 0]

    def get_position_y(self):
        """Iterate through pre-determined y positions, does not increment the counter
        """
        return self.positions[self.counter % self.nframes - 1, 1]

    def get_end_of_scan(self):
        """Returns True if the end of the scan has been reached
        """
        return self.counter == (self.nframes + 1)

if __name__ == '__main__':
    
    # Simulate the ptychography experiment at AMO
    sim = Simulation()
    sim.setSource(wavelength=0.9918e-9, focus_diameter=1.5e-6, pulse_energy=1e-3, transmission=5.13e-8)
    sim.setDetector(pixelsize=75e-6, nx=512, distance=730e-3, adus_per_photon=7.95)
    sim.setScan(nperpos=10, scanx=20, scany=20, step=500e-9, start=(-8e-6, 8e-6))
    sim.setObject(sample='xradia_star', size=40e-6, thickness=180e-9, material='gold')
    sim.setIllumination(shape='gaussian')
    posx = sim.positions_x[0]
    posy = sim.positions_y[0]
    sim.shoot(posx,posy)
    print("Maximum signal on detector [ADUs]: ", sim.diffraction_pattern.max())
    
    # Plotting settings
    fig_width  = 16*0.393701
    fig_width *= 1
    fontsize = 8
    save = True
    
    # Plotting the illumination
    fig = plt.figure(figsize=(fig_width,fig_width/2))
    ax1 = fig.add_subplot(121)
    extent = 2*[-1e6*sim.dx*sim.det_sidelength/2, 1e6*sim.dx*sim.det_sidelength/2]
    ax1.imshow(np.abs(sim.illumination)**2, cmap='gray', interpolation='nearest', extent=extent)
    ax1.set_title('Illumination - Intensity', fontsize=fontsize)
    ax1.set_xlabel('[microns]', fontsize=fontsize)
    ax1.set_ylabel('[microns]', fontsize=fontsize)
    ax1.tick_params(labelsize=fontsize)
    ax2 = fig.add_subplot(122)
    im = ax2.imshow(np.angle(sim.illumination), cmap='hsv', interpolation='nearest', extent=extent)
    ax2.set_title('Illumination - Phase', fontsize=fontsize)
    ax2.set_xlabel('[microns]', fontsize=fontsize)
    ax2.set_ylabel('[microns]', fontsize=fontsize)
    ax2.tick_params(labelsize=fontsize)
    if save:
        fig.savefig('./illumination.pdf', format='pdf', bbox_inches='tight', dpi=300)

    # Plotting the exitwave 
    fig = plt.figure(figsize=(fig_width,fig_width/2))
    ax1 = fig.add_subplot(121)
    extent = 2*[-1e6*sim.dx*sim.det_sidelength/2, 1e6*sim.dx*sim.det_sidelength/2]
    im1 = ax1.imshow(np.abs(sim.exitwave), cmap='gray', interpolation='nearest', extent=extent)
    ax1.set_title('Exit wave - Amplitude', fontsize=fontsize)
    ax1.set_xlabel('[microns]', fontsize=fontsize)
    ax1.set_ylabel('[microns]', fontsize=fontsize)
    ax1.tick_params(labelsize=fontsize)
    ax2 = fig.add_subplot(122)
    ax2.imshow(np.angle(sim.exitwave), cmap='hsv', interpolation='nearest', extent=extent)
    ax2.set_title('Exit wave - Phase', fontsize=fontsize)
    ax2.set_xlabel('[microns]', fontsize=fontsize)
    ax2.set_ylabel('[microns]', fontsize=fontsize)
    ax2.tick_params(labelsize=fontsize)
    if save:
        fig.savefig('./exitwave.pdf', format='pdf', bbox_inches='tight', dpi=300)

    # Plotting the sample
    fig = plt.figure(figsize=(fig_width,fig_width/2))
    ax1= fig.add_subplot(121)
    extent = 2*[-1e6*sim.dx*sim.sample_sidelength/2, 1e6*sim.dx*sim.sample_sidelength/2]
    ax1.imshow(np.abs(sim.obj), cmap='gray', interpolation='nearest', extent=extent)
    origin = (1e6*(posx-sim.dx*sim.det_sidelength/2),1e6*(posy-sim.dx*sim.det_sidelength/2))
    width  = (1e6*sim.dx*sim.det_sidelength)
    height = (1e6*sim.dx*sim.det_sidelength)
    ax1.add_patch(plt.Rectangle(origin, width, height, facecolor='None', edgecolor='r', linewidth=2, alpha=1))
    ax1.set_title('Object - Amplitude', fontsize=fontsize)
    ax1.set_xlabel('[microns]', fontsize=fontsize)
    ax1.set_ylabel('[microns]', fontsize=fontsize)
    ax1.tick_params(labelsize=fontsize)
    ax2 = fig.add_subplot(122)
    ax2.imshow(np.angle(sim.obj), cmap='hsv', interpolation='nearest', extent=extent)
    ax2.add_patch(plt.Rectangle(origin,width,height, facecolor='None', edgecolor='w', linewidth=2, alpha=1))
    ax2.set_title('Object - Phase', fontsize=fontsize)
    ax2.set_xlabel('[microns]', fontsize=fontsize)
    ax2.set_ylabel('[microns]', fontsize=fontsize)
    ax2.tick_params(labelsize=fontsize)
    if save:
        fig.savefig('./object.pdf', format='pdf', bbox_inches='tight', dpi=300)

    # Plotting the diffraction pattern
    fig = plt.figure(figsize=(fig_width,fig_width*(5./14)))
    ax1 = fig.add_subplot(121)
    im1 = ax1.imshow(sim.diffraction_pattern, cmap='gnuplot', interpolation='nearest', norm=LogNorm(vmin=0.1))
    ax1.set_title('Continuous diffraction pattern', fontsize=fontsize)
    ax1.tick_params(labelsize=fontsize)
    ax2 = fig.add_subplot(122)
    im2 = ax2.imshow(sim.diffraction_photons, cmap='gnuplot', interpolation='nearest', norm=LogNorm(vmin=0.1))
    ax2.set_title('Sampled diffraction pattern', fontsize=fontsize)
    ax2.tick_params(labelsize=fontsize)
    cb = fig.colorbar(im1)
    cb.ax.set_ylabel('ADUs / pixel', fontsize=fontsize)
    cb.ax.tick_params(labelsize=fontsize)
    if save:
        fig.savefig('./diffraction.pdf', format='pdf', bbox_inches='tight', dpi=300)
    plt.show()
