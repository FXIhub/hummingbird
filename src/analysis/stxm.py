import numpy as np
from backend import add_record

def stxm_sum(evt, data_rec):
    data = data_rec.data
    v = data.sum()
    rec = add_record(evt["analysis"], "analysis", "stxm sum", v)
    return rec

def stxm_diff(evt, data_rec, cx=None, cy=None):
    data = data_rec.data
    Nx = data.shape[1]
    Ny = data.shape[0]
    if cx is None:
        cx = (Nx-1)/2.
    if cy is None:
        cy = (Ny-1)/2.
    # Round to .0 / .5    
    cx = np.round(cx * 2)/2.
    cy = np.round(cy * 2)/2.
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
    diffx = data[y1_min:y2_max, x1_min:x1_max].sum() - data[y1_min:y2_max, x2_min:x2_max].sum()
    diffy = data[y1_min:y1_max, x1_min:x2_max].sum() - data[y2_min:y2_max, x1_min:x2_max].sum()
    # Combine diff
    diff = np.sqrt(diffx**2+diffy**2)
    rec = add_record(evt["analysis"], "analysis", "stxm diff", diff)
    return rec
