import time


class StateManager:
    def __init__(self, ttl_seconds=300):
        self._states = {}
        self._timestamps = {}
        self.ttl = ttl_seconds
        self._last_cleanup = time.time()
        self._cleanup_interval = 60

    def set(self, user_id, key, value):
        now = time.time()
        if user_id not in self._states:
            self._states[user_id] = {}
            self._timestamps[user_id] = now
        self._states[user_id][key] = value
        self._timestamps[user_id] = now
        self._maybe_cleanup(now)

    def get(self, user_id, key, default=None):
        if self._is_expired(user_id):
            self.clear(user_id)
            return default
        return self._states.get(user_id, {}).get(key, default)

    def pop(self, user_id, key, default=None):
        if self._is_expired(user_id):
            self.clear(user_id)
            return default
        return self._states.get(user_id, {}).pop(key, default)

    def clear(self, user_id):
        self._states.pop(user_id, None)
        self._timestamps.pop(user_id, None)

    def has(self, user_id, key):
        if self._is_expired(user_id):
            self.clear(user_id)
            return False
        return key in self._states.get(user_id, {})

    def _is_expired(self, user_id):
        ts = self._timestamps.get(user_id)
        if ts is None:
            return False
        return (time.time() - ts) > self.ttl

    def _maybe_cleanup(self, now):
        if (now - self._last_cleanup) < self._cleanup_interval:
            return
        self._last_cleanup = now
        expired = [uid for uid, ts in self._timestamps.items() if (now - ts) > self.ttl]
        for uid in expired:
            self.clear(uid)


state = StateManager(ttl_seconds=300)
