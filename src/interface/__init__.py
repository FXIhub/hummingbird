"""Displays the results of the analysis to the user, using images and plots.
"""

from Qt import QtGui, QtCore
from gui import GUI
import sys
import signal

def start_interface():
    """Initialize and show the Interface"""
    # Catch Ctrl+c and such
    signal.signal(signal.SIGINT, sigint_handler)
    QtCore.QCoreApplication.setOrganizationName("SPI")
    QtCore.QCoreApplication.setOrganizationDomain("spidocs.rtfd.org")
    QtCore.QCoreApplication.setApplicationName("Hummingbird")
    app = QtGui.QApplication(sys.argv)
    GUI().show()
    sys.exit(app.exec_())

def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    if QtGui.QMessageBox.question(None, '', "Are you sure you want to quit?",
                                  QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                                  QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
        GUI.instance.closeEvent(None)


