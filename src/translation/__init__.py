import logging
from lcls import LCLSTranslator

def init_translator(state):
    if('Facility' not in state):
        raise ValueError("You need to set the 'Facility' in the configuration")
    elif(state['Facility'] == 'LCLS'):
        return LCLSTranslator(state)
    else:
        raise ValueError('Facility %s not supported' % (state['Facility']))

        

        
