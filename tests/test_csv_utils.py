"""Tests for utils/csv_utils.py"""
from utils.csv_utils import detect_columns, build_accounts_from_csv, _parse_bool


class TestDetectColumns:
    def test_standard_headers(self):
        headers = ["username", "password", "email"]
        mapping = detect_columns(headers)
        assert mapping == {"username": 0, "password": 1, "email": 2}

    def test_alternative_names(self):
        headers = ["user", "pass", "mail"]
        mapping = detect_columns(headers)
        assert mapping["username"] == 0
        assert mapping["password"] == 1
        assert mapping["email"] == 2

    def test_2fa_headers(self):
        headers = ["username", "password", "2fa", "verified"]
        mapping = detect_columns(headers)
        assert mapping["has_2fa"] == 2
        assert mapping["is_verified"] == 3

    def test_notes_header(self):
        headers = ["username", "password", "comment"]
        mapping = detect_columns(headers)
        assert mapping["notes"] == 2

    def test_unknown_headers_ignored(self):
        headers = ["username", "password", "random_col"]
        mapping = detect_columns(headers)
        assert "random_col" not in mapping


class TestBuildAccountsFromCsv:
    def test_basic_build(self):
        headers = ["username", "password"]
        data = [["u1", "p1"], ["u2", "p2"]]
        mapping = {"username": 0, "password": 1}
        accounts = build_accounts_from_csv(headers, data, mapping)
        assert len(accounts) == 2
        assert accounts[0]["username"] == "u1"
        assert accounts[1]["password"] == "p2"

    def test_skips_empty_rows(self):
        headers = ["username", "password"]
        data = [["u1", "p1"], ["", ""], ["u2", "p2"]]
        mapping = {"username": 0, "password": 1}
        accounts = build_accounts_from_csv(headers, data, mapping)
        assert len(accounts) == 2

    def test_optional_fields(self):
        headers = ["username", "password", "email", "notes"]
        data = [["u1", "p1", "a@b.com", "note1"]]
        mapping = {"username": 0, "password": 1, "email": 2, "notes": 3}
        accounts = build_accounts_from_csv(headers, data, mapping)
        assert accounts[0]["email"] == "a@b.com"
        assert accounts[0]["notes"] == "note1"

    def test_missing_optional_field(self):
        headers = ["username", "password"]
        data = [["u1", "p1"]]
        mapping = {"username": 0, "password": 1}
        accounts = build_accounts_from_csv(headers, data, mapping)
        assert accounts[0]["email"] is None
        assert accounts[0]["has_2fa"] is False


class TestParseBool:
    def test_truthy_values(self):
        assert _parse_bool("true") is True
        assert _parse_bool("1") is True
        assert _parse_bool("yes") is True
        assert _parse_bool("True") is True

    def test_falsy_values(self):
        assert _parse_bool("false") is False
        assert _parse_bool("0") is False
        assert _parse_bool("no") is False
        assert _parse_bool("") is False
        assert _parse_bool(None) is False
