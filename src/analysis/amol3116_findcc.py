# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from backend import add_record
import numpy as np
from numpy.fft import fft2,ifft2,fftshift
from scipy import ndimage
from skimage import segmentation
from skimage import morphology
from scipy.ndimage.filters import gaussian_filter
from scipy.ndimage.measurements import center_of_mass

def gaussian_mask(dim1, dim2, centerX, centerY, sigma):
    [X, Y] = np.meshgrid(np.arange(dim1),np.arange(dim2))
    X -= centerX
    Y -= centerY
    mask = np.exp(-(X**2+Y**2)/(2*sigma**2))
    mask /= np.max(mask)
    return mask
    
def euclid(dim1, dim2, radius, centerX = -1, centerY = -1):
    [X, Y] = np.meshgrid(np.arange(dim1),np.arange(dim2))
    if centerX == -1:
        centerX = np.floor(dim1/2)
    if centerY == -1:
        centerY = np.floor(dim2/2)
    X -= centerX.astype(int)
    Y -= centerY.astype(int)
    circ = (X**2 + Y**2) <= radius**2
    return circ.astype(int)
    
def strel(dim, shape = 'cross'):
    # dim should be uneven! otherwise output could be asymmetric
    if shape == 'cross':
        se = np.zeros((dim, dim))
        mid = np.floor(dim/2)
        se[mid, :] = 1
        se[:, mid] = 1
    elif shape == 'square':
        se = np.ones((dim, dim))
    elif shape == 'disk':
        se = euclid(dim, dim, np.floor(dim/2))
    return se
    
def zeropad(inp, dim1, dim2):
    output = np.zeros((dim1, dim2))
    x = dim1/2 - inp.shape[0]/2
    y = dim2/2 - inp.shape[1]/2
    output[x:x + inp.shape[0], y:y + inp.shape[1]] = inp
    return output
    
def myconv2(A, B, zeropadding = False):
    # TO DO: zero padding to get rid of aliasing!
    if zeropadding:
        origdim = A.shape
        nextpow = pow(2, np.ceil(np.log(np.max(origdim))/np.log(2))+1)
        A = zeropad(A, nextpow.astype(int), nextpow.astype(int))
        B = zeropad(B, nextpow.astype(int), nextpow.astype(int))
    output = fftshift(ifft2( np.multiply(fft2(fftshift(A)), fft2(fftshift(B)) )))
    if zeropadding:
        output = output[nextpow/2 - origdim[0]/2: nextpow/2 + origdim[0]/2,nextpow/2 - origdim[1]/2: nextpow/2 + origdim[1]/2]
    return output
    
def centeroidnp(arr):
    length = arr.shape[0]
    sum_x = np.sum(arr[:, 0])
    sum_y = np.sum(arr[:, 1])
    return sum_x/length, sum_y/length

def get_CC_size(img):
    # here a much simpler function is used as the original was way too slow
    sx = ndimage.sobel(img, axis=0, mode='constant')
    sy = ndimage.sobel(img, axis=1, mode='constant')
    sob = np.hypot(sx, sy)
    
    thresh = np.median(sob) * 2
    sob_binary = sob > thresh
    
    im_dilated = morphology.binary_opening(sob_binary, selem = strel(7, shape = 'disk'))
    im_filled = ndimage.binary_fill_holes(im_dilated)
    
    return np.sum(im_filled)

def find_cc(evt, type, key, mask=None):
    """An example for an analysis module. Please document here in the docstring:

    - what the module is doing
    - what arguments need to be passed
    - what the module returns (adds to the event variable)
    - who the authors are

    Args:
        :evt:       The event variable
        :type(str): The event type
        :key(str):  The event key

    Kwargs:
        :keyword(type): Kewyword description (default = None)

    :Authors: 
        Name (email), 
        Name (email)
    """

    center_mask_radius = 0.1 # in parts of whole image
    small_CC_thresh = 500
    large_CC_thresh = 10000
    remove_large_CC = False
    pix_opening = 7
    
    H = evt[type][key].data
    #    speed up with half resolution?
    #    H = H[255:-257, 255:-257] 
    dimX, dimY = np.shape(H)
    
    if mask is None:
        bright_pixel_thresh = 1.1e4
        dark_pixel_thresh = 30
        bad_pixels_brigth = H > bright_pixel_thresh
        bad_pixels_bg = H < dark_pixel_thresh
        mask = np.array(bad_pixels_brigth + bad_pixels_bg)
        
    mask_dilated = morphology.binary_opening(mask, selem = strel(3, shape = 'disk'))
    mask_soft = gaussian_filter(np.array(mask_dilated, dtype=np.float64), 3)
    
    mask_soft /= np.max(mask_soft)
    H = H * (1-mask_soft)
    
    R = fftshift(ifft2(H))
    Rabs = np.abs(R)
    
    x = np.linspace(-dimX/2, dimX/2-1, dimX)
    y = np.linspace(-dimY/2, dimY/2-1, dimY)
    xx, yy = np.meshgrid(x,y)
    
    mask_center = np.asarray(xx**2 + yy**2) < (center_mask_radius)**2
    Rabs[mask_center] = 0
    
    intensity_mask = Rabs > np.median(Rabs)*5
    im = Rabs * intensity_mask
    
    ##### Get gradiant Image #####
    sx = ndimage.sobel(im, axis=0, mode='constant')
    sy = ndimage.sobel(im, axis=1, mode='constant')
    sob = np.hypot(sx, sy)
    
    thresh = np.median(sob)*5
    sob_binary = sob > thresh
    
    ##### Dilate the Image #####
    # TO DO: test whether cross or square works better -- original code uses cross
    im_dilated = morphology.binary_opening(sob_binary, selem = strel(pix_opening, shape = 'disk'))
    
    ##### Fill Interior Gaps #####
    im_filled = ndimage.binary_fill_holes(im_dilated)
    
    ##### Remove Connected Objects on Border #####
    im_cleared = segmentation.clear_border(im_filled)
    
    ##### Smoothen the Object #####
    # TO DO: test whether cross or square works better -- original code uses disk
    # TO DO: check if is this really necessary
    im_eroded = ndimage.binary_erosion(im_cleared, structure = strel(pix_opening, shape = 'disk'))
    # im_eroded = im_cleared
    
    ##### Remove small Objects #####
    im_cleaned = morphology.remove_small_objects(im_eroded, min_size = small_CC_thresh, connectivity = 1)
    # remove large objects?
    if remove_large_CC:
        im_cleaned = im_cleaned - morphology.remove_small_objects(im_cleaned, 
                                                               min_size = large_CC_thresh, 
                                                              connectivity = 1)
    
    labeled, n = ndimage.measurements.label(im_cleaned)        
    centroids = [[0 for a in np.arange(2)] for b in np.arange(n)]    
    
    for CC in np.arange(n):    
        tmp = labeled == CC+1
        centroids[CC] = np.round(center_of_mass(tmp)).astype(int)
    
    v = evt["analysis"]
    add_record(v, "analysis", "centroids", centroids, unit='')
    add_record(v, "analysis", "nbr_cc", n, unit='')
    # find_foci(H, centroids, -100000, 100000, 51, 50)
        
def find_foci(evt, type, key, minPhase=-100000, maxPhase=100000, steps=51, field_of_view_rad=50, wavelength=1.053, CCD_S_DIST=0.735, PX_SIZE=75e-6):
    img = evt[type][key].data #np.array(hologram.copy(), dtype=np.float64)
    centroids = evt["analysis"]["centroids"]
    Nfoci = centroids.shape[0]
    Xrange, Yrange = img.shape
    Npixel = field_of_view_rad
    
    p = np.linspace(-Xrange/2, Xrange/2-1, Xrange)
    q = np.linspace(-Yrange/2, Yrange/2-1, Yrange)
    pp, qq = np.meshgrid(p, q)
   
    phase_matrix = (2*np.pi/wavelength)*np.sqrt(1-((PX_SIZE/CCD_S_DIST)**2)*(qq**2 + pp**2))
    prop_length = np.linspace(minPhase, maxPhase, steps)
    
    variance = np.zeros([steps, Nfoci])
    # shift stuff for performance reasons
    img_shifted = fftshift(img)
    phase_matrix_shifted = fftshift(phase_matrix)
    
    for idx, phase in enumerate(prop_length):
        
        img_propagated = img_shifted * np.exp(1.j*phase*phase_matrix_shifted)
        recon = fftshift(ifft2(img_propagated))
        
        for CC in np.arange(Nfoci):
            centerx, centery = centroids[CC, :]
            reconcut = np.abs(recon[np.max([0, centerx-Npixel-1]).astype(int): np.min([Xrange-1, centerx+Npixel]).astype(int), np.max([0, centery-Npixel-1]).astype(int): np.min([Yrange-1, centery+Npixel]).astype(int)])
            variance[idx, CC] = reconcut.var()
    
    focus_distance = np.zeros(Nfoci)
    CC_size = np.zeros(Nfoci)
    focused_CC = np.zeros(4*Npixel**2 * Nfoci).reshape(Nfoci, 2*Npixel, 2*Npixel)
    
    for CC in np.arange(Nfoci):
        ind_max = np.argmax(variance[:, CC])
        tmp = variance[:, CC]
        # get max which is not at border
        loc_max_bool = np.r_[True, tmp[1:] > tmp[:-1]] & np.r_[tmp[:-1] > tmp[1:], True]
        loc_max_bool[0] = False
        loc_max_bool[-1] = False
        ind_max = np.argmax(tmp*loc_max_bool)
        
        focus_distance[CC] = prop_length[ind_max]
        img_propagated = img_shifted * np.exp(1.j * focus_distance[CC]  * phase_matrix_shifted)
        recon = fftshift(ifft2(img_propagated))
        
        centerx, centery = centroids[CC, :]
        
        reconcut = np.real(recon[np.max([0, centerx-Npixel]).astype(int): np.min([Xrange-1, centerx+Npixel]).astype(int), np.max([0, centery-Npixel]).astype(int): np.min([Yrange-1, centery+Npixel]).astype(int)])
        focused_CC[CC, 0:reconcut.shape[0], 0:reconcut.shape[1]] = reconcut
        CC_size[CC] = np.sum(get_CC_size(reconcut))
        
    v = evt["analysis"]
    add_record(v, "analysis", "focused_cc", focused_CC, unit='')
    add_record(v, "analysis", "focus_distance", focus_distance, unit='')
    add_record(v, "analysis", "cc_size", CC_size, unit='')
    add_record(v, "analysis", "prop_range", prop_length, unit='')
#        
#    size_bool = (CC_size > -1)
#    CC_size = CC_size[size_bool]
#    Nfoci_new = np.sum(size_bool.astype(int))
#    focused_CC = focused_CC[size_bool]
#    focus_distance = focus_distance[size_bool]
#        
#    if Nfoci_new > 0:
#        plt.figure(figsize=(16, 16))
#        for CC in np.arange(Nfoci_new):
#            plt.subplot(np.round(np.sqrt(Nfoci_new)).astype(int), np.ceil(np.sqrt(Nfoci_new)).astype(int), CC+1)
#            plt.imshow(focused_CC[CC], vmin=np.min(focused_CC[CC]),  vmax=np.max(focused_CC[CC]), interpolation='none', cmap=CM.gray);
#            plt.title('focus at ' + str(focus_distance[CC]) + ', size ' + str(CC_size[CC]))
##            plt.axis('off')
#        plt.figure(figsize=(16, 16))
#        for CC in np.arange(Nfoci_new):
#            plt.subplot(np.round(np.sqrt(Nfoci_new)).astype(int), np.ceil(np.sqrt(Nfoci_new)).astype(int), CC+1)
#            plt.plot(prop_length ,variance[:, CC])            
#            plt.title('focus at ' + str(focus_distance[CC]) + ', size ' + str(CC_size[CC]))
##            plt.axis('off')
#        
#    plt.show()