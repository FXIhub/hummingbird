# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import numpy as np
import scipy.ndimage.measurements

from hummingbird.backend import add_record
from . import beamline


def stxm(evt, data_rec, pulse_energy=1., mode='bf', cx=None, cy=None, r=20, mask=None, badmask=None):
    data = data_rec.data
    if badmask is None:
        badmask = np.ones_like(data).astype(np.bool8)
    else:
        badmask = np.bool8(badmask)
    Ny, Nx = data.shape
    if cx is None:
        cx = (Nx-1)/2.
    if cy is None:
        cy = (Ny-1)/2.
    # Round to .0 / .5    
    cx = np.round(cx * 2)/2.
    cy = np.round(cy * 2)/2.
    xx, yy = np.meshgrid(np.arange(Nx)-cx, np.arange(Ny)-cy)
    rr = np.sqrt(xx**2 + yy**2)
    if mode == 'bf':
        if mask is None:
            mask = rr < r
        else:
            mask = np.bool8(mask)
        v = data[mask & badmask].sum() / pulse_energy
    elif mode == 'df':
        if mask is None:
            mask = rr > r
        else:
            mask = ~np.bool8(mask)
        v = data[mask & badmask].sum() / pulse_energy
    elif mode == 'sum':
        v = data[badmask].sum() / pulse_energy
    elif mode == 'diff':
        # Calc crop coordinates
        Nx_half = min([cx, Nx-1-cx])
        Ny_half = min([cy, Ny-1-cy])
        x1_min = cx - Nx_half
        y1_min = cy - Ny_half
        x2_max = cx + Nx_half + 1
        y2_max = cy + Ny_half + 1
        Nx_half = int(np.ceil(Nx_half))
        Ny_half = int(np.ceil(Ny_half))
        x1_max = x1_min + Nx_half
        y1_max = y1_min + Ny_half
        x2_min = x2_max - Nx_half
        y2_min = y2_max - Ny_half
        # Calc diff
        # Original type might be unsigned integer
        #
        # Casting is done to doubles for accumulation.
        tmp = data*badmask
        diffx = (tmp[y1_min:y2_max, x1_min:x1_max].sum(dtype=np.float64) - tmp[y1_min:y2_max, x2_min:x2_max].sum(dtype=np.float64)) / pulse_energy
        diffy = (tmp[y1_min:y1_max, x1_min:x2_max].sum(dtype=np.float64) - tmp[y2_min:y2_max, x1_min:x2_max].sum(dtype=np.float64)) / pulse_energy
        # Combine diff
        v = np.sqrt(diffx**2+diffy**2)
    rec = add_record(evt["analysis"], "analysis", "stxm %s" %mode, v)
    return rec

def stxmCenterOfMass(evt, data_rec):
    center_of_mass_y, center_of_mass_x = scipy.ndimage.measurements.center_of_mass(data_rec.data)
    # this assumes that the image is centered already.
    center_of_mass_y -= data_rec.data.shape[0]/2. - 0.5
    center_of_mass_x -= data_rec.data.shape[1]/2. - 0.5
    diff = np.sqrt(center_of_mass_x**2 + center_of_mass_x**2)
    # x_rec = add_record(evt["analysis"], "analysis", "stxm center of mass x", center_of_mass_x)
    # y_rec = add_record(evt["analysis"], "analysis", "stxm center of mass y", center_of_mass_y)
    # return y_rec, x_rec
    rec = add_record(evt["analysis"], "analysis", "stxm center of mass", diff)
    return rec
