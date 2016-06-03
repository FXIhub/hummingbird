# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
import numpy
import utils.io
from backend.record import add_record

def patterson(evt, type, key, mask=None, threshold=None, diameter_pix=None, crop=None, full_output=False, **params):
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

    if crop is not None:
        img = module.crop(img, crop)
        mask = module.crop(mask, crop)
        
    out = module.patterson(img, mask, full_output=full_output, normalize_median=True, **params)

    v = evt["analysis"]
    
    if full_output:
        P = abs(out[0])
        info = out[1]
        add_record(v, "analysis", "patterson kernel", info["kernel"], unit='')
        add_record(v, "analysis", "patterson kernel", info["intensities_times_kernel"], unit='')
    else:
        P = abs(out)
    
    add_record(v, "analysis", "patterson", abs(P), unit='')

    if threshold is not None:
        M = P > threshold
        if diameter_pix is not None:
            Y,X = numpy.indices(P.shape)
            X -= P.shape[1]/2
            Y -= P.shape[0]/2
            Rsq = X**2+Y**2
            M *= Rsq > diameter_pix**2
            if full_output:
                add_record(v, "analysis", "patterson multiples", M, unit='')
        multiple_score = M.sum()
        add_record(v, "analysis", "multiple score", multiple_score, unit='')
    
