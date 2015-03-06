from interface.Qt import QtGui, QtCore
from interface.ui import Ui_preferences

class PreferencesDialog(QtGui.QDialog, Ui_preferences):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self,parent,QtCore.Qt.WindowTitleHint)
        self.setupUi(self)
        settings = QtCore.QSettings()
        self.outputPath.setText(settings.value("outputPath"))
