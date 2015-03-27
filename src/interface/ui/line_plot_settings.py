"""Dialog to change the line plot settings"""
from interface.Qt import QtGui, QtCore
from interface.ui import Ui_linePlotSettings

class LinePlotSettings(QtGui.QDialog, Ui_linePlotSettings):
    """Dialog to change the line plot settings"""
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)
