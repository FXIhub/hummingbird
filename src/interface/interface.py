"""Displays the results of the analysis to the user, using images and plots.
"""
from Qt import QtGui, QtCore
import sys

class Interface(QtGui.QMainWindow):
    """Main Window Class

    Contains only menus and toolbars. The plots will be in their own windows.
    """
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

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

