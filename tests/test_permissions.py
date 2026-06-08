"""Tests for core/permissions.py"""
from core.permissions import get_user_role
from database import add_seller
from database.sellers import remove_seller


class TestGetUserRole:
    def test_admin_role(self, isolated_db):
        role = get_user_role(12345)
        assert role == "admin"

    def test_seller_role(self, isolated_db):
        add_seller(999, "seller1", 12345)
        role = get_user_role(999)
        assert role == "seller"
        remove_seller(999)

    def test_unknown_user(self, isolated_db):
        role = get_user_role(00000)
        assert role is None

    def test_inactive_seller(self, isolated_db):
        add_seller(999, "seller1", 12345)
        remove_seller(999)
        role = get_user_role(999)
        assert role is None
