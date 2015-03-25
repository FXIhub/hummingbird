"""Generic storage class for a name/data pair extracted from an event"""

def add_record(values, name, data, unit=None):
    """Convenience function to add a new Record
    to an existing Records dictionary."""
    values[name] = Record(name, data, unit)

class Record(object):
    """Generic storage class for a name/data pair extracted from an event"""
    def __init__(self, name, data, unit=None):
        self.name = name
        self.data = data
        self.unit = unit
