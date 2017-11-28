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
    """
    Generic storage class for a name/data pair extracted from an event

    Accept both values and functions for data. In the latter case the
    first time data is accessed evaluate the function and return its result.
    """
    def __init__(self, name, data, unit=None):
        self.name  = name
        self.data  = data
        self.unit  = unit

    @property
    def data(self):
        # If self._data is a function first retrieve
        # the result of the function and use that as the value.
        # This allows lazy evaluation records such
        # that unused records are not unnecessarily costly.
        if hasattr(self._data, '__call__'):
            self._data = self._data()
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
