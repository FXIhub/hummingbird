"""Provides the interface between the analysis code and the various
translators."""

class EventTranslator(object):
    """Provides the interface between the analysis code and the various
    translators.

    The evt argument of onEvent(), which must be defined in every
    configuration file is actually an EventTranslator.
    """
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
        """Returns the translated keys available"""
        if self._keys is None:
            self._keys = self._trans.eventKeys(self._evt)
        return self._keys

    def nativeKeys(self):
        """Returns the keys, with facility specific names, available"""
        if self._nativeKeys is None:
            self._nativeKeys = self._trans.eventNativeKeys(self._evt)
        return self._nativeKeys

    def event_id(self):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        if self._id is None:
            self._id = self._trans.event_id(self._evt)
        return self._id
