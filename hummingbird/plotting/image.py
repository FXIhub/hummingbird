# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""A plotting module for images"""
import numpy as np

from hummingbird import ipc

images = {}
def plotImage(record, history=10, vmin=None, vmax=None, log=False, mask=None, msg=None, alert=False, name=None, group=None, send_rate=None, roi_center=None, roi_diameters=None, aspect_ratio=None, sum_over=False, max_over=False):
    """Plotting an image.

    Args:
        :record(Record): record.data is plotted as an image

    Kwargs:
        :history(int):  Length of history buffer
        :vmin(float):   Minimum value
        :vmax(float):   Maximum value
        :log(boolean):  Plot image in log scale (needs restart of GUI, only works with grayscale colormap)
        :mask(boolean or int): Multiply image with mask
        :sum_over(boolean): Run a cumulative mean of the results in the front-end
    """
    if record is None:
        return

    if name is None:
        n = record.name
    else:
        n = name
    if group is None:
        group = record.group
    if(not n in images):
        ipc.broadcast.init_data(n, data_type='image', history_length=history, vmin=vmin, vmax=vmax, log=log, group=group, sum_over=sum_over, max_over=max_over)
        images[n] = True
    image = record.data
    sh = image.shape
    if (image.ndim == 3):
        image = image.reshape(sh[0]*sh[2], sh[1])
    if mask is None:
        mask = np.ones_like(image)
    ipc.new_data(n, image*mask, msg=msg, alert=alert, send_rate=send_rate, center=roi_center, diameters=roi_diameters, aspect_ratio=aspect_ratio, sum_over=sum_over, log=log, max_over=max_over)
