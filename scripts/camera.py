
# coding: utf-8

# In[ ]:

import numpy as np
import scipy as sp
import scipy.misc as misc
import scipy.ndimage as ndi
import matplotlib.pyplot as plt
get_ipython().magic(u'matplotlib notebook')


# In[ ]:

nrs = [1]
filename = '../camera/pos%d.bmp' 
filenames = [filename %r for r in nrs]


# In[ ]:

images = [misc.imread(f).mean(axis=2) for f in filenames]


# In[ ]:

mask = np.zeros(images[0].shape)
mask[300:500,350:650] = 1


# In[ ]:

diameter = 1.5 # mm
diameter_px = 2.*np.sqrt(697. / np.pi)
pixelsize = diameter / float(diameter_px)


# In[ ]:

index = 0


# In[ ]:

cxs = []
cys = []
Ns  = []
Bs  = []
for i in range(len(images)):
    image  = images[index]
    imagec = ndi.gaussian_filter(image - np.median(image), 2)
    binary = (imagec*mask)>5
    Bs.append(binary)
    Ns.append(binary.sum())
    cy,cx  = ndi.measurements.center_of_mass(binary)
    cxs.append(cx*pixelsize)
    cys.append(cy*pixelsize)
cx_array = np.array(cxs)
cy_array = np.array(cys)
Ns_array = np.array(Ns)
B_array  = np.array(Bs)


# In[ ]:

k = 0
plt.figure()
plt.scatter([cx_array[k]/pixelsize],[cy_array[k]/pixelsize], 10, color='r')
plt.imshow(images[k], vmin=0, vmax=50, cmap='gray')
plt.show()


# In[ ]:

plt.figure()
plt.plot(range(cx_array.shape[0]), cx_array-cx_array[0], label='horizontal')
plt.plot(range(cy_array.shape[0]), cy_array-cy_array[0], label='vertical')
plt.ylabel('Distance [mm]')
plt.xlabel('Position index')
plt.legend()
plt.show()


# In[ ]:



