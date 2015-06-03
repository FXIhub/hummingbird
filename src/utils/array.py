import numpy
import logging

def slacH5ToCheetah(slacArr):
    out_arr = numpy.zeros((8*185, 4*388))
    for c in range(4):
        for r in range(8):
            slacPos = r + c*8
            (rB, rE) = (r*185, (r+1)*185)
            (cB, cE) = (c*388, (c+1)*388)
            out_arr[rB:rE, cB:cE] = (slacArr[slacPos])
    return out_arr


def cheetahToSlacH5(cheetahArr):
    out_arr = numpy.zeros((32, 185, 388))
    for c in range(4):
        for r in range(8):
            slacPos = r + c*8
            (rB, rE) = (r*185, (r+1)*185)
            (cB, cE) = (c*388, (c+1)*388)
            out_arr[slacPos] = cheetahArr[rB:rE, cB:cE]
    return out_arr

def assembleImage(x, y, img=None, nx=None, ny=None, dtype=None, return_indices=False):
    x -= x.min()
    y -= y.min()
    shape = (y.max() - y.min() + 1, x.max() - x.min() + 1)  
    (height, width) = shape
    if (nx is not None) and (nx > shape[1]):
        width = nx
    if (ny is not None) and (ny > shape[0]):
        height = ny 
    assembled = numpy.zeros((height,width))
    if return_indices:
        return assembled, height, width, shape, y, x
    assembled[height-shape[0]:height, :shape[1]][y,x] = img
    if dtype is not None:
        assembled = assembled.astype(getattr(numpy, dtype))
    return assembled

def binImage(img, binning, msk=None, output_binned_mask=False):
    """ This function bins a 2D image. The image will be cropped before binning if the dimensions are not a multiple of the binning factor. 
    If a mask is provided the mask is applied to the image before binning. 
    Binned pixels from partly masked out regions are scaled up such that the mean value within the bin matches the binned value divided by the binning factor squared.

    Args:
        :img:       Array of the native image
        :binning(ing): Binning factor
    Kwargs:
        :msk(int, bool):  Mask array, True (or 1) means it is a valid pixel
        :output_binned_mask: (bool): Toggle if you want that the binned mask is return besides the binned image
    
    :Authors:
        Max F. Hantke (hantke@xray.bmc.uu.se)
    """
    nx = img.shape[1]
    ny = img.shape[0]
    valid_input = True
    img_new = img
    msk_new = msk
    if binning > nx or binning > ny:
        valid_input = False
        logging.warning("Image with dimensions %i x %i too small to be binned by %i x %i.", ny, nx, binning, binning)
    if msk is not None:
        # Check for matching dimensions
        if msk.shape[0] != img.shape[0] or msk.shape[1] != img.shape[1]:
            logging.error("Dimensions of image (%i x %i) and mask (%i x %i) do not match.", img.shape[0], img.shape[1], msk.shape[0], msk.shape[1])
            valid_input = False
    if valid_input:
        # Crop image such that dimensions are multiples of binning
        nx_new = nx - nx % binning
        ny_new = ny - ny % binning
        img_new = img[:ny_new,:nx_new]
        if msk is not None:
            # Crop mask
            msk_new = msk[:ny_new,:nx_new]
            # Set masked out values in image to zero
            img_new *= msk_new
            # Bin mask
            msk_new = numpy.array(msk_new, dtype="int")
            msk_new = msk_new.reshape(nx_new // binning, binning, ny_new // binning, binning)
            msk_new = msk_new.sum(axis=3).sum(axis=1)
        # New dimensions for binned pixels
        img_new = img_new.reshape(nx_new // binning, binning, ny_new // binning, binning)
        img_new = img_new.sum(axis=3).sum(axis=1)
        if msk is not None:
            img_new *= float(binning**2) / (msk_new + numpy.finfo("float").eps)
    if output_binned_mask:
        return img_new, msk_new
    else:
        return img_new

def _testBinImage(binning,masking=True):
    from scipy import misc
    l1 = misc.lena()
    l1 = l1[:l1.shape[0] - l1.shape[0] % binning,:l1.shape[1] - l1.shape[1] % binning]
    S1 = l1.sum()
    m1 = m2 = None
    if masking:
        m1 = numpy.random.random(l1.shape)
        m1 = numpy.array(numpy.round(m1),dtype="bool")
        l1 *= m1
    l2,m2 = binImage(l1,binning,m1,output_binned_mask=True)
    S2 = l2.sum()
    print "Sum original (cropped) image: %f" % S1
    print "Sum binned image: %f" % S2
    print "Sum difference: %.3f %%" % (100.*abs(S1-S2).sum()/2./(S1+S2).sum())
    return l1,l2,m1,m2
    
    
def _radialImage(img,mode="mean",cx=None,cy=None,msk=None,output_r=False):
    """ This function calculates a radial representation of a 2D image.
    If a mask is provided the mask is applied to the image before projection. The output of radii that include only masked out pixels is set to nan.
    The center is put into the middle of the respective axis if a center coordinate is not specified (set to None).

    Args:
        :img:       Array of the native image
        :mode(str): Projection mode can be mean, sum, std or median
    Kwargs:
        :cx(float): Center x coordinate
        :cy(float): Center y coordinate
        :msk(int, bool):  Mask array, True (or 1) means it is a valid pixel
        :output_r(book): Set to true if also the array of the radii shall be in the output

    :Authors:
        Max F. Hantke (hantke@xray.bmc.uu.se)
    """
    if mode == "mean": f = numpy.mean
    elif mode == "sum": f = numpy.sum
    elif mode == "std": f = numpy.std
    elif mode == "median": f = numpy.median
    else:
        logging.error("ERROR: No valid mode given for radial projection.")
        return None
    if cx is None: cx = (img.shape[1]-1)/2.0
    if cy is None: cy = (img.shape[0]-1)/2.0
    X,Y = numpy.meshgrid(numpy.arange(img.shape[1]),numpy.arange(img.shape[0]))
    R = numpy.sqrt((X - float(cx))**2 + (Y - float(cy))**2)
    R = R.round()
    if msk is not None:
        if (msk == 0).sum() > 0:
            R[msk == 0] = -1
    radii = numpy.arange(R.min(),R.max()+1,1)
    if radii[0] == -1:
        radii = radii[1:]
    values = numpy.zeros_like(radii)
    for i in range(0,len(radii)):
        tmp = R==radii[i]
        if tmp.sum() > 0:
            values[i] = f(img[tmp])
        else:
            values[i] = numpy.nan
    if output_r:
        return radii,values
    else:
        return values

def radialSumImage(img,**kwargs):
    return _radialImage(img,mode="sum",**kwargs)
def radialStd(img,**kwargs):
    return _radialImage(img,mode="std",**kwargs)
def radialMeanImage(img,**kwargs):
    return _radialImage(img,mode="mean",**kwargs)
def radialMedianImage(img,**kwargs):
    return _radialImage(img,mode="median",**kwargs)

def _testRadialImage(Nx=100,Ny=103,cx=45.3,cy=43.2):
    X,Y = numpy.meshgrid(numpy.arange(Nx),numpy.arange(Ny))
    R = numpy.sqrt((X-cx)**2+(Y-cy)**2)
    img = R.round()
    print "Std-zero-test: Succeeded = %s" % (radialStdImage(img,cx=cx,cy=cy).sum()==0.)
    return img,radialMeanImage(img,cx=cx,cy=cy,output_r=True)
