from backend import Record
import ipc
import numpy as np
try:
    import spimage
    spimage_installed = True
except ImportError:
    spimage_installed = False

parameters = {}
def findCenter(evt, type, key, mask=None, x0=0, y0=0, maxshift=10, threshold=0.5, blur=4):
    """Estimating the center of diffraction based on pair-wise correlation enforcing friedel-symmetry and adding the estimated off center shifts cx and cy to
    ``evt['analysis']['offCenterX']`` and ``evt['analysis']['offCenterX']``.

    .. note:: For this function, ``libspimage`` (https://github.com/FilipeMaia/libspimage) needs to be installed.

    Args:
        :evt:       The event variable
        :type(str): The event type, e.g. photonPixelDetectors
        :key(str):  The event key of the detector, e.g. CCD 

    Kwargs:
        :mask(bool or int): Only valid pixels (mask == True or 1) are used (default: all pixels are valid)
        :x0(int):           Initial guess for off center shift in x given in pixels (default = 0)
        :y0(int):           Initial guess for off center shift in y given in pixels (default = 0)
        :maxshift(int):     Maximum shift (in both directions) in pixels that is used for searching optimum (default = 10)
        :threshold(float):  Intensities below this threshold are set to zero (default = 0.5)
        :blur(int):         Radius of the blurring kernel used to find the solution quickly (default = 4)

    :Authors: 
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se), 
        Filipe Maia (...)
    """
    if not spimage_installed:
        print "For the sizing module, libspimage (https://github.com/FilipeMaia/libspimage) needs to be installed"
        return
    img  = evt[type][key].data
    if mask is None:
        mask = np.ones_like(img)
    cx, cy = spimage.find_center(img, mask, method='blurred', x0=x0, y0=y0,
                                 dmax=maxshift, threshold=threshold, blur_radius=blur)
    evt["analysis"]["offCenterX"] = Record("offCenterX", cx, unit='px')
    evt["analysis"]["offCenterY"] = Record("offCenterY", cy, unit='px')

parameters = {}
def fitSphere(evt, type, key, mask=None, x0=0, y0=0, d0=100, i0=1.,
                wavelength=1., pixelsize=110, distance=1000, adu_per_photon=1,
                quantum_efficiency=1, material='virus', mask_radius=100,
                downsampling=1, brute_evals=10, photon_counting=True):
    """Estimating the size of particles based on diffraction data using sphere model fitting.
    Adds results to ``evt['analysis'][RESULT]`` where RESULT is 'size', 'intensity', 'centerx', 'centery', 'goodness'.
    .. note:: For this, libspimage (https://github.com/FilipeMaia/libspimage) needs to be installed.

    Args:
        :evt:       The event variable
        :type(str): The event type, e.g. photonPixelDetectors
        :key(str):  The event key of the detector, e.g. CCD 

    Kwargs:
        :keyword(type): 

    :Authors: 
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se), 
        Max Hantke (...)
    """
    if not spimage_installed:
        print "For the sizing module, libspimage (https://github.com/FilipeMaia/libspimage) needs to be installed"
        return

    img = evt[type][key].data
    if mask is None:
        mask = np.ones_like(img).astype(np.bool)

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
                                                 downsampling=1,
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
    
    evt["analysis"]["offCenterX"] = Record("offCenterX", x0, unit='px')
    evt["analysis"]["offCenterY"] = Record("offCenterY", y0, unit='px')
    evt["analysis"]["diameter"]   = Record("diameter",   diameter / 1e-9, unit='nm')
    evt["analysis"]["intensity"]  = Record("intensity",  intensity / (1e-3 / 1e-12), unit='mJ_um2')
    evt["analysis"]["goodness"]   = Record("goodness",   info["error"], unit='')


def sphereModel(evt, type, key_centerx, key_centery, key_diameter, key_intensity, 
                shape, wavelength=1., pixelsize=110, distance=1000, adu_per_photon=1,
                quantum_efficiency=1, material='virus', poisson=False):
    """Return sphere model.
    .. note:: For this, libspimage (https://github.com/FilipeMaia/libspimage) needs to be installed.

    Args:
        :evt:       The event variable
        :type(str): The event type, e.g. analysis
        :key(str):  The event key of the detector

    Kwargs:
        :keyword(type): 

    :Authors: 
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se), 
        Max Hantke (...)
    """
    if not spimage_installed:
        print "For the sizing module, libspimage (https://github.com/FilipeMaia/libspimage) needs to be installed"
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
    evt["analysis"]["fit"] = Record("fit", fit, unit='ADU')
