import os
import sys
import ctypes
import logging
from event_translator import EventTranslator

class LCLSTranslator(object):
    def __init__(self, state):
        import psana
        if('LCLS/DataSource' not in state):
            raise ValueError("You need to set the 'LCLS/DataSource'"
                             " in the configuration")
        else:
            self.ds = psana.DataSource(state['LCLS/DataSource'])

    def nextEvent(self):
        evt = self.ds.events().next()
        return EventTranslator(evt,self)
        
    def translate(self, evt, key):
        pass
