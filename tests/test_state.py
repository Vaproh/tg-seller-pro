"""Tests for core/state.py"""
import time
from core.state import StateManager


class TestStateManager:
    def test_set_and_get(self):
        sm = StateManager(ttl_seconds=300)
        sm.set(1, "key", "value")
        assert sm.get(1, "key") == "value"

    def test_get_default(self):
        sm = StateManager(ttl_seconds=300)
        assert sm.get(1, "key") is None
        assert sm.get(1, "key", "default") == "default"

    def test_pop(self):
        sm = StateManager(ttl_seconds=300)
        sm.set(1, "key", "value")
        assert sm.pop(1, "key") == "value"
        assert sm.get(1, "key") is None

    def test_pop_default(self):
        sm = StateManager(ttl_seconds=300)
        assert sm.pop(1, "missing", "fallback") == "fallback"

    def test_clear(self):
        sm = StateManager(ttl_seconds=300)
        sm.set(1, "k1", "v1")
        sm.set(1, "k2", "v2")
        sm.clear(1)
        assert sm.get(1, "k1") is None
        assert sm.get(1, "k2") is None

    def test_has(self):
        sm = StateManager(ttl_seconds=300)
        assert sm.has(1, "key") is False
        sm.set(1, "key", "value")
        assert sm.has(1, "key") is True

    def test_isolation_between_users(self):
        sm = StateManager(ttl_seconds=300)
        sm.set(1, "key", "user1_val")
        sm.set(2, "key", "user2_val")
        assert sm.get(1, "key") == "user1_val"
        assert sm.get(2, "key") == "user2_val"

    def test_ttl_expiry(self):
        sm = StateManager(ttl_seconds=0)  # immediate expiry
        sm.set(1, "key", "value")
        time.sleep(0.01)
        assert sm.get(1, "key") is None

    def test_pop_after_expiry(self):
        sm = StateManager(ttl_seconds=0)
        sm.set(1, "key", "value")
        time.sleep(0.01)
        assert sm.pop(1, "key", "expired") == "expired"

    def test_multiple_keys(self):
        sm = StateManager(ttl_seconds=300)
        sm.set(1, "k1", "v1")
        sm.set(1, "k2", "v2")
        sm.set(1, "k3", "v3")
        assert sm.get(1, "k1") == "v1"
        assert sm.get(1, "k2") == "v2"
        assert sm.get(1, "k3") == "v3"
