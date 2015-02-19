"""Displays the results of the analysis to the user, using images and plots.
"""

from Qt import QtGui, QtCore
from interface import Interface
import sys

def start_interface():
    """Initialize and show the Interface"""
    QtCore.QCoreApplication.setOrganizationName("SPI")
    QtCore.QCoreApplication.setOrganizationDomain("spidocs.rtfd.org")
    QtCore.QCoreApplication.setApplicationName("Hummingbird")
    app = QtGui.QApplication(sys.argv)
    mw = Interface()
    mw.show()
    ret = app.exec_()
    sys.exit(ret)
