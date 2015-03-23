"""Implements all the reading and translation of facility specific
data streams into a unified format that can be used by the analysis
package."""

from .pint import UnitRegistry
from .worker import Worker # pylint: disable=unused-import
from .event_translator import EventTranslator # pylint: disable=unused-import
from .record import Record, addRecord # pylint: disable=unused-import

ureg = UnitRegistry()
ureg.enable_contexts('spectroscopy')
ureg.default_format = '~'
