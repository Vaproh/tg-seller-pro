"""Tests for utils/parsers.py"""
from utils.parsers import parse_bulk_lines, parse_csv_file


class TestParseBulkLines:
    def test_basic_format(self):
        text = "user1:pass1\nuser2:pass2"
        items = parse_bulk_lines(text)
        assert len(items) == 2
        assert items[0]["username"] == "user1"
        assert items[0]["password"] == "pass1"

    def test_with_extra_fields(self):
        text = "user1:pass1,email@test.com,epass,1,0,notes"
        items = parse_bulk_lines(text)
        assert len(items) == 1
        assert items[0]["email"] == "email@test.com"
        assert items[0]["email_password"] == "epass"
        assert items[0]["has_2fa"] is True
        assert items[0]["is_verified"] is False
        assert items[0]["notes"] == "notes"

    def test_skips_invalid_lines(self):
        text = "user1:pass1\ninvalidline\nuser2:pass2"
        items = parse_bulk_lines(text)
        assert len(items) == 2

    def test_empty_input(self):
        assert parse_bulk_lines("") == []
        assert parse_bulk_lines("   ") == []

    def test_password_with_colons(self):
        text = "user1:pass:with:colons"
        items = parse_bulk_lines(text)
        assert len(items) == 1
        assert items[0]["password"] == "pass:with:colons"


class TestParseCsvFile:
    def test_basic_csv(self):
        content = b"username,password,email\nuser1,pass1,email1@test.com\n"
        headers, data = parse_csv_file(content)
        assert headers == ["username", "password", "email"]
        assert len(data) == 1
        assert data[0] == ["user1", "pass1", "email1@test.com"]

    def test_empty_csv(self):
        headers, data = parse_csv_file(b"")
        assert headers == []
        assert data == []

    def test_utf8_bom(self):
        content = b"\xef\xbb\xbfusername,password\nuser1,pass1\n"
        headers, data = parse_csv_file(content)
        assert headers[0] == "username"
