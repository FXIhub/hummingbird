# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

from hummingbird.backend import add_record


def someAnalysis(evt, type, key, keyword=None):
    """An example for an analysis module. Please document here in the docstring:

    - what the module is doing
    - what arguments need to be passed
    - what the module returns (adds to the event variable)
    - who the authors are

    Args:
        :evt:       The event variable
        :type(str): The event type
        :key(str):  The event key

    Kwargs:
        :keyword(type): Kewyword description (default = None)

    :Authors: 
        Name (email), 
        Name (email)
    """

    # ADD YOUR CODE HERE
    # 
    # something = ....

    add_record(evt["analysis"], "analysis", "somethingNew"+key, something, unit=some_unit)
