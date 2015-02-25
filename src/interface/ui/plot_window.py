from interface.Qt import QtGui, QtCore
from interface.ui import Ui_plotWindow
import pyqtgraph

class PlotWindow(QtGui.QMainWindow, Ui_plotWindow):
    def __init__(self, parent = None):
        QtGui.QMainWindow.__init__(self,parent)
        self.setupUi(self)
        self.plot = pyqtgraph.PlotWidget(self.plotFrame)
        self.plot.plot([1,2,3,2,3,1])
        layout = QtGui.QVBoxLayout(self.plotFrame)
        layout.addWidget(self.plot)
        icon = QtGui.QPixmap("/Users/filipe/Caravaggio/src/hummingbird/src/interface/images/logo_48.png"); 
        self.logoLabel.setPixmap(icon)
