# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Generic storage class for a name/data pair extracted from an event"""

def add_record(values, group, name, data, unit=None):
    """Convenience function to add a new Record
    to an existing Records dictionary."""
    if data is not None:
        values[name] = Record(group + " / " + name, data, unit)
    else:
        values[name] = None
    return values[name]
    
class Record(object):
    """Generic storage class for a name/data pair extracted from an event"""
    def __init__(self, name, data, unit=None):
        self.name  = name
        self.data  = data
        self.unit  = unit
        #print "group: ", name.split('/')[0]
        #print "name: ", name.split('/')[1]
        # try:
        #     self.group = name.split('/')[0]
        #     self.key   = name.split('/')[1]
        # except IndexError:
        #     self.group = None
        #     self.key = None
