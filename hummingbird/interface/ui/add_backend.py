# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Dialog to add data sources to the GUI"""
from ..Qt import QtCore, QtGui
from . import Ui_addBackend


class AddBackendDialog(QtGui.QDialog, Ui_addBackend):
    """Dialog to add data sources to the GUI"""
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent, QtCore.Qt.WindowTitleHint)
        self.setupUi(self)
