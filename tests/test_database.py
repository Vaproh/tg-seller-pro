"""Tests for database/accounts.py"""
from database import (
    add_account, get_account_by_id, list_accounts, count_accounts,
    search_accounts, delete_account, delete_accounts_by_ids,
    set_account_status, update_account_notes, update_account_optional_fields,
    add_accounts_bulk, export_accounts_csv, list_categories,
)
from database.connection import connect


class TestAddAccount:
    def test_add_single(self, isolated_db):
        success, msg, acc_id = add_account("u1", "p1", 1)
        assert success is True
        assert acc_id is not None
        acc = get_account_by_id(acc_id)
        assert acc["username"] == "u1"
        assert acc["password"] == "p1"
        assert acc["status"] == "available"

    def test_add_with_optional_fields(self, isolated_db):
        success, msg, acc_id = add_account(
            "u1", "p1", 1,
            email="a@b.com", email_password="ep",
            has_2fa=True, is_verified=True, notes="test notes",
        )
        assert success
        acc = get_account_by_id(acc_id)
        assert acc["email"] == "a@b.com"
        assert acc["email_password"] == "ep"
        assert acc["has_2fa"] == 1
        assert acc["is_verified"] == 1
        assert acc["notes"] == "test notes"

    def test_duplicate_rejected(self, isolated_db):
        add_account("u1", "p1", 1)
        success, msg, _ = add_account("u1", "p1", 1)
        assert success is False
        assert "Duplicate" in msg


class TestListAccounts:
    def test_list_all(self, seed_accounts):
        accounts = list_accounts(limit=100)
        assert len(accounts) == 3

    def test_filter_by_status(self, seed_accounts):
        available = list_accounts(limit=100, status="available")
        assert len(available) == 2
        sold = list_accounts(limit=100, status="sold")
        assert len(sold) == 1

    def test_filter_by_category(self, seed_accounts):
        cat_a = list_accounts(limit=100, category_id=1)
        assert len(cat_a) == 2
        cat_b = list_accounts(limit=100, category_id=2)
        assert len(cat_b) == 1

    def test_pagination(self, seed_accounts):
        page1 = list_accounts(limit=2, offset=0)
        assert len(page1) == 2
        page2 = list_accounts(limit=2, offset=2)
        assert len(page2) == 1


class TestCountAccounts:
    def test_count_all(self, seed_accounts):
        assert count_accounts() == 3

    def test_count_by_status(self, seed_accounts):
        assert count_accounts(status="available") == 2
        assert count_accounts(status="sold") == 1


class TestSearchAccounts:
    def test_search_by_username(self, seed_accounts):
        results = search_accounts(username="user1")
        assert len(results) == 1
        assert results[0]["username"] == "user1"

    def test_search_by_general_term(self, seed_accounts):
        results = search_accounts(term="user")
        assert len(results) == 3

    def test_search_by_category(self, seed_accounts):
        results = search_accounts(category_id=2)
        assert len(results) == 1
        assert results[0]["username"] == "user3"


class TestDeleteAccount:
    def test_delete_existing(self, seed_accounts):
        assert delete_account(1) is True
        assert get_account_by_id(1) is None

    def test_delete_nonexistent(self, seed_accounts):
        assert delete_account(9999) is False

    def test_bulk_delete(self, seed_accounts):
        deleted = delete_accounts_by_ids([1, 2])
        assert deleted == 2
        assert get_account_by_id(1) is None
        assert get_account_by_id(2) is None


class TestAccountStatus:
    def test_set_status(self, seed_accounts):
        assert set_account_status(1, "sold") is True
        acc = get_account_by_id(1)
        assert acc["status"] == "sold"

    def test_set_status_nonexistent(self, seed_accounts):
        assert set_account_status(9999, "sold") is False


class TestAccountNotes:
    def test_update_notes(self, seed_accounts):
        assert update_account_notes(1, "new notes") is True
        acc = get_account_by_id(1)
        assert acc["notes"] == "new notes"


class TestBulkAdd:
    def test_bulk_add(self, isolated_db):
        items = [
            {"username": "bu1", "password": "bp1"},
            {"username": "bu2", "password": "bp2"},
        ]
        result = add_accounts_bulk(items, 1)
        assert result["added"] == 2
        assert result["skipped"] == 0

    def test_bulk_add_with_duplicates(self, isolated_db):
        add_account("bu1", "bp1", 1)
        items = [
            {"username": "bu1", "password": "bp1"},
            {"username": "bu2", "password": "bp2"},
        ]
        result = add_accounts_bulk(items, 1)
        assert result["added"] == 1
        assert result["skipped"] == 1


class TestExportCsv:
    def test_export(self, seed_accounts):
        csv_data = export_accounts_csv()
        assert isinstance(csv_data, bytes)
        text = csv_data.decode("utf-8")
        assert "username" in text
        assert "user1" in text
