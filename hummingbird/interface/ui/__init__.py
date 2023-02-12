"""Contains all the Designer created widgets, one per module"""
import os
import sys

from ..Qt import loadUiType

# Append the images to the module search path so we can find the resources file
sys.path.append(os.path.dirname(__file__)+"/../images/")

uidir = os.path.dirname(os.path.realpath(__file__))
Ui_addBackend, base = loadUiType(uidir + '/add_backend.ui')
Ui_preferences, base = loadUiType(uidir + '/preferences.ui')
Ui_plotWindow, base = loadUiType(uidir + '/plot_window.ui')
Ui_imageWindowSettings, base = loadUiType(uidir + '/image_window_settings.ui')
Ui_imageWindow, base = loadUiType(uidir + '/image_window.ui')
Ui_linePlotSettings, base = loadUiType(uidir + '/line_plot_settings.ui')

from .add_backend import AddBackendDialog  # pylint: disable=unused-import
from .data_window import DataWindow  # pylint: disable=unused-import
from .image_window import ImageWindow  # pylint: disable=unused-import
from .line_plot_settings import LinePlotSettings  # pylint: disable=unused-import
from .plot_window import PlotWindow  # pylint: disable=unused-import
from .preferences import PreferencesDialog  # pylint: disable=unused-import

Ui_mainWindow, base = loadUiType(uidir + '/main_window.ui')
