class EventTranslator(object):
    def __init__(self, event, sourceTranslator):
        self._evt = event
        self._trans = sourceTranslator
        self._cache = {}
        self._keys = None

    def __getitem__(self, key):
        if key not in self._cache:
            self._cache[key] = self._translate(self._evt, key)
        return self._cache[key]

    def keys(self):
        if self._keys is None:
            self._keys = self._evt.keys()
        return self._keys
        
