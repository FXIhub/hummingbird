from interface.Qt import loadUiType
import os

uidir = os.path.dirname(os.path.realpath(__file__))
Ui_addBackend, base = loadUiType(uidir + '/add_backend.ui')

from add_backend import AddBackendDialog
