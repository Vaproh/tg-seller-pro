"""Tests for core/filters.py"""
from core.filters import (
    parse_id_list, parse_filter_state, build_filter_state,
    apply_list_filters, count_from_filter, fmt_account_list_line,
    fmt_account_list_page, PAGE_SIZE,
)


class TestParseIdList:
    def test_basic(self):
        assert parse_id_list("1,2,3") == [1, 2, 3]

    def test_with_spaces(self):
        assert parse_id_list("1, 2, 3") == [1, 2, 3]

    def test_empty(self):
        assert parse_id_list("") is None
        assert parse_id_list("   ") is None

    def test_non_digits_filtered(self):
        assert parse_id_list("1,abc,3") == [1, 3]


class TestParseFilterState:
    def test_single_filter(self):
        result = parse_filter_state("status:available")
        assert result == {"status": "available"}

    def test_multiple_filters(self):
        result = parse_filter_state("status:available|cat:1")
        assert result["status"] == "available"
        assert result["cat"] == "1"

    def test_none_returns_empty(self):
        assert parse_filter_state(None) == {}
        assert parse_filter_state("") == {}


class TestBuildFilterState:
    def test_status_only(self):
        result = build_filter_state(status="sold")
        assert "status:sold" in result

    def test_category_only(self):
        result = build_filter_state(category_id=5)
        assert "cat:5" in result

    def test_all_filters(self):
        result = build_filter_state(status="available", category_id=3, id_list=[1, 2])
        assert "status:available" in result
        assert "cat:3" in result
        assert "ids:1,2" in result

    def test_no_filters(self):
        assert build_filter_state() is None


class TestFmtAccountListLine:
    def test_basic(self):
        account = {
            "id": 1, "username": "user1",
            "category_name": "cat1",
        }
        line = fmt_account_list_line(account)
        assert "1" in line
        assert "user1" in line
        assert "cat1" in line


class TestFmtAccountListPage:
    def test_with_accounts(self):
        accounts = [
            {"id": 1, "username": "u1", "category_name": "c1"},
            {"id": 2, "username": "u2", "category_name": "c2"},
        ]
        text = fmt_account_list_page(accounts, 1, 2, title="Test")
        assert "Test" in text
        assert "u1" in text
        assert "u2" in text

    def test_empty_accounts(self):
        text = fmt_account_list_page([], 1, 1, title="Test")
        assert "No accounts" in text


class TestApplyListFilters:
    def test_no_filter(self, seed_accounts):
        accounts, total = apply_list_filters(None, limit=100)
        assert total == 3

    def test_status_filter(self, seed_accounts):
        accounts, total = apply_list_filters("status:available", limit=100)
        assert total == 2

    def test_category_filter(self, seed_accounts):
        accounts, total = apply_list_filters("cat:1", limit=100)
        assert total == 2


class TestCountFromFilter:
    def test_no_filter(self, seed_accounts):
        assert count_from_filter(None) == 3

    def test_status_filter(self, seed_accounts):
        assert count_from_filter("status:sold") == 1
