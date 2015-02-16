import logging
from pint import UnitRegistry

ureg = UnitRegistry()

def init_translator(state):
    if('Facility' not in state):
        raise ValueError("You need to set the 'Facility' in the configuration")
    elif(state['Facility'] == 'LCLS'):
        from lcls import LCLSTranslator
        return LCLSTranslator(state)
    else:
        raise ValueError('Facility %s not supported' % (state['Facility']))

        

        
