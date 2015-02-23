from interface.Qt import QtGui, QtCore
from interface.ui import Ui_addBackend

class AddBackendDialog(QtGui.QDialog, Ui_addBackend):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self,parent,QtCore.Qt.WindowTitleHint)
        self.setupUi(self)
