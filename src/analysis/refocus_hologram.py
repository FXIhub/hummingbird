#!/usr/bin/env python
import sys
import os
from eke import tools
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import h5py
import numpy
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
#from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
#from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import argparse
from numpy.fft import *
from scipy.ndimage import label, gaussian_filter,center_of_mass
from skimage.morphology import binary_erosion as binary_erode
from skimage.morphology import binary_dilation
from pylab import subplots
from matplotlib.colors import LogNorm
from scipy.ndimage import sobel
from skimage.feature import canny
from backend.record import add_record

def refocus_hologram_evt(evt, type, key):
        img = evt[type][key].data.copy()
        img = img[513-256:513+256,584-256:584+256]
        image_to_show, centroidsmap, centroids, focal_distance, intensity = refocus_hologram(img)
        if image_to_show.sum() > 0:
                add_record(evt["analysis"], "analysis", "focused_CC", image_to_show)
                add_record(evt["analysis"], "analysis", "focus distance", focal_distance[intensity.argmax()]*5E-7)
                add_record(evt["analysis"], "analysis", "hologram_score", intensity.max() )
        

def rest(ar,s):
	ar[ar<numpy.median(ar)*s] = 0
	ar[256-5:256+5] = ar.max()
	ar[216-26:296+26,216-26:296+26] = ar.max()
	for i in range(2):
	    ar = binary_erode(ar>0)
	ar = gaussian_filter(ar*4,2)
	l,n = label(ar>0)
	ramp = (l == l[256,256])*1
	for i in range(2):
	    ramp = binary_dilation(ramp>0)
	ramp = (ramp <1)
	
	l[l==l[256,256]] =0
	l,n = label(l>0)
	for i in range(1,n+1):	    
	    if (l[l==i] >0).sum() < 30:
		l[l==i]=0

	l,n = label(l>0)
	
	return l,n


def refocus_hologram(input_image,wavelength=5.3E-9,pixelsize=75E-6,detectordistance=150E-3,limit=60,stepsize=5E-7):
    	input_image[input_image < 400] = 0
	input_image[input_image > 10000] =0
	
        [Xrange,Yrange] = input_image.shape
	p = numpy.linspace(-Xrange/2, Xrange/2-1, Xrange)
	q = numpy.linspace(-Yrange/2, Yrange/2-1, Yrange)
	pp, qq = numpy.meshgrid(p, q)

	phase_matrix = (2*numpy.pi/wavelength)*numpy.sqrt(1-((pixelsize/detectordistance)**2)*(qq**2 + pp**2))

	img_shifted = fftshift(input_image)
	phase_matrix_shifted = fftshift(phase_matrix)
	added_recon = numpy.zeros((limit,512,512),dtype='complex128')
	
	for phase in range(0,limit):
	    img_propagated = img_shifted * numpy.exp(1.j*phase*stepsize*phase_matrix_shifted)
	    recon1 = fftshift(ifft2(img_propagated))	    
	    added_recon[phase]=abs(recon1)

	ttt = added_recon[0].copy()
	ttt[abs(ttt)<numpy.median(abs(ttt))*6] = 0
	ttt[231:291,221:301] = 0
	ttt[251:261,:] = 0
	r = sobel(abs(ttt)) > 0
	for i in range(4):
	    r = binary_dilation(r)
	for i in range(7):
	    r = binary_erode(r)

	h,m  = label(r)
	for i in range(m):
	    if (h == (i+1)).sum() < 20:
		h[h==(i+1)]=0
		
	r = (r>0)
	ar = added_recon[:limit].max(axis=0)
	bar = ar.copy()
	l,n = rest(ar,2)
	if n==0:
	    l,n=rest(ar,1)

	if n > 8:
	    for i in range(6):
		l = binary_erode(l > 0)

	l += r
	l,n = label(l>0)
	

	for i in range(1,n+1):
	    if ((l[l==i] >0)*1).sum() < 50:		
		l[l==i]=0
	    
	l,n = label(l>0)
	l = l

	centroidsmap = numpy.zeros_like(l)
	
	if n:
	    centroids = numpy.zeros((n,2))
	    for i in range(1,n+1):
		centroids[i-1] = center_of_mass((l==i)*abs(bar))
                for cc in range(len(centroids[i-1])): 
                        centroids[i-1][cc] = numpy.round(centroids[i-1][cc]).astype(int)
                print centroids[i-1]
		centroidsmap[int(centroids[i-1][0])-30:int(centroids[i-1][0])+30,int(centroids[i-1][1])-30:int(centroids[i-1][1])+30] = 1
	    variance = numpy.zeros((limit,n))
	    maxv = numpy.zeros((limit,n))
	    for i in range(limit):
		for j in range(n):
		    variance[i][j] = (abs(added_recon[i][int(centroids[j][0])-30:int(centroids[j][0]+30),int(centroids[j][1])-30:int(centroids[j][1])+30])).var()
		    maxv[i][j] = (abs(added_recon[i])*(l==j+1)).max()
		    
	    love = numpy.zeros(n)
	    rat = numpy.zeros(n)
	    
	    for i in range(n):
		love[i] = variance[:,i].argmax()
		rat[i] = variance[:,i].max()
		if variance[:,i].max() < 1:
		    love[i] = maxv[:,i].argmax()
		    rat[i] = maxv.max()
		    
	    for i in range(rat.shape[0]):
		if numpy.isnan(rat[i]):
		    rat[i] = 0

	    sett = rat.argmax()
	    
	    image_to_show = numpy.log10(abs(added_recon[int(love[sett])]))+centroidsmap*2
										
	    print love,rat
	    return image_to_show, centroidsmap, centroids, rat, love

        
	return numpy.zeros_like(input_image), numpy.zeros_like(input_image), numpy.array([]),numpy.array([0,-1]),numpy.array([0,-1])
