"""Contains all the Designer created widgets, one per module"""
from interface.Qt import loadUiType
import os

uidir = os.path.dirname(os.path.realpath(__file__))
Ui_addBackend, base = loadUiType(uidir + '/add_backend.ui')
Ui_preferences, base = loadUiType(uidir + '/preferences.ui')
Ui_plotWindow, base = loadUiType(uidir + '/plot_window.ui')
Ui_imageWindow, base = loadUiType(uidir + '/image_window.ui')

from interface.ui.data_window import DataWindow # pylint: disable=unused-import
from interface.ui.add_backend import AddBackendDialog # pylint: disable=unused-import
from interface.ui.preferences import PreferencesDialog # pylint: disable=unused-import
from interface.ui.plot_window import PlotWindow # pylint: disable=unused-import
from interface.ui.image_window import ImageWindow # pylint: disable=unused-import
