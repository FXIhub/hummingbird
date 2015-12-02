import numpy as np
from backend import add_record

def stxm(evt, data_rec, mode='bf', cx=None, cy=None, r=20):
    data = data_rec.data
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
        mask = rr < r
        v = data[mask].sum()
    elif mode == 'df':
        mask = rr > r
        v = data[mask].sum()
    elif mode == 'sum':
        v = data.sum()
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
        diffx = data[y1_min:y2_max, x1_min:x1_max].sum() - data[y1_min:y2_max, x2_min:x2_max].sum()
        diffy = data[y1_min:y1_max, x1_min:x2_max].sum() - data[y2_min:y2_max, x1_min:x2_max].sum()
        # Combine diff
        v = np.sqrt(diffx**2+diffy**2)
    rec = add_record(evt["analysis"], "analysis", "stxm %s" %mode, v)
    return rec
