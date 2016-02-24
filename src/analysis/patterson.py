# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
import numpy
import utils.io
from backend.record import add_record

def patterson(evt, type, key, mask=None, threshold=None, diameter_pix=None):
    """TODO: missing docstring

    .. note:: This feature depends on the python package `libspimage <https://github.com/FilipeMaia/libspimage>`_.
    """
    success, module = utils.io.load_spimage()
    if not success:
        print "Skipping analysis.patterson.patterson"
        return
    img  = evt[type][key].data
    if mask is None:
        mask = numpy.ones(shape=img.shape, dtype="bool")
    else:
        mask = numpy.array(mask, dtype="bool")
        
    P = spimage.patterson(img, mask, floor_cut=100., mask_smooth=4., darkfield_x=None, darkfield_y=None, darkfield_sigma=None, normalize_median=True, radial_boost=False, log_boost=True, gauss_damp=True, gauss_damp_sigma=None, gauss_damp_threshold=None, subtract_fourier_kernel=True, log_min=1., full_output=False)    
    v = evt["analysis"]
    add_record(v, "analysis", "patterson", abs(P), unit='')

    if threshold is not None:
        M = P > threshold
        if diameter_pix is not None:
            Y,X = numpy.indices(P.shape)
            X -= P.shape[1]/2
            Y -= P.shape[0]/2
            Rsq = X**2+Y**2
            M *= Rsq > diameter_pix**2
        multiple_score = M.sum()
        add_record(v, "analysis", "multiple score", multiple_score, unit='')
    
