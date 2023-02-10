# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import numpy

from hummingbird import utils
from hummingbird.backend.record import add_record


def patterson(evt, type, key, mask=None, threshold=None, diameter_pix=None, crop=None, full_output=False, xgap_pix=None, ygap_pix=None, frame_pix=None, **params):
    """TODO: missing docstring

    .. note:: This feature depends on the python package `libspimage <https://github.com/FilipeMaia/libspimage>`_.
    """
    success, module = utils.io.load_spimage()
    if not success:
        print("Skipping analysis.patterson.patterson")
        return
    img  = evt[type][key].data
    if mask is None:
        mask = numpy.ones(shape=img.shape, dtype="bool")
    else:
        mask = numpy.array(mask, dtype="bool")

    if crop is not None:
        img = module.crop(img, crop)
        mask = module.crop(mask, crop)
        
    out = module.patterson(numpy.float64(img), mask, full_output=full_output, normalize_median=False, **params)
    
    v = evt["analysis"]
    
    if full_output:
        P = abs(out[0])
        info = out[1]
        add_record(v, "analysis", "patterson kernel", info["kernel"], unit='')
        add_record(v, "analysis", "patterson intensities", info["intensities_times_kernel"], unit='')
    else:
        P = abs(out)

    m = numpy.median(P)
    if not numpy.isclose(m, 0.):
        P = P / m
    
    add_record(v, "analysis", "patterson", P, unit='')

    if threshold is not None:
        Minf = ~numpy.isfinite(P)
        if Minf.sum() > 0:
            P[Minf] = 0
        M = P > threshold
        if diameter_pix is not None:
            Y,X = numpy.indices(P.shape)
            X -= P.shape[1]/2
            Y -= P.shape[0]/2
            Rsq = X**2+Y**2
            M *= Rsq > (diameter_pix/2)**2
        if xgap_pix is not None:
            cy = M.shape[0]/2 
            M[cy-xgap_pix/2:cy+xgap_pix/2,:] = False
        if ygap_pix is not None:
            cx = M.shape[1]/2 
            M[:,cx-ygap_pix/2:cx+ygap_pix/2] = False
        if frame_pix is not None:
            M[:frame_pix,:] = False
            M[-frame_pix:,:] = False
            M[:,:frame_pix] = False
            M[:,-frame_pix:] = False
        if full_output:
            add_record(v, "analysis", "patterson multiples", M, unit='')
        multiple_score = M.sum()
        add_record(v, "analysis", "multiple score", multiple_score, unit='')
