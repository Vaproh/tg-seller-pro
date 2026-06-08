"""Tests for database/sales.py — sell flow, mark_payment, void_sale"""
from database import (
    add_account, get_account_by_id, add_seller,
    sell_account, void_sale, get_sale_by_id,
)
from database.sales import mark_payment, bulk_sell_accounts, get_sales, count_sales
from database.sellers import remove_seller


class TestSellAccount:
    def test_sell_available_account(self, isolated_db):
        add_account("u1", "p1", 1)
        add_seller(999, "seller1", 12345)
        success, msg, sale_id = sell_account(1, 1, "Buyer1", 100)
        assert success is True
        assert sale_id is not None
        acc = get_account_by_id(1)
        assert acc["status"] == "pending_payment"  # default is pending

    def test_sell_with_paid_status(self, isolated_db):
        add_account("u1", "p1", 1)
        add_seller(999, "seller1", 12345)
        success, msg, sale_id = sell_account(1, 1, "Buyer1", 100, payment_status="paid")
        assert success
        acc = get_account_by_id(1)
        assert acc["status"] == "sold"

    def test_sell_nonexistent_account(self, isolated_db):
        add_seller(999, "seller1", 12345)
        success, msg, _ = sell_account(9999, 1, "Buyer1", 100)
        assert success is False
        assert "not found" in msg.lower()

    def test_sell_already_sold_account(self, isolated_db):
        add_account("u1", "p1", 1)
        add_seller(999, "seller1", 12345)
        sell_account(1, 1, "Buyer1", 100, payment_status="paid")
        success, msg, _ = sell_account(1, 1, "Buyer2", 200)
        assert success is False
        assert "not available" in msg.lower()

    def test_cannot_sell_same_account_twice(self, isolated_db):
        add_account("u1", "p1", 1)
        add_seller(999, "seller1", 12345)
        sell_account(1, 1, "Buyer1", 100)
        success, msg, _ = sell_account(1, 1, "Buyer2", 200)
        assert success is False


class TestMarkPayment:
    def test_mark_paid(self, isolated_db):
        add_account("u1", "p1", 1)
        add_seller(999, "seller1", 12345)
        _, _, sale_id = sell_account(1, 1, "Buyer1", 100)
        assert mark_payment(sale_id, "paid") is True
        acc = get_account_by_id(1)
        assert acc["status"] == "sold"
        sale = get_sale_by_id(sale_id)
        assert sale["payment_status"] == "paid"

    def test_mark_pending(self, isolated_db):
        add_account("u1", "p1", 1)
        add_seller(999, "seller1", 12345)
        _, _, sale_id = sell_account(1, 1, "Buyer1", 100, payment_status="paid")
        assert mark_payment(sale_id, "pending") is True
        acc = get_account_by_id(1)
        assert acc["status"] == "pending_payment"
        sale = get_sale_by_id(sale_id)
        assert sale["payment_status"] == "pending"

    def test_invalid_status_rejected(self, isolated_db):
        add_account("u1", "p1", 1)
        add_seller(999, "seller1", 12345)
        _, _, sale_id = sell_account(1, 1, "Buyer1", 100)
        assert mark_payment(sale_id, "garbage") is False

    def test_nonexistent_sale(self, isolated_db):
        assert mark_payment(99999, "paid") is False


class TestVoidSale:
    def test_void_sale(self, isolated_db):
        add_account("u1", "p1", 1)
        add_seller(999, "seller1", 12345)
        _, _, sale_id = sell_account(1, 1, "Buyer1", 100)
        assert void_sale(sale_id) is True
        acc = get_account_by_id(1)
        assert acc["status"] == "available"
        assert get_sale_by_id(sale_id) is None

    def test_void_nonexistent(self, isolated_db):
        assert void_sale(99999) is False

    def test_void_returns_account_to_available(self, isolated_db):
        add_account("u1", "p1", 1)
        add_seller(999, "seller1", 12345)
        _, _, sale_id = sell_account(1, 1, "Buyer1", 100, payment_status="paid")
        acc = get_account_by_id(1)
        assert acc["status"] == "sold"
        void_sale(sale_id)
        acc = get_account_by_id(1)
        assert acc["status"] == "available"


class TestBulkSell:
    def test_bulk_sell(self, isolated_db):
        add_account("u1", "p1", 1)
        add_account("u2", "p2", 1)
        add_account("u3", "p3", 1)
        add_seller(999, "seller1", 12345)
        result = bulk_sell_accounts([1, 2, 3], 1, "Buyer", 50, payment_status="paid")
        assert result["added"] == 3
        assert result["skipped"] == 0
        for i in range(1, 4):
            assert get_account_by_id(i)["status"] == "sold"

    def test_bulk_sell_skips_unavailable(self, isolated_db):
        add_account("u1", "p1", 1)
        add_account("u2", "p2", 1)
        add_seller(999, "seller1", 12345)
        sell_account(1, 1, "Buyer", 50, payment_status="paid")
        result = bulk_sell_accounts([1, 2], 1, "Buyer", 50)
        assert result["added"] == 1
        assert result["skipped"] == 1

    def test_bulk_sell_empty_list(self, isolated_db):
        add_seller(999, "seller1", 12345)
        result = bulk_sell_accounts([], 1, "Buyer", 50)
        assert result["added"] == 0
        assert result["skipped"] == 0


class TestGetSales:
    def test_get_sales(self, isolated_db):
        add_account("u1", "p1", 1)
        add_seller(999, "seller1", 12345)
        sell_account(1, 1, "Buyer1", 100)
        sales = get_sales()
        assert len(sales) == 1
        assert sales[0]["buyer_name"] == "Buyer1"

    def test_count_sales(self, isolated_db):
        add_account("u1", "p1", 1)
        add_account("u2", "p2", 1)
        add_seller(999, "seller1", 12345)
        sell_account(1, 1, "Buyer1", 100)
        sell_account(2, 1, "Buyer2", 200)
        assert count_sales() == 2

    def test_count_sales_by_status(self, isolated_db):
        add_account("u1", "p1", 1)
        add_account("u2", "p2", 1)
        add_seller(999, "seller1", 12345)
        sell_account(1, 1, "Buyer1", 100, payment_status="paid")
        sell_account(2, 1, "Buyer2", 200)
        assert count_sales(status="paid") == 1
        assert count_sales(status="pending") == 1
