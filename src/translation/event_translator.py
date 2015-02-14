class EventTranslator(object):
    def __init__(self, event, sourceTranslator):
        self._evt = event
        self._trans = sourceTranslator
        self._cache = {}

    def __getitem__(self, key):
        if key not in self._cache:
            self._cache[key] = self._translate(self._evt, key)
        return self._cache[key]
