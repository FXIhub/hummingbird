"""Implements all the reading and translation of facility specific
data streams into a unified format that can be used by the analysis
package."""
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import os

from pint import UnitRegistry

from .event_translator import EventTranslator  # pylint: disable=unused-import
from .record import Record, add_record  # pylint: disable=unused-import
from .worker import Worker  # pylint: disable=unused-import

ureg = UnitRegistry()
ureg.enable_contexts('spectroscopy')
ureg.default_format = '~'
ureg.load_definitions(os.path.join(os.path.dirname(__file__), 'units.txt'))
