#    This file is part of cfelpyutils.
#
#    cfelpyutils is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    cfelpyutils is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with cfelpyutils.  If not, see <http://www.gnu.org/licenses/>.
"""
Utilities for CrystFEL-style geometry files.

This module contains utilities for the processing of CrystFEL-style geometry
files.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy


def apply_geometry_from_file(data_as_slab, geometry_filename):
    """Parses a geometry file and applies the geometry to data.

    Parses a geometry file and applies the geometry to detector data in 'slab' format. Turns a 2d array of pixel
    values into an array containing a representation of the physical layout of the detector, keeping the origin of
    the reference system at the beam interaction point.

    Args:

        data_as_slab (numpy.ndarray): the pixel values to which geometry is to be applied.

        geometry_filename (str): geometry filename.

    Returns:

        im_out (numpy.ndarray data_as_slab.dtype): Array containing a representation of the physical layout of the
        detector, with the origin of the  reference system at the beam interaction point.
    """

    yx, slab_shape, img_shape = pixel_maps_for_image_view(geometry_filename)
    im_out = numpy.zeros(img_shape, dtype=data_as_slab.dtype)

    im_out[yx[0], yx[1]] = data_as_slab.ravel()
    return im_out


def apply_geometry_from_pixel_maps(data_as_slab, yx, im_out=None):
    """Applies geometry in pixel map format to data.

    Applies geometry, in the form of pixel maps, to detector data in 'slab' format. Turns a 2d array of pixel values
    into an array containing a representation of the physical layout of the detector, keeping the origin of the
    reference system at the beam interaction point.

    Args:

        data_as_slab (numpy.ndarray): the pixel values to which geometry is to be applied.

        yx (tuple): the yx pixel maps describing the geometry of the detector; each map is a numpy.ndarray.

        im_out (Optional[numpy.ndarray]): array to hold the output; if not provided, one will be generated
        automatically.

    Returns:

        im_out (numpy.ndarray data_as_slab.dtype): Array containing a representation of the physical layout of the
        detector, with the origin of the  reference system at the beam interaction point.
    """

    if im_out is None:
        im_out = numpy.zeros(data_as_slab.shape, dtype=data_as_slab.dtype)

    im_out[yx[0], yx[1]] = data_as_slab.ravel()
    return im_out


def pixel_maps_for_image_view(geometry_filename):
    """Parses a geometry file and creates pixel maps for pyqtgraph visualization.

    Parse the geometry file and creates pixel maps for an  array in 'slab' format containing pixel values. The pixel
    maps can be used to create a representation of the physical layout of the detector in a pyqtgraph ImageView
    widget (i.e. they apply the detector geometry setting the origin of the reference system is in the top left corner
    of the output array).

    Args:

        geometry_filename (str): geometry filename.

    Returns:

        (y, x) (numpy.ndarray int, numpy.ndarray int): pixel maps

        slab_shape tuple (int, int): shape of the original geometry uncorrected array (the pixel values in "slab"
        format).

        img_shape tuple (int, int): shape of the array needed to contain the representation of the physical layout
        of the detector.
    """

    pixm = pixel_maps_from_geometry_file(geometry_filename)
    x, y = pixm[0], pixm[1]
    slab_shape = x.shape

    # find the smallest size of cspad_geom that contains all
    # xy values but is symmetric about the origin
    n = 2 * int(max(abs(y.max()), abs(y.min()))) + 2
    m = 2 * int(max(abs(x.max()), abs(x.min()))) + 2

    # convert y x values to i j values
    i = numpy.array(y, dtype=numpy.int) + n//2 - 1
    j = numpy.array(x, dtype=numpy.int) + m//2 - 1

    yx = (i.flatten(), j.flatten())
    img_shape = (n, m)
    return yx, slab_shape, img_shape


def parse_xy(string):
    """Extracts x and y values from strings in a geometry file.

    Parse the x, y values from strings in that have the format: '1x + 2.0y'.

    Args:

        string (str): the string to be parsed.

    Returns:

        x, y (float, float): the values of x and y.
    """

    x = y = 0

    if string.find('x') is not -1:
        xs = string.split('x')[0].split(' ')[-1]
        if len(xs) > 0:
            x = float(xs)
        else:
            x = 1.

    if string.find('y') is not -1:
        ys = string.split('y')[0].split(' ')[-1]
        if len(ys) > 0:
            y = float(ys)
        else:
            y = 1.
    return x, y


def pixel_maps_from_geometry_file(fnam):
    """Parses a geometry file and creates pixel maps.

    Extracts pixel maps from a CrystFEL-style geometry file. The pixel maps can be used to create a representation of
    the physical layout of the detector, keeping the origin of the  reference system at the beam interaction
    point.

    Args:

        fnam (str): geometry filename.

    Returns:

        x,y,r (numpy.ndarray float, numpy.ndarray float, numpy.ndarray float): slab-like pixel maps with
        respectively x, y coordinates of the pixel and distance of the pixel from the center of the reference system.
    """

    f = open(fnam, 'r')
    f_lines = f.readlines()
    f.close()

    keyword_list = ['min_fs', 'min_ss', 'max_fs', 'max_ss', 'fs', 'ss', 'corner_x', 'corner_y']

    detector_dict = {}

    panel_lines = [x for x in f_lines if '/' in x and
                   len(x.split('/')) == 2 and x.split('/')[1].split('=')[0].strip() in keyword_list and
                   'bad_' not in x.split('/')[0].strip()]

    for pline in panel_lines:
        items = pline.split('=')[0].split('/')
        panel = items[0].strip()
        prop = items[1].strip()
        if prop in keyword_list:
            if panel not in detector_dict.keys():
                detector_dict[panel] = {}
            detector_dict[panel][prop] = pline.split('=')[1].split(';')[0]

    parsed_detector_dict = {}

    for p in detector_dict.keys():

        parsed_detector_dict[p] = {}

        parsed_detector_dict[p]['min_fs'] = int(detector_dict[p]['min_fs'])
        parsed_detector_dict[p]['max_fs'] = int(detector_dict[p]['max_fs'])
        parsed_detector_dict[p]['min_ss'] = int(detector_dict[p]['min_ss'])
        parsed_detector_dict[p]['max_ss'] = int(detector_dict[p]['max_ss'])
        parsed_detector_dict[p]['fs'] = list(parse_xy(detector_dict[p]['fs']))
        parsed_detector_dict[p]['ss'] = list(parse_xy(detector_dict[p]['ss']))
        parsed_detector_dict[p]['corner_x'] = float(detector_dict[p]['corner_x'])
        parsed_detector_dict[p]['corner_y'] = float(detector_dict[p]['corner_y'])

    max_slab_fs = numpy.array([parsed_detector_dict[k]['max_fs'] for k in parsed_detector_dict.keys()]).max()
    max_slab_ss = numpy.array([parsed_detector_dict[k]['max_ss'] for k in parsed_detector_dict.keys()]).max()

    x = numpy.zeros((max_slab_ss+1, max_slab_fs+1), dtype=numpy.float32)
    y = numpy.zeros((max_slab_ss+1, max_slab_fs+1), dtype=numpy.float32)

    for p in parsed_detector_dict.keys():
        # get the pixel coords for this asic
        i, j = numpy.meshgrid(numpy.arange(parsed_detector_dict[p]['max_ss'] - parsed_detector_dict[p]['min_ss'] + 1),
                              numpy.arange(parsed_detector_dict[p]['max_fs'] - parsed_detector_dict[p]['min_fs'] + 1),
                              indexing='ij')

        #
        # make the y-x ( ss, fs ) vectors, using complex notation
        dx = parsed_detector_dict[p]['fs'][1] + 1J * parsed_detector_dict[p]['fs'][0]
        dy = parsed_detector_dict[p]['ss'][1] + 1J * parsed_detector_dict[p]['ss'][0]
        r_0 = parsed_detector_dict[p]['corner_y'] + 1J * parsed_detector_dict[p]['corner_x']
        #
        r = i * dy + j * dx + r_0
        #
        y[parsed_detector_dict[p]['min_ss']: parsed_detector_dict[p]['max_ss'] + 1,
            parsed_detector_dict[p]['min_fs']: parsed_detector_dict[p]['max_fs'] + 1] = r.real

        x[parsed_detector_dict[p]['min_ss']: parsed_detector_dict[p]['max_ss'] + 1,
            parsed_detector_dict[p]['min_fs']: parsed_detector_dict[p]['max_fs'] + 1] = r.imag

    r = numpy.sqrt(numpy.square(x) + numpy.square(y))

    return x, y, r


def coffset_from_geometry_file(fnam):
    """Extracts detector distance information from a geometry file.

    Extracts detector distance offset information from a CrystFEL-style geometry file.

    Args:

        fnam (str): geometry filename.

    Returns:

        coffset (float): the detector distance offset
    """

    f = open(fnam, 'r')
    f_lines = f.readlines()
    f.close()

    coffset = 0.0

    for line in f_lines:
        if line.startswith('coffset'):
            coffset = float(line.split('=')[1].split(';')[0])

    return coffset


def res_from_geometry_file(fnam):
    """Extracts pixel resolution information from a geometry file.

    Extracts pixel resolution information from a CrystFEL-style geometry file.

    Args:

        fnam (str): geometry filename.

    Returns:

        res (float): the pixel resolution
    """

    f = open(fnam, 'r')
    f_lines = f.readlines()
    f.close()

    res = None

    for line in f_lines:
        if line.startswith('res'):
            res = float(line.split('=')[1].split(';')[0])

    return res
