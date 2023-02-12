# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
import inspect


def load_spimage():
    """Loading the ```libspimage``` module if available"""
    try:
        import spimage
        success = True
        module  = spimage
    except ImportError:
        print("Warning: libspimage not found! The function '%s' is dependent on libspimage (https://github.com/FilipeMaia/libspimage)" %inspect.stack()[1][3])
        success = False
        module = None
    return success, module

def load_condor():
    """Loading the ```condor``` module if available"""
    try:
        import condor
        success = True
        module  = condor
    except ImportError:
        print("Warning: condor not found! The function '%s' is dependent on condor (https://github.com/mhantke/condor)" %inspect.stack()[1][3])
        success = False
        module = None
    return success, module
