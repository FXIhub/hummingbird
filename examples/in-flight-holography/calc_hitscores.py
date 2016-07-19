import numpy
import glob
import double_hitfinder
from os import listdir

filepath = '/home/toli/Python/Test_and_Learning/data/'
image_names = listdir(filepath)
print 'found data:'
print image_names
#image_names = glob.glob('r0074*.dat')
print 'load first image'
img = numpy.loadtxt(filepath + image_names[0], delimiter = '\t')
print 'generate masks'
mask,gmask,centermask = double_hitfinder.generate_masks(img)
print 'calculating hitscores for files:'
print image_names

for idx, imname in enumerate(image_names):
    print 'loading image #' + str(idx)
    img = numpy.loadtxt(filepath + imname, delimiter = '\t')
    hitscore = double_hitfinder.double_hit_finder(img,mask,gmask,centermask,imname=imname)
    print imname, hitscore
