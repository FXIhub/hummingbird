# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Wraps the preferences Dialog"""
from ..Qt import QtCore, QtGui
from . import Ui_preferences


class PreferencesDialog(QtGui.QDialog, Ui_preferences):
    """Wraps the preferences Dialog"""
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent, QtCore.Qt.WindowTitleHint)
        self.setupUi(self)
        settings = QtCore.QSettings()
        self.outputPath.setText(settings.value("outputPath"))
        self.fontSize.setValue(int(settings.value("plotFontSize")))
        self.plotRefresh.setValue(int(settings.value("plotRefresh")))
