# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import numpy as np

from hummingbird import ipc, utils
from hummingbird.backend import add_record


def findCenter(evt, type, key, mask=None, x0=0, y0=0, maxshift=10, threshold=0.5, blur=4):
    """Estimating the center of diffraction based on pair-wise correlation enforcing friedel-symmetry and adding the estimated off center shifts cx and cy to
    ``evt['analysis']['offCenterX']`` and ``evt['analysis']['offCenterX']``.

    .. note:: For this function, `libspimage <https://github.com/FilipeMaia/libspimage>`_ needs to be installed.

    Args:
        :evt:       The event variable
        :type(str): The event type of detectors, e.g. photonPixelDetectors
        :key(str):  The event key of a detector, e.g. CCD 

    Kwargs:
        :mask(bool or int): Only valid pixels (mask == True or 1) are used (default: all pixels are valid)
        :x0(int):           Initial guess for off center shift in x given in pixels (default = 0)
        :y0(int):           Initial guess for off center shift in y given in pixels (default = 0)
        :maxshift(int):     Maximum shift (in both directions) in pixels that is used for searching optimum (default = 10)
        :threshold(float):  Intensities below this threshold are set to zero (default = 0.5)
        :blur(int):         Radius of the blurring kernel used to find the solution quickly (default = 4)

    :Authors: 
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se), 
        Filipe Maia,
        Tomas Ekeberg
    """
    success, spimage = utils.io.load_spimage()
    if not success:
        print("Skipping analysis.sizing.findCenter")
        return
    img  = evt[type][key].data
    if mask is None:
        mask = np.ones(shape=img.shape, dtype="bool")
    else:
        mask = np.array(mask, dtype="bool")
    cx, cy = spimage.find_center(img, mask, method='blurred', x0=x0, y0=y0,
                                 dmax=maxshift, threshold=threshold, blur_radius=blur)
    v = evt["analysis"]
    add_record(v, "analysis", "offCenterX", cx, unit='px')
    add_record(v, "analysis", "offCenterY", cy, unit='px')
    add_record(v, "analysis", "cx", (img.shape[1]-1)/2. + cx, unit='px')
    add_record(v, "analysis", "cy", (img.shape[0]-1)/2. + cy, unit='px')

def fitSphere(evt, type, key, mask=None, x0=0, y0=0, d0=100, i0=1.,
                wavelength=1., pixelsize=110, distance=1000, adu_per_photon=1,
                quantum_efficiency=1, material='virus', mask_radius=100,
                downsampling=1, brute_evals=10, photon_counting=True):
    """Estimating the size of particles based on diffraction data using sphere model fitting.
    Adds results to ``evt['analysis'][RESULT]`` where RESULT is 'size', 'intensity', 'centerx', 'centery', 'goodness'.

    .. note:: For this function, `libspimage <https://github.com/FilipeMaia/libspimage>`_ needs to be installed.

    Args:
        :evt:       The event variable
        :type(str): The event type of detectors, e.g. photonPixelDetectors
        :key(str):  The event key of a detector, e.g. CCD 

    Kwargs:
        :x0(int):   Initial guess for off center shift in x (default = 0)
        :y0(int):   Initial guess for off center shift in y (default = 0)
        :d0(int):   Initial guess for diameter [nm] (default = 100)
        :i0(int):   Initial guess for intensity [mJ/um2] (default = 1)
        :wavelength(float):   Photon wavelength [nm] (default = 1)
        :pixelsize(int):      Side length of a pixel [um] (default=110)
        :distance(int):       Distance from interaction to detector [mm] (default = 1000)
        :adu_per_photon(int): ADUs per photon (default = 1)
        :quantum_efficiency(float):  Quantum efficiency of the detector (default = 1)
        :material(str):       Material of particle, e.g. virus, protein, water, ... (default = virus)
        :mask_radius(int):    Radius in pixels used for circular mask defining valid pixels for fitting (default=100)
        :downsampling(int):   Factor of downsampling, 1 means no downsampling (default = 1)
        :brute_evals(int):    Nr. of brute force evaluations for estimating the size (default = 10)
        :photon_counting(bool): If True, Do photon conversion (discretization)  before fitting (default = True)

    :Authors: 
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se), 
        Max Hantke,
        Filipe Maia
    """
    success, spimage = utils.io.load_spimage()
    if not success:
        print("Skipping analysis.sizing.fitSphere")
        return
    
    img = evt[type][key].data
    if mask is None:
        mask = np.ones(shape=img.shape, dtypt="bool")
    else:
        mask = np.array(mask, dtype="bool")

    diameter   = d0 * 1e-9
    intensity  = i0 * 1e-3 / 1e-12
    wavelength *= 1e-9
    distance   *= 1e-3
    pixelsize  *= 1e-6

    diameter, info = spimage.fit_sphere_diameter(img, mask, diameter, intensity, wavelength, pixelsize, distance,
                                                 method='pearson', full_output=True, x0=x0, y0=y0,
                                                 detector_adu_photon=adu_per_photon,
                                                 detector_quantum_efficiency=quantum_efficiency,
                                                 material=material,
                                                 rmax=mask_radius,
                                                 downsampling=downsampling,
                                                 do_brute_evals=brute_evals,
                                                 do_photon_counting=photon_counting)
    
    intensity, info = spimage.fit_sphere_intensity(img, mask, diameter, intensity, wavelength, pixelsize, distance,
                                                   method='nrphotons', full_output=True, x0=x0, y0=y0,
                                                   detector_adu_photon=adu_per_photon,
                                                   detector_quantum_efficiency=quantum_efficiency,
                                                   material=material,
                                                   rmax=mask_radius,
                                                   downsampling=downsampling,
                                                   do_photon_counting=photon_counting)

    params = spimage.fit_full_sphere_model(img, mask, diameter, intensity, wavelength, pixelsize, distance,
                                           full_output=True, x0=x0, y0=y0, detector_adu_photon=adu_per_photon,
                                           detector_quantum_efficiency=quantum_efficiency,
                                           material=material,
                                           rmax=mask_radius,
                                           downsampling=downsampling,
                                           do_photon_counting=photon_counting)
    x0, y0, diameter, intensity, info = params

    v = evt["analysis"]
    add_record(v, "analysis", "offCenterX", x0, unit='')
    add_record(v, "analysis", "offCenterY", y0, unit='')
    add_record(v, "analysis", "cx", (img.shape[1]-1)/2. + x0, unit='px')
    add_record(v, "analysis", "cy", (img.shape[0]-1)/2. + y0, unit='px')
    add_record(v, "analysis", "diameter", diameter / 1E-9, unit='nm')
    add_record(v, "analysis", "intensity", intensity / (1e-3 / 1e-12), unit='mJ/um**2')
    add_record(v, "analysis", "error", info["error"], unit='')

def sphereModel(evt, type, key_centerx, key_centery, key_diameter, key_intensity, 
                shape, wavelength=1., pixelsize=110, distance=1000, adu_per_photon=1,
                quantum_efficiency=1, material='virus', poisson=False):
    """Return sphere model.

    .. note:: For this function, `libspimage <https://github.com/FilipeMaia/libspimage>`_ needs to be installed.

    Args:
        :evt:       The event variable
        :type(str): The event type, e.g. analysis
        :key_centerx(str):    The event key of the estimated off center shift in x
        :key_centery(str):    The event key of the estimated off center shift in y
        :key_diameter(str):   The event key of the estimated diameter
        :key_intensity(str):  The event key of the estimated intensity
        :shape(tuple):        The shape of the fit

    Kwargs:
        :wavelength(float):   Photon wavelength [nm] (default = 1)
        :pixelsize(int):      Side length of a pixel [um] (default=110)
        :distance(int):       Distance from interaction to detector [mm] (default = 1000)
        :adu_per_photon(int): ADUs per photon (default = 1)
        :quantum_efficiency(float):  Quantum efficiency of the detector (default = 1)
        :material(str):       Material of particle, e.g. virus, protein, water, ... (default = virus)
        :poisson(bool):       If True, apply poisson sampling (default = False)

    :Authors: 
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se), 
        Max Hantke,
        Filipe Maia
    """
    success, spimage = utils.io.load_spimage()
    if not success:
        print("Skipping analysis.sizing.sphereModel")
        return
    
    centerx    = evt[type][key_centerx].data
    centery    = evt[type][key_centery].data    
    diameter   = evt[type][key_diameter].data * 1e-9
    intensity  = evt[type][key_intensity].data * 1e-3 / 1e-12    
    wavelength *= 1e-9
    distance   *= 1e-3
    pixelsize  *= 1e-6

    size    = spimage.sphere_model_convert_diameter_to_size(diameter, wavelength,
                                                            pixelsize, distance) 
    scaling = spimage.sphere_model_convert_intensity_to_scaling(intensity, diameter,
                                                                wavelength, pixelsize,
                                                                distance, quantum_efficiency,
                                                                adu_per_photon, material)
    fit     = spimage.I_sphere_diffraction(scaling,
                                           spimage.rgrid(shape, (centerx, centery)),
                                           size)
    if poisson:
        fit = np.random.poisson(fit)
    add_record(evt["analysis"], "analysis", "fit", fit, unit='ADU')


def fitSphereRadial(evt, type, radial_distance_key, radial_average_key, mask_r=None, d0=100, i0=1.,
                    wavelength=1., pixelsize=110, distance=1000, adu_per_photon=1,
                    quantum_efficiency=1, material='virus', mask_radius=100,
                    brute_evals=10, photon_counting=True):
    """    
    Estimating the size of particles based on diffraction data using radial sphere model fitting.
    Adds results to ``evt['analysis'][RESULT]`` where RESULT is 'diameter', 'intensity', 'error'.

    .. note:: For this function, `libspimage <https://github.com/FilipeMaia/libspimage>`_ needs to be installed.

    Args:
        :evt:       The event variable
        :type(str): The event type of detectors, e.g. photonPixelDetectors
        :key(str):  The event key of a detector radial average, e.g. radial average - CCD 

    Kwargs:
        :d0(int):   Initial guess for diameter [nm] (default = 100)
        :i0(int):   Initial guess for intensity [mJ/um2] (default = 1)
        :wavelength(float):   Photon wavelength [nm] (default = 1)
        :pixelsize(int):      Side length of a pixel [um] (default=110)
        :distance(int):       Distance from interaction to detector [mm] (default = 1000)
        :adu_per_photon(int): ADUs per photon (default = 1)
        :quantum_efficiency(float):  Quantum efficiency of the detector (default = 1)
        :material(str):       Material of particle, e.g. virus, protein, water, ... (default = virus)
        :mask_radius(int):    Radius in pixels used for circular mask defining valid pixels for fitting (default=100)
        :brute_evals(int):    Nr. of brute force evaluations for estimating the size (default = 10)
        :photon_counting(bool): If True, Do photon conversion (discretization)  before fitting (default = True)

    :Authors: 
        Max Hantke (hantke@xray.bmc.uu.se),
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se), 
        Filipe Maia
    """
    success, spimage = utils.io.load_spimage()
    if not success:
        print("Skipping analysis.sizing.fitSphereRadial")
        return
    
    r     = evt[type][radial_distance_key].data
    img_r = evt[type][radial_average_key].data

    diameter   = d0 * 1e-9
    intensity  = i0 * 1e-3 / 1e-12
    wavelength *= 1e-9
    distance   *= 1e-3
    pixelsize  *= 1e-6

    if False:
        t = img_r.max()*0.2
        i_max = np.arange(img_r.size)[img_r>t].max()
        img_r_m = img_r[:i_max]
        r_m = r[:i_max]
    else:
        img_r_m = img_r
        r_m = r
    
    #if True:    
    #    from scipy.ndimage.filters import gaussian_filter
    #    img_r_m = gaussian_filter(img_r_m,2.)
    #    add_record(evt["analysis"], "analysis", "radial average - used", img_r_m)
    
    diameter, info = spimage.fit_sphere_diameter_radial(r_m, img_r_m, diameter, intensity, wavelength, pixelsize, distance,
                                                        full_output=True,
                                                        detector_adu_photon=adu_per_photon,
                                                        detector_quantum_efficiency=quantum_efficiency,
                                                        material=material,
                                                        do_brute_evals=brute_evals)
                                                        
    
    intensity, info = spimage.fit_sphere_intensity_radial(r_m, img_r_m, diameter, intensity, wavelength, pixelsize, distance,
                                                          full_output=True,
                                                          detector_adu_photon=adu_per_photon,
                                                          detector_quantum_efficiency=quantum_efficiency,
                                                          material=material)
    
    v = evt["analysis"]
    add_record(v, "analysis", "diameter", diameter / 1E-9, unit='nm')
    add_record(v, "analysis", "intensity", intensity / (1e-3 / 1e-12), unit='mJ/um**2')
    add_record(v, "analysis", "fit error", info["error"], unit='')

def absolute_error(evt, type_a, key_a, type_b, key_b, out_key=None):
    """Returning the absolute error between two records as a new record."""
    a = evt[type_a][key_a]
    b = evt[type_b][key_b]
    if out_key is None:
        out_key = "abs(%s - %s)" %(a.name, b.name)
    add_record(evt["analysis"], "analysis", out_key, abs(a.data-b.data), unit='')
    
def photon_error(evt, type_data, key_data, type_fit, key_fit, adu_per_photon):
    import scipy.misc
    data = np.array(evt[type_data][key_data].data / (1.*adu_per_photon), dtype="float")
    fit = np.array(evt[type_fit][key_fit].data / (1.*adu_per_photon), dtype="float")
    data_best = fit.round()
    data = data.copy()
    M = fit != 0
    M *= data > 0
    M *= data_best > 0

    K = data[M]
    W = fit[M]
    Ks = data_best[M]
    
    # Stirling
    lKf = K*np.log(K)-K
    tmp = K < 5
    if tmp.sum():
        lKf[tmp] = np.log( scipy.misc.factorial(K[tmp], exact=False) )

    # Stirling
    lKsf = Ks*np.log(Ks)-Ks
    tmp = Ks < 5
    if tmp.sum():
        lKsf[tmp] = np.log( scipy.misc.factorial(Ks[tmp], exact=False) )
    
    error = ( Ks * np.log(W) - lKsf ) - ( K * np.log(W) - lKf )
    error = error.sum()
    add_record(evt["analysis"], "analysis", "photon error", error, unit='')
