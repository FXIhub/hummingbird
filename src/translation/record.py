def addRecord(values, name, data, unit=None):
    values[name] = Record(name,data, unit)

class Record(object):
    def __init__(self, name, data, unit):
        self.name = name
        self.data = data
        self.unit = unit
