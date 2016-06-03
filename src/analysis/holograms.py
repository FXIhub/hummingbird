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

def gaussian_mask(dim1, dim2, centerX, centerY, sigma):
    [X, Y] = numpy.meshgrid(numpy.arange(dim1, dtype=numpy.float64),numpy.arange(dim2, dtype=numpy.float64))
    X -= centerX
    Y -= centerY
    mask = numpy.exp(-(X**2+Y**2)/(2*sigma**2))
    return mask

def euclid(dim1, dim2, center1, center2, radius):
    [X, Y] = numpy.meshgrid(numpy.arange(dim1, dtype=numpy.float64),numpy.arange(dim2, dtype=numpy.float64))
    X -= center1
    Y -= center2
    mask = ( (X**2 + Y**2) > radius**2).astype('double')
    return mask

def generate_masks(pattern,scattMaskRadius=50,scattMaskCenterX=523, scattMaskCenterY=523, background=30, slit=17):
    [dimy,dimx] = pattern.shape
    mask = euclid(dimx, dimx, scattMaskCenterX, scattMaskCenterY, scattMaskRadius)
    mask[518:518+slit,:] = 0
    mask[370:480,520:650] = 0
    mask[:370,520:580] = 0
    mask[590:600,505:515] = 0    
    mask = fliplr(rot90(mask,3))
    H = numpy.array([map(float,line.strip('\n').split(',')) for line in filterwindow.split('\n')])
    blurred = imfilter(mask,H)
    newMask = 1-(blurred<0.99)
    H2 = H
    newMask = imfilter(newMask.astype('double'),H2)
    mask *= newMask
    gMask = gaussian_mask(dimx,dimx,400,700,300)
    centerMask = euclid(dimx,dimx,numpy.round(dimx/2),numpy.round(dimx/2),150)
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

def holographic_hitfinder_evt(evt, type, key,mask,gMask,centerMask,th=3):
    img = evt[type][key].data
    hitData = numpy.zeros((1044,1044))
    hitData[:513,:] = img[:513,:]
    hitData[-514:,:] = img[-514:,:]
    hitData *= mask
    hitData *= gMask	
    holoData = fftshift(numpy.abs(ifft2(hitData)))
    holoData *= centerMask
    hData = holoData[holoData>0]
    med = numpy.median(hData)
    hitS = 1.*(holoData > med*th)
    hitS[513:533,350:700] = 0
    hitS[:,518:528] = 0
    hitS = gaussian_filter(hitS,sigma=2)
    hitS[hitS<0.65] = 0
    hitS[hitS > 0.1] = 1
    hitScore = hitS.sum()
    out = numpy.zeros((1027,1044))
    out[:513,:] = hitS[:513,:]
    out[-514:,:] = hitS[-514:,:]
    add_record(evt["analysis"], "analysis", "hologramScore", hitScore)
    add_record(evt["analysis"], "analysis", "hologram", out)



def hitfind_cxi_file(fname, attribute='/entry_1/image_1/detector_corrected/data',initial=0, final=400):
    #open h5 file
    f = h5py.File(fname,'r')
    runname = fname.split('/')[7]
    #data is 3D structure, N x dimy x dimx, frame = dimy x dimx
    #N=number of frames/shots/diff_patterns, dimy=pixels_in_y, dimx=pixels_in_x
    print f[attribute].shape
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
