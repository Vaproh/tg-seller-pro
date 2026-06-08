"""Tests for core/format.py"""
from core.format import esc, _truncate, _d, reddit_url, fmt_account_block, fmt_receipt, fmt_sale_block


class TestEsc:
    def test_escapes_html(self):
        assert esc("<b>test</b>") == "&lt;b&gt;test&lt;/b&gt;"

    def test_none_returns_dash(self):
        assert esc(None) == "—"

    def test_converts_to_string(self):
        assert esc(123) == "123"

    def test_plain_text_unchanged(self):
        assert esc("hello") == "hello"


class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello") == "hello"

    def test_exact_limit(self):
        text = "x" * 4000
        assert _truncate(text) == text

    def test_over_limit_truncated(self):
        text = "x" * 5000
        result = _truncate(text)
        assert len(result) < len(text)
        assert result.endswith("... (truncated)")

    def test_custom_limit(self):
        text = "x" * 100
        result = _truncate(text, limit=50)
        assert len(result) < 100
        assert result.endswith("... (truncated)")


class TestD:
    def test_none_returns_empty_dict(self):
        assert _d(None) == {}

    def test_dict_returned_as_is(self):
        d = {"key": "value"}
        assert _d(d) is d

    def test_row_converted_to_dict(self):
        class FakeRow:
            def keys(self):
                return ["a", "b"]
            def __getitem__(self, key):
                return f"val_{key}"
        row = FakeRow()
        result = _d(row)
        assert result == {"a": "val_a", "b": "val_b"}


class TestRedditUrl:
    def test_basic(self):
        assert reddit_url("testuser") == "https://reddit.com/user/testuser"


class TestFmtAccountBlock:
    def test_basic(self):
        account = {
            "id": 1, "username": "u1", "password": "p1",
            "status": "available", "category_name": "cat1",
            "email": None, "email_password": None,
            "has_2fa": 0, "is_verified": 0, "notes": None,
        }
        result = fmt_account_block(account)
        assert "u1" in result
        assert "available" in result
        assert "cat1" in result


class TestFmtReceipt:
    def test_basic(self):
        sale = {
            "id": 1, "username": "u1", "password": "p1",
            "price": 100, "sold_at": "2024-01-01 12:00:00",
            "payment_status": "paid",
        }
        result = fmt_receipt(sale)
        assert "u1" in result
        assert "100" in result
        assert "Paid" in result
