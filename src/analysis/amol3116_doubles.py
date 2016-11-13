import sys
import os
import glob

import numpy
from numpy.fft import fft2,ifft2,fftshift
from scipy.ndimage import convolve as imfilter
from pylab import imsave,rot90,flipud,fliplr
import h5py
from backend.record import add_record

def gaussian_mask(dim1, dim2, centerX, centerY, sigma):
    [X, Y] = numpy.meshgrid(numpy.arange(dim1),numpy.arange(dim2))
    X -= centerX
    Y -= centerY
    mask = numpy.exp(-(X**2+Y**2)/(2*sigma**2))
    return mask

def euclid(dim1, dim2, center1, center2, radius):
    [X, Y] = numpy.meshgrid(numpy.arange(dim1),numpy.arange(dim2))
    X -= center1
    Y -= center2
    mask = ( (X**2 + Y**2) > radius**2).astype('double')
    return mask
    
def strel(dim, shape = 'cross'):
    if shape == 'cross':
        se = numpy.zeros((dim, dim))
        mid = numpy.floor(dim/2)
        se[mid, :] = 1
        se[:, mid] = 1
    elif shape == 'square':
        se = numpy.ones((dim, dim))
    elif shape == 'disk':
        se = euclid(dim, dim, dim/2, dim/2, numpy.floor(dim/2))
    return se
    
def zeropad(inp, dim1, dim2):
    output = numpy.zeros((dim1, dim2))
    x = dim1/2 - inp.shape[0]/2
    y = dim2/2 - inp.shape[1]/2
    output[x:x + inp.shape[0], y:y + inp.shape[1]] = inp
    return output
    
def myconv2(A, B, zeropadding = False):
    # TO DO: zero padding to get rid of aliasing!
    if zeropadding:
        origdim = A.shape
        nextpow = pow(2, numpy.ceil(numpy.log(numpy.max(origdim))/numpy.log(2))+1)
        A = zeropad(A, nextpow.astype(int), nextpow.astype(int))
        B = zeropad(B, nextpow.astype(int), nextpow.astype(int))
    output = fftshift(ifft2( numpy.multiply(fft2(fftshift(A)), fft2(fftshift(B)) )))
    if zeropadding:
        mid = nextpow/2
        x = origdim[0].astype(int)/2
        y = origdim[1].astype(int)/2
        output = output[mid-x: mid+x, mid-y: mid+y]
    return output

def generate_masks(pattern,scattMaskRadius=50,scattMaskCenterX=523, scattMaskCenterY=523, background=30, slit=17):
    print 'getting shape'
    [dimy,dimx] = pattern.shape
    print 'mask bad areas'
    mask = euclid(dimx, dimx, scattMaskCenterX, scattMaskCenterY, scattMaskRadius)
    mask[518:518+slit,:] = 0
    mask[370:480,520:650] = 0
    mask[:370,520:580] = 0
    mask[590:600,505:515] = 0
    print 'doint some flipping...'
    mask = fliplr(rot90(mask,3))
#    H = numpy.array([map(float,line.strip('\n').split(',')) for line in open('/Users/Goldmund/Documents/MATLAB/H.txt').readlines()])
    print 'generate smear object'
    H = zeropad(strel(9, shape = 'disk'), mask.shape[0], mask.shape[1])
    print 'broaden mask by blurring it'
    blurred = numpy.abs(myconv2(mask,H))
    newMask = 1-(blurred<0.99)
    H2 = H
    print 'blurring new mask'
    newMask = numpy.abs(myconv2(newMask.astype('double'),H2))
    mask *= newMask
    print 'creating gaussian and center mask'
    gMask = gaussian_mask(dimx,dimx,400,700,300)
    centerMask = euclid(dimx,dimx,numpy.round(dimx/2),numpy.round(dimx/2),150)
    return mask, gMask, centerMask

def double_hit_finder_evt(evt, type, key, mask, weighting_mask, center_mask, threshold_med)
    img = evt[type][key].data
    img *= mask
    img *= weighting_mask
    recon = fftshift(numpy.abs(fftshift(img)))
    recon *= center_mask
    recon = recon[recon>0]    
    med = numpy.median(recon)
    lit_pix = recon > (med*threshold_med)
    double_hitscore = lit_pix.sum()
    add_record(evt["analysis"], "analysis", "hologram score", double_hitscore, unit='cats per doghnuts')

def double_hit_finder(pattern, mask, gMask, centerMask, threshold_med, imname=''):
    hitData = numpy.array(pattern, dtype=numpy.float64)
    hitData *= numpy.array(mask)
    hitData *= numpy.array(gMask)
    holoData = fftshift(numpy.abs(ifft2(hitData)))
#    if imname == '':
#        imsave('hit2.png',holoData*centerMask)
#    else: imsave('%s.png' % imname[:-4],holoData*centerMask)
    holoData *= centerMask            
    hData = holoData[holoData>0]
    med = numpy.median(hData)
    hitS = holoData > (med * threshold_med)
#    if imname == '':
#	imsave('hit.png',hitS)
#    else: imsave('hitS_%s.png' % imname[:-4],hitS)	
    hitScore = hitS.sum()

    return hitScore

def hitfind_cxi_file(fname, attribute='/entry_1/image_1/detector_corrected/data'):
    #open h5 file
    f = h5py.File(fname,'r')
    #data is 3D structure, N x dimy x dimx, frame = dimy x dimx
    #N=number of frames/shots/diff_patterns, dimy=pixels_in_y, dimx=pixels_in_x
    data = f[attribute][...]
    hitscores = numpy.zeros((len(data),2))

    mask,gMask,centerMask = generate_masks(data[0])
    #enumerates gives number to frame -- start with 0
    for n,frame in enumerate(data):
	hitscores[n][0] = n
	hitscores[n][1] = double_hit_finder(frame,mask,gMask,centerMask)
    f.close()
    return hitscores

if __name__=='__main__':
    sourcepath = '/scratch/fhgfs/xray/amoc6914/cheetah/data/'
    outdir = 'hitScores'
    if not os.path.exists(outdir): os.mkdir(outdir)

    #find files that conform to '/scratch/fhgfs/xray/amoc6914/cheetah/data/r????/amoc6914*.h5
    # ? = any charactar
    # * = any string of characters -- in folder
    for fname in glob.glob('%s/r????/amoc6914*.h5' % sourcepath):

	# create outfile
	out = open("%s/%s_hitscores.txt" % (outdir,runname),'w')

	#get runname from fname by splitting the string at '/' and take the second to last (-2)
	runname = fname.split('/')[-2]

	#calc the hitscores for each frame in cxifile
	hitscores = hitfind_cxi_file(fname)

	# write 'framenr hiscore' for each frame/pattern 
	for m,s in hitscores:
	    out.write('%06d %6d\n' % (m,s) )

	#close file
	out.close()
