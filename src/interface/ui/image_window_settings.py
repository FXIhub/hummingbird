import interface.ui
from interface.Qt import QtCore, QtGui

class ImageWindowSettings(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.ui = interface.ui.Ui_imageWindowSettings()
        self.ui.setupUi(self)

