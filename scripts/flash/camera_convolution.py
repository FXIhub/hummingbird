import numpy
import scipy
import scipy.misc
import scipy.ndimage
import matplotlib.pyplot
from eke import tools
import os
import re

# #nrs = [1]
# #filename = "/asap3/flash/gpfs/bl1/2017/data/11001733/scratch_cc/tmp/pos1.bmp"
# filename = "pos1.bmp"
# filenames = [filename]

# images = [scipy.misc.imread(f).mean(axis=2) for f in filenames]

catcher_size_pixels = 561
catcher_size_m = 0.025
pixel_size = catcher_size_m / catcher_size_pixels

upsampling = 8

data_dir = "zscan2"
filenames = [f for f in os.listdir(data_dir) if re.search("^20170303_[0-9]{4}.bmp$", f)]
filenames = sorted(filenames)
images = numpy.array([scipy.misc.imread(os.path.join(data_dir, f)).mean(axis=2) for f in filenames])
#
run_number = numpy.array([int(re.search("^20170303_([0-9]{4}).bmp$", f).groups()[0]) for f in filenames])

light_images = scipy.misc.imread(os.path.join(data_dir, "20170303_0235.bmp"))

good_images_bool = numpy.array([image.sum() for image in images]) < 3e7
images = images[good_images_bool]
run_number = run_number[good_images_bool]
#filenames = filenames[numpy.arange(len(good_images_bool))[good_images_bool]]

#template = tools.round_mask(images[0].shape, 15.) # injector looks like 15 pixels in radius
template = tools.round_mask([upsampling * s for s in images[0].shape], 15.*upsampling) # injector looks like 15 pixels in radius
template_ft = numpy.fft.fft2(numpy.fft.fftshift(template))


mask = numpy.zeros(images[0].shape)
mask[200:600,250:750] = 1
mask_large = numpy.zeros([upsampling*s for s in images[0].shape])
mask_large[200*upsampling:600*upsampling,250*upsampling:750*upsampling] = 1

def find_center(image):
    image_ft = numpy.fft.fftshift(tools.pad_with_zeros(numpy.fft.fftshift(numpy.fft.fft2(numpy.fft.fftshift(image))),
                                    [upsampling*s for s in image.shape]))
    conv_ft = template_ft*image_ft
    conv = numpy.fft.ifftshift(numpy.fft.ifft2(conv_ft))
    center = numpy.unravel_index((abs(conv)*mask_large).argmax(), conv.shape)
    print "done"
    return numpy.array(center[::-1]) / float(upsampling)


centers = numpy.array([find_center(image) for image in images]) * pixel_size

poly_coeff = numpy.polyfit(centers[:, 0], centers[:, 1], 1)
line_x = numpy.linspace(0.0228, 0.0240, 1000)
line_y = poly_coeff[1] + poly_coeff[0]*line_x

line_origin = numpy.array([0, poly_coeff[1]])
line_vector = numpy.array([1, poly_coeff[0]]) / numpy.sqrt((numpy.array([1, poly_coeff[0]])**2).sum())

dot_prod = (line_vector[numpy.newaxis, :] * (centers-line_origin[numpy.newaxis, :])).sum(axis=1)
projected_centers = line_origin[numpy.newaxis, :] + dot_prod[:, numpy.newaxis]*line_vector[numpy.newaxis, :]


fig = matplotlib.pyplot.figure("Center path")
fig.clear()
ax = fig.add_subplot(111)
ax.plot(centers[:, 0], centers[:, 1])
ax.plot(projected_centers[:, 0], projected_centers[:, 1], 'o', color="black")
for i in range(len(run_number)):
    ax.text(centers[i, 0], centers[i, 1], str(run_number[i]))
ax.plot(line_x, line_y)
ax.set_aspect("equal")
fig.canvas.draw()

figgrid = (4, 6)
window_size = 80
fig = matplotlib.pyplot.figure("Image and center")
fig.clear()
for i in range(len(images)):
    ax = fig.add_subplot(figgrid[0], figgrid[1], i+1)
    ax.imshow(images[i]*mask, vmin=0, vmax=30)
    ax.plot(centers[i, 0]/pixel_size, centers[i, 1]/pixel_size, "+", ms=2, color="black")
    # ax.set_xlim((centers[i, 0]/pixel_size-window_size/2, centers[i, 0]/pixel_size+window_size/2))
    # ax.set_ylim((centers[i, 1]/pixel_size-window_size/2, centers[i, 1]/pixel_size+window_size/2))
    ax.set_xlim((centers[0, 0]/pixel_size-window_size/2, centers[0, 0]/pixel_size+window_size/2))
    ax.set_ylim((centers[0, 1]/pixel_size-window_size/2, centers[0, 1]/pixel_size+window_size/2))
    fig.canvas.draw()


print("\n".join(["{0}: {1:.5}".format(rn, dp*1e6) for rn, dp in zip(run_number, dot_prod - dot_prod[-1])]))

fig = matplotlib.pyplot.figure("Center in same image")
fig.clear()
ax = fig.add_subplot(111)
ax.imshow(images[0]*mask, vmin=0, vmax=30)
ax.plot(centers[:, 0]/pixel_size, centers[:, 1]/pixel_size, 'o', color="black")
fig.canvas.draw()
