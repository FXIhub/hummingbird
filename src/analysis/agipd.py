# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import print_function, absolute_import # Compatibility with python 2 and 3
import numpy as np
from backend import ureg
from backend import add_record


def get_panel(evt, record, index):
    """
    Returns one out of the 16 individual panels of the AGIPD by indexing the raw (16,512,128) array.
    """
    return add_record(evt['analysis'], 'analysis', 'AGIPD_panel_%d' %(index), record.data[:, index])

