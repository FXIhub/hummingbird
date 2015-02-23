class EventTranslator(object):
    def __init__(self, event, sourceTranslator):
        self._evt = event
        self._trans = sourceTranslator
        self._cache = {}
        self._keys = None
        self._nativeKeys = None
        self._id = None

    def __getitem__(self, key):
        if key not in self._cache:
            self._cache[key] = self._trans.translate(self._evt, key)
        return self._cache[key]

    def keys(self):
        if self._keys is None:
            self._keys = self._trans.eventKeys(self._evt)
        return self._keys

    def nativeKeys(self):
        if self._nativeKeys is None:
            self._nativeKeys = self._trans.eventNativeKeys(self._evt)
        return self._nativeKeys
            
    def id(self):
        if self._id is None:
            self._id = self._trans.id(self._evt)
        return self._id
