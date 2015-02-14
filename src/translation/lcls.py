
class LCLSTranslator(object):
    def __init__(self, state):
        import psana
        if('DataSource' not in state):
            raise ValueError("You need to set the 'DataSource' in the configuration")
        else:
            self.ds = psana.DataSource(state['DataSource'])

    def nextEvent(self):
        evt = self.ds.next()
        return EventTranslator(evt,self)
        
    def translate(self, evt, key):
        pass
