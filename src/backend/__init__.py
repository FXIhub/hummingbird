import logging

from .pint import UnitRegistry
from .backend import Backend 
from .event_translator import EventTranslator
from .record import Record, addRecord

ureg = UnitRegistry()
ureg.enable_contexts('spectroscopy')
ureg.default_format = '~'



        

        
