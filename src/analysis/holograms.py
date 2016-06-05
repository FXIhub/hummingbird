import sys
import os
import glob
import h5py
import numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pylab as pylab
from scipy.fftpack import fft2,ifft2,fftshift
from scipy.ndimage import convolve as imfilter
from pylab import imsave,sqrt,rot90,flipud,fliplr,subplots,savefig,close
from matplotlib.colors import LogNorm
from scipy.ndimage import gaussian_filter
from backend.record import add_record
from scipy.ndimage.morphology import binary_dilation, binary_erosion, binary_opening
from scipy.ndimage.measurements import center_of_mass
import time
from scipy import ndimage
import skimage
from skimage.morphology import binary_opening as bin_opening
from matplotlib.colors import LogNorm
from scipy.ndimage import gaussian_filter
from scipy.ndimage.morphology import binary_dilation, binary_erosion, binary_opening, binary_fill_holes
from scipy.ndimage.measurements import center_of_mass
import time
from scipy import ndimage

def gaussian_mask(dim1, dim2, centerX, centerY, sigma):
    [X, Y] = numpy.meshgrid(numpy.arange(dim1, dtype=numpy.float64),numpy.arange(dim2, dtype=numpy.float64))
    X -= centerX
    Y -= centerY
    mask = numpy.exp(-(X**2+Y**2)/(2*sigma**2))
    mask[mask<1e-20] = 0
    return mask

def euclid(dim1, dim2, center1, center2, radius):
    [X, Y] = numpy.meshgrid(numpy.arange(dim1, dtype=numpy.float64),numpy.arange(dim2, dtype=numpy.float64))
    X -= center1
    Y -= center2
    mask = ( (X**2 + Y**2) > radius**2).astype('double')
    return mask

def strel(dim, shape = 'cross'):
    # dim should be uneven! otherwise output could be asymmetric
    if shape == 'cross':
        se = numpy.zeros((dim, dim))
        mid = numpy.floor(dim/2)
        se[mid, :] = 1
        se[:, mid] = 1
    elif shape == 'square':
        se = numpy.ones((dim, dim))
    elif shape == 'disk':
        se = euclid(dim, dim, numpy.floor(dim/2))
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
        output = output[nextpow/2 - origdim[0]/2: nextpow/2 + origdim[0]/2,nextpow/2 - origdim[1]/2: nextpow/2 + origdim[1]/2]
    return output

def generate_masks(pattern,scattMaskRadius=50,scattMaskCenterX=523, scattMaskCenterY=523, background=30, slit=60):
    [dimy,dimx] = pattern.shape
    mask = euclid(dimx, dimx, scattMaskCenterX, scattMaskCenterY, scattMaskRadius)
    #mask[518:518+slit,:] = 0
    #mask[370:480,520:650] = 0
    #mask[:370,520:580] = 0
    #mask[590:600,505:515] = 0        
    crosswidth = 10
    shiftx = 10
    shifty = 5
    mask[512-crosswidth+shiftx:512+crosswidth+shiftx, :] = 0
    mask[:, 512-crosswidth+shifty:512+crosswidth+shifty] = 0
    mask[470:512, 400:512] = 0
    
    mask = fliplr(rot90(mask,3))
    H = numpy.array([map(float,line.strip('\n').split(',')) for line in filterwindow.split('\n')])
    blurred = imfilter(mask,H)
    newMask = 1-(blurred<0.99)
    H2 = H
    newMask = imfilter(newMask.astype('double'), H2)

    #newMask = imfilter(newMask.astype('double'), H2)


    mask *= newMask

    gMask = gaussian_mask(dimx,dimx,400,700,300)
    centerMask = euclid(dimx,dimx,numpy.round(dimx/2),numpy.round(dimx/2),70)
    return mask, gMask, centerMask

def plotting_hologram(imname,pattern,holoData,hitS,runname=''):
    fig,[ax0,ax1,ax2] = subplots(1,3)    
    fig.tight_layout()
    for i in (ax0,ax1,ax2):
        i.set_xticks([])
        i.set_yticks([])

    ax0.imshow(pattern,norm=LogNorm())
    ax1.imshow(holoData)
    ax2.imshow(hitS)
    savefig('hitScores/hologram_%s_%06d.png' % (runname,imname))
    close(fig)

def crossremove(img,width=4):
    a = img.shape[0]/2
    b = 217
    c = 297
    img[a-width:a+width,:] = 0
    img[b-width:b+width,:] = 0
    img[c-width:c+width,:] = 0
    img[:,a-width:a+width] = 0
    return img

def holographic_hitfinder_evt(evt, type, key, mask, gMask, centerMask, off_x, th=3):
    img = evt[type][key].data
    #img = gaussian_filter(img,sigma=3)
    hitData = numpy.zeros((1024+off_x,1024+off_x))
   
    hitData[:513,:] = img[:513,:]
    hitData[-514:,:] = img[-514:,:]
    
    hitData[hitData > 12000] = 0
    #    hitData[:512,393] = 0
    #   hitData[-512:,395] = 0
    dd = int(off_x/2)
    cropsize = 256
    pattern = hitData[dd+cropsize:-dd-cropsize,dd+cropsize:-dd-cropsize]
    mask = mask[dd+cropsize:-dd-cropsize,dd+cropsize:-dd-cropsize]
    gMask = gMask[dd+cropsize:-dd-cropsize,dd+cropsize:-dd-cropsize]
    centerMask = centerMask[dd+cropsize:-dd-cropsize,dd+cropsize:-dd-cropsize]

    pattern[:512,393] = 0
    pattern[-512:,395] = 0

    hitData = pattern*mask
    #hitData *= gMask	
    holoData = fftshift(numpy.abs(ifft2(hitData)))
    holoData *= centerMask
    hData = holoData[holoData>0]
    med = numpy.median(hData)

    #if holoData.max() > 1: holoData /= holoData.max()
    med = numpy.median(holoData)
    #hitS = 1.*(holoData > 0.1)
    hitS = 1.*(holoData > med*3)
    hitS = crossremove(hitS)
    hitScore = hitS.sum()
    
    if hitScore > 2000:
        #hitS = 1.*(holoData > 0.2)
        hitS = 1.*(holoData > med*5)
        hitS = crossremove(hitS)

        hitScore = hitS.sum()

    if hitScore > 5000:
        hitS = binary_erosion(hitS)
        hitS = binary_erosion(hitS)
        hitS = binary_erosion(hitS)
        hitS = binary_erosion(hitS)
        hitS = binary_dilation(hitS)

        hitS = crossremove(hitS)

        hitScore = hitS.sum()
        #labeled = hitS
        labeled, n = ndimage.measurements.label(hitS)
    
    else:
        hitS[0][0] = 2
    
        labeled, n = ndimage.measurements.label(hitS)
        
        for i in range(1,n):
            ss = ((labeled == i)*1.).sum()
            if ss < 20:
                labeled[labeled == i] = 0
                hitS[labeled == i] = 0.
        
        hitScore = ((labeled>0)*1).sum()
#        print hitScore
    
    add_record(evt["analysis"], "analysis", "hologramScore", hitScore)
    add_record(evt["analysis"], "analysis", "holoData", holoData)

    add_record(evt["analysis"], "analysis", "labeledHolograms", labeled)
    add_record(evt["analysis"], "analysis", "croppedPattern", pattern*mask)

#    add_record(evt["analysis"], "analysis", "holomask", mask)

def segment_holographic_hit(evt, type, key):
    labeled = evt[type][key].data
    if numpy.unique(labeled).shape[0] == 3: 
        return labeled

    hitS = ((labeled >0)*1)
    hitS = ndimage.morphology.binary_dilation(hitS)

    for i in range(4):
        hitS = ndimage.morphology.binary_dilation(hitS)

    hh = gaussian_filter(hitS*4,sigma=15)


    thresh = 5*numpy.median(hh)
    hh[hh > thresh] = 1
    hh[hh <= thresh] = 0
    hitS = hh
    labeled, nn = ndimage.measurements.label(hitS)
    
    centroids = [[0 for a in numpy.arange(2)] for b in numpy.arange(nn)]    

    for CC in numpy.arange(nn):    
        tmp = (labeled == CC+1)*1.
        centroid = center_of_mass(tmp)
        #labeled[labeled == CC+1] = 0
        if centroid[0] > 30 and centroid[0] < tmp.shape[0]-30 and centroid[1] > 30 and centroid[1] < tmp.shape[1]-30:
            centroids[CC] = numpy.round(center_of_mass(tmp)).astype(int)
            labeled[centroid[0]-4:centroid[0]+4,centroid[1]-4:centroid[1]+4] = 10

            
        

    centroids = numpy.array(centroids, dtype=numpy.int64)

    add_record(evt["analysis"], "analysis", "labeledHolograms", labeled)

    add_record(evt["analysis"], "analysis", "centroids", centroids)
   
def centeroidnp(arr):
    length = arr.shape[0]
    sum_x = numpy.sum(arr[:, 0])
    sum_y = numpy.sum(arr[:, 1])
    return sum_x/length, sum_y/length

def get_CC_size(img):
    # here a much simpler function is used as the original was way too slow
    sx = ndimage.sobel(img, axis=0, mode='constant')
    sy = ndimage.sobel(img, axis=1, mode='constant')
    sob = numpy.hypot(sx, sy)
    
    thresh = numpy.median(sob) * 2
    sob_binary = sob > thresh
    
    im_dilated = bin_opening(sob_binary, selem=strel(7, shape = 'disk'))
    im_filled = ndimage.binary_fill_holes(im_dilated)
    
    return numpy.sum(im_filled)

def strel(dim, shape = 'cross'):
    # dim should be uneven! otherwise output could be asymmetric
    if shape == 'cross':
        se = numpy.zeros((dim, dim))
        mid = numpy.floor(dim/2)
        se[mid, :] = 1
        se[:, mid] = 1
    elif shape == 'square':
        se = numpy.ones((dim, dim))
    elif shape == 'disk':
        se = euclid(dim, dim, numpy.floor(dim/2),numpy.floor(dim/2),numpy.floor(dim/2))
    return se

def find_foci(evt, type,key,type2,key2,minPhase=-500000, maxPhase=500000, steps=101, field_of_view_rad=100, wavelength=1.053, CCD_S_DIST=0.375, PX_SIZE=75e-6):
    img = evt[type][key].data
    centroids = evt[type2][key2].data

    Nfoci = centroids.shape[0]
    Xrange, Yrange = img.shape
    Npixel = field_of_view_rad
    
    p = numpy.linspace(-Xrange/2, Xrange/2-1, Xrange)
    q = numpy.linspace(-Yrange/2, Yrange/2-1, Yrange)
    pp, qq = numpy.meshgrid(p, q)
   
    phase_matrix = (2*numpy.pi/wavelength)*numpy.sqrt(1-((PX_SIZE/CCD_S_DIST)**2)*(qq**2 + pp**2))
    prop_length = numpy.linspace(minPhase, maxPhase, steps)
    
    variance = numpy.zeros([steps, Nfoci])
    # shift stuff for performance reasons
    img_shifted = fftshift(img)
    phase_matrix_shifted = fftshift(phase_matrix)
    
    for idx, phase in enumerate(prop_length):
        
        img_propagated = img_shifted * numpy.exp(1.j*phase*phase_matrix_shifted)
        recon = fftshift(ifft2(img_propagated))
        
        for CC in numpy.arange(Nfoci):
            centerx, centery = centroids[CC, :]
            ###print  centerx, centery
            reconcut = numpy.abs(recon[numpy.max([0, centerx-Npixel-1]).astype(int): numpy.min([Xrange-1, centerx+Npixel]).astype(int), numpy.max([0, centery-Npixel-1]).astype(int): numpy.min([Yrange-1, centery+Npixel]).astype(int)])
            variance[idx, CC] = reconcut.var()
    
    focus_distance = numpy.zeros(Nfoci)
    CC_size = numpy.zeros(Nfoci)
    focused_CC = numpy.zeros(4*Npixel**2 * Nfoci).reshape(Nfoci, 2*Npixel, 2*Npixel)
    
    for CC in numpy.arange(Nfoci):
        ind_max = numpy.argmax(variance[:, CC])
        tmp = variance[:, CC]
        # get max which is not at border
        loc_max_bool = numpy.r_[True, tmp[1:] > tmp[:-1]] & numpy.r_[tmp[:-1] > tmp[1:], True]
        loc_max_bool[0] = False
        loc_max_bool[-1] = False
        ind_max = numpy.argmax(tmp*loc_max_bool)
        
        focus_distance[CC] = prop_length[ind_max]
        img_propagated = img_shifted * numpy.exp(1.j * focus_distance[CC]  * phase_matrix_shifted)
        recon = fftshift(ifft2(img_propagated))
        
        centerx, centery = centroids[CC, :]
        
        reconcut = numpy.real(recon[numpy.max([0, centerx-Npixel]).astype(int): numpy.min([Xrange-1, centerx+Npixel]).astype(int), numpy.max([0, centery-Npixel]).astype(int): numpy.min([Yrange-1, centery+Npixel]).astype(int)])
        focused_CC[CC, 0:reconcut.shape[0], 0:reconcut.shape[1]] = reconcut
        CC_size[CC] = numpy.sum(get_CC_size(reconcut))
    
    if len(focused_CC):
        add_record(evt["analysis"], "analysis", "focused_CC", focused_CC[0])
        add_record(evt["analysis"], "analysis", "focus distance", focus_distance)
        add_record(evt["analysis"], "analysis", "CC_size", CC_size)
        add_record(evt["analysis"], "analysis", "propagation length", prop_length)



def hitfind_cxi_file(fname, attribute='/entry_1/image_1/detector_corrected/data',initial=0, final=400):
    #open h5 file
    f = h5py.File(fname,'r')
    runname = fname.split('/')[7]
    #data is 3D structure, N x dimy x dimx, frame = dimy x dimx
    #N=number of frames/shots/diff_patterns, dimy=pixels_in_y, dimx=pixels_in_x
    #print f[attribute].shape
    data = f[attribute]
    hitscores = numpy.zeros((data.shape[0],2))

    mask,gMask,centerMask = generate_masks(data[0])

    [dim1,dim2]=data[0].shape
    [X, Y] = numpy.meshgrid(numpy.arange(dim1),numpy.arange(dim2))
    X -= 523
    Y -= 523
    R = sqrt(X**2+Y**2)


    for n,frame in enumerate(data):
        ration = 0
        if frame.sum():
            ration = 1.*frame[R>50].sum()/frame.sum() 
        if n < initial or ration < 0.42: continue 
        if n > final: break
        hitscore, holoData, hitS = holographic_hitfinder(frame,mask,gMask,centerMask)
	hitscores[n][0] = n
	hitscores[n][1] = hitscore
        #os.system('echo "%s %s" >> hitScores/log.%s.txt' % (n,hitscores[n][1],fname.split('/')[1]))
        if hitscore > 100:
            plotting_hologram(n,frame,holoData,hitS,runname=runname)
            #print n,hitscores[n][1],ration
    f.close()
    return hitscores



def make_propagation(evt, type, key_img, key_mask, imnr, minPhase=-120000, maxPhase=120000, steps=50, field_of_view_rad=50, wavelength=2.353, CCD_S_DIST=0.38, PX_SIZE=75e-6,Npixel=50):
    img = evt[type][key_img].data
    Xrange, Yrange = img.shape
    p = numpy.linspace(-Xrange/2, Xrange/2-1, Xrange)
    q = numpy.linspace(-Yrange/2, Yrange/2-1, Yrange)
    pp, qq = numpy.meshgrid(p, q)
    rr = numpy.sqrt(pp**2+qq**2)

    phase_matrix = (2*numpy.pi/wavelength)*numpy.sqrt(1-((PX_SIZE/CCD_S_DIST)**2)*(qq**2 + pp**2))
    img_shifted = fftshift(img)
    phase_matrix_shifted = fftshift(phase_matrix)
    
    r,rg = [],[]
    steps = 10
    rgt = numpy.zeros((steps,Xrange,Yrange))
    stepsize = maxPhase/steps
    
    from skimage.feature import canny
    import numpy as np

    sobt = numpy.zeros_like(img)

    runname='r0043'

    for step in range(steps):
        phase = stepsize*step

        img_propagated = img_shifted * numpy.exp(1.j*phase*phase_matrix_shifted)
        img_propagated[:,Yrange/2-3:Yrange/2+3] = img_propagated.mean()
        recon = fftshift(ifft2(img_propagated))
        recon[rr < 30] = recon.mean()


        cc = canny(abs(recon), sigma=9)

        cc = binary_dilation(cc)
        cc = binary_dilation(cc)
        cc = binary_dilation(cc)
        cc = binary_fill_holes(cc)
        cc = binary_erosion(cc)
        cc = binary_erosion(cc)
        cc = binary_erosion(cc)
        cc = binary_erosion(cc)
        cc = binary_erosion(cc)

        criterion0 = cc

        sx = ndimage.sobel(abs(recon), axis=0, mode='constant')
        sy = ndimage.sobel(abs(recon), axis=1, mode='constant')
        sob = numpy.hypot(sx, sy)
        sob[rr < 31] = sob.max()
        sobt += (sob > 0.1*sob.max())*1.
      
        diff = abs(sob-sob.max())
        diff /= diff.max()
      
        if phase == 0:
            
            criterion1 = sob>sob.max()/2

            sg = gaussian_filter(sobt,sigma=1)
            labeled,nnn = ndimage.measurements.label(sg)
            
            remove = (labeled == labeled[256][256])*1
            remove[246:266,:] = 1
            remove[206:306,246:266]= 1

            sg[labeled == labeled[256][256]] = 0
            sg = sg > 0
            sg = binary_erosion(sg)
            sg = binary_erosion(sg)
            sg = binary_erosion(sg)
            sg = binary_erosion(sg)
            sg = binary_erosion(sg)
            sg = binary_erosion(sg)
            sg = binary_erosion(sg)
            criterion2 = sg
            

            FF = 1*(criterion0+criterion1+criterion2)#*abs(1-remove)
            FF = binary_erosion(FF,numpy.ones((2,2)))
            FF[remove > 0] = 1
            labeled,nnn = ndimage.measurements.label(FF)
            labeled[labeled == labeled[256][256]] = 0
            dance = labeled > 0
            dance = binary_dilation(dance)

            if nnn-1 < 2:
                return 0
            num_holograms = nnn-1
            images = []
            variance = []
            centroids = []
            for structure in numpy.unique(labeled):
                if structure < 1: continue
                centroids.append( numpy.round(center_of_mass(labeled == structure)).astype(int) )
                images.append([])
                variance.append([])
        
        cnt = 0

        for centerx,centery in centroids:
            reconcut = numpy.abs(recon[numpy.max([0, centerx-Npixel-1]).astype(int): numpy.min([Xrange-1, centerx+Npixel]).astype(int), numpy.max([0, centery-Npixel-1]).astype(int): numpy.min([Yrange-1, centery+Npixel]).astype(int)])
            images[cnt].append(reconcut)
            variance[cnt].append(reconcut.var())
            cnt +=1
        #imsave('hitScores/hollows/img_recon_%05d_%06d_3.png'%(imnr,phase),recon,cmap='gray')
            
        #rg.append(recon)
    #print variance
    
    focused_CC = []
    z_location = []
    for i in range(num_holograms):
        minn = numpy.argmax(numpy.array(variance[i]))
        imsave('hitScores/hollows/img_%s_%05d_%06d_%d.png'%(runname,imnr,phase,i), images[i][minn])
        focused_CC.append(images[i][numpy.argmin(numpy.array(variance[i]))])
        z_location.append(stepsize*minn)

    if len(focused_CC) > ):
        add_record(evt["analysis"], "analysis", "focused_CC", focused_CC[0])
        add_record(evt["analysis"], "analysis", "focus distance", z_location)
    #add_record(evt["analysis"], "analysis", "CC_size", CC_size)
    #add_record(evt["analysis"], "analysis", "propagation length", prop_length)


if __name__=='__main__':
    sourcepath = '/scratch/fhgfs/xray/amoc6914/cheetah/data/'
    outdir = 'hitScores'
    if not os.path.exists(outdir): os.mkdir(outdir)

    i,f = 0,400

    if len(sys.argv) > 1:
        i = int(sys.argv[1])
    if len(sys.argv) > 2:
        f = int(sys.argv[2])

    #find files that conform to '/scratch/fhgfs/xray/amoc6914/cheetah/data/r????/amoc6914*.h5
    # ? = any charactar
    # * = any string of characters -- in folder
    for fname in glob.glob('%s/r0???/amoc6914*.cxi' % sourcepath):
        print fname
	runname = int(fname.split('/')[7][1:])
        if runname < 140 or runname == 214 or runname ==151 or runname == 145: continue
        #if not 'r0201' in fname: continue

	#get runname from fname by splitting the string at '/' and take the second to last (-2)
	runname = fname.split('/')[-2]

        # create outfile
	out = open("%s/%s_hitscores.txt" % (outdir,runname),'w')




	#calc the hitscores for each frame in cxifile
	hitscores = hitfind_cxi_file(fname,initial=i,final=f)

	# write 'framenr hiscore' for each frame/pattern 
	for m,s in hitscores:
	    out.write('%06d %6d\n' % (m,s) )

	#close file
	out.close()


filterwindow = """0,0,0,0,0,0,0,0.00018801,0.00093433,0.0014185,0.0015783,0.0014185,0.00093433,0.00018801,0,0,0,0,0,0,0
0,0,0,0,0,0.00054392,0.0021,0.0031052,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031052,0.0021,0.00054392,0,0,0,0,0
0,0,0,1.8176e-05,0.0015656,0.0031288,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031288,0.0015656,1.8176e-05,0,0,0
0,0,1.8176e-05,0.001987,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.001987,1.8176e-05,0,0
0,0,0.0015656,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0015656,0,0
0,0.00054392,0.0031288,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031288,0.00054392,0
0,0.0021,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0021,0
0.00018801,0.0031052,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031052,0.00018801
0.00093433,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.00093433
0.0014185,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0014185
0.0015783,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0015783
0.0014185,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0014185
0.00093433,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.00093433
0.00018801,0.0031052,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031052,0.00018801
0,0.0021,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0021,0
0,0.00054392,0.0031288,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031288,0.00054392,0
0,0,0.0015656,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0015656,0,0
0,0,1.8176e-05,0.001987,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.001987,1.8176e-05,0,0
0,0,0,1.8176e-05,0.0015656,0.0031288,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031288,0.0015656,1.8176e-05,0,0,0
0,0,0,0,0,0.00054392,0.0021,0.0031052,0.0031831,0.0031831,0.0031831,0.0031831,0.0031831,0.0031052,0.0021,0.00054392,0,0,0,0,0
0,0,0,0,0,0,0,0.00018801,0.00093433,0.0014185,0.0015783,0.0014185,0.00093433,0.00018801,0,0,0,0,0,0,0"""
