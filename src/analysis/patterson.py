import numpy
from backend.record import add_record
try:
    import spimage
    spimage_installed = True
except ImportError:
    spimage_installed = False



def patterson(evt, type, key, mask=None, threshold=None, diameter_pix=None):
    
    if not spimage_installed:
        print "For the sizing.findCenter, libspimage (https://github.com/FilipeMaia/libspimage) needs to be installed"
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
    
