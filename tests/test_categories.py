"""Tests for database/categories.py"""
from database import (
    add_category, delete_category, list_categories,
    get_category_name, get_category_id_by_name, update_category_price,
)
from database.connection import connect


class TestAddCategory:
    def test_add_category(self, isolated_db):
        success, msg = add_category("newcat")
        assert success is True
        cats = list_categories()
        assert any(c["name"] == "newcat" for c in cats)

    def test_duplicate_category(self, isolated_db):
        add_category("cat1")
        success, msg = add_category("cat1")
        assert success is False
        assert "already exists" in msg.lower()

    def test_normalize_name(self, isolated_db):
        add_category("  spaced  name  ")
        cats = list_categories()
        assert any(c["name"] == "spaced name" for c in cats)

    def test_empty_name_rejected(self, isolated_db):
        success, msg = add_category("")
        assert success is False


class TestDeleteCategory:
    def test_delete_existing(self, isolated_db):
        add_category("todelete")
        success, msg = delete_category("todelete")
        assert success is True
        cats = list_categories()
        assert not any(c["name"] == "todelete" for c in cats)

    def test_delete_nonexistent(self, isolated_db):
        success, msg = delete_category("nonexistent")
        assert success is False
        assert "not found" in msg.lower()

    def test_cannot_delete_uncategorized(self, isolated_db):
        success, msg = delete_category("uncategorized")
        assert success is False
        assert "cannot delete" in msg.lower()

    def test_delete_moves_accounts(self, isolated_db):
        db = connect()
        add_category("tempcat")
        cat_id = get_category_id_by_name("tempcat")
        db.execute(
            "INSERT INTO accounts (username, password, category_id, status) VALUES (?, ?, ?, ?)",
            ("u1", "p1", cat_id, "available"),
        )
        db.commit()
        db.close()

        delete_category("tempcat")
        uncategorized_id = get_category_id_by_name("uncategorized")
        from database import list_accounts
        accounts = list_accounts(category_id=uncategorized_id)
        assert len(accounts) == 1
        assert accounts[0]["username"] == "u1"


class TestGetCategoryName:
    def test_existing(self, isolated_db):
        add_category("testname")
        cat_id = get_category_id_by_name("testname")
        name = get_category_name(cat_id)
        assert name == "testname"

    def test_nonexistent(self, isolated_db):
        name = get_category_name(99999)
        assert name is None


class TestUpdateCategoryPrice:
    def test_update_price(self, isolated_db):
        add_category("pricetest", default_price=0)
        cat_id = get_category_id_by_name("pricetest")
        assert update_category_price(cat_id, 250) is True
        cats = list_categories()
        cat = [c for c in cats if c["name"] == "pricetest"][0]
        assert cat["default_price"] == 250
