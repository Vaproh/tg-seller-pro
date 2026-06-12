import sqlite3
import secrets
import string
from database.connection import connect


def _generate_sale_code():
    alphabet = string.ascii_uppercase + string.digits
    return "SALE-" + "".join(secrets.choice(alphabet) for _ in range(8))


def _resolve_sale_id(conn, sale_id):
    if isinstance(sale_id, int):
        return sale_id
    row = conn.execute("SELECT id FROM sales WHERE sale_code = ?", (str(sale_id),)).fetchone()
    return row["id"] if row else None


def sell_account(account_id, seller_id, price, payment_status="pending", notes=None):
    conn = connect()
    try:
        account = conn.execute(
            "SELECT id, status FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if not account:
            return False, "Account not found.", None
        if account["status"] != "available":
            return False, f"Account is '{account['status']}', not available.", None
        sale_code = _generate_sale_code()
        cursor = conn.execute(
            """INSERT INTO sales (account_id, seller_id, buyer_name, price, payment_status, notes, sale_code)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (account_id, seller_id, "Unknown", price, payment_status, notes, sale_code),
        )
        new_status = "pending_payment" if payment_status == "pending" else "sold"
        conn.execute(
            "UPDATE accounts SET status = ? WHERE id = ?",
            (new_status, account_id),
        )
        conn.commit()
        return True, "Sale recorded.", sale_code
    except sqlite3.IntegrityError:
        return False, "Account already has a sale record.", None
    finally:
        conn.close()


def bulk_sell_accounts(ids, seller_id, price_each, payment_status="pending", notes=None):
    added = 0
    skipped = 0
    conn = connect()
    try:
        for aid in ids:
            account = conn.execute("SELECT id, status FROM accounts WHERE id = ?", (aid,)).fetchone()
            if not account or account["status"] != "available":
                skipped += 1
                continue
            try:
                sale_code = _generate_sale_code()
                conn.execute(
                    """INSERT INTO sales (account_id, seller_id, buyer_name, price, payment_status, notes, sale_code)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (aid, seller_id, "Unknown", price_each, payment_status, notes, sale_code),
                )
                new_status = "pending_payment" if payment_status == "pending" else "sold"
                conn.execute(
                    "UPDATE accounts SET status = ? WHERE id = ?",
                    (new_status, aid),
                )
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
        conn.commit()
        return {"added": added, "skipped": skipped}
    finally:
        conn.close()


def mark_payment(sale_id, status):
    if status not in ("paid", "pending"):
        return False
    conn = connect()
    try:
        resolved_id = _resolve_sale_id(conn, sale_id)
        if resolved_id is None:
            return False
        sale = conn.execute(
            "SELECT account_id FROM sales WHERE id = ?", (resolved_id,)
        ).fetchone()
        if not sale:
            return False
        cursor = conn.execute(
            "UPDATE sales SET payment_status = ? WHERE id = ?",
            (status, resolved_id),
        )
        if status == "paid":
            conn.execute(
                "UPDATE accounts SET status = 'sold' WHERE id = ?",
                (sale["account_id"],),
            )
        elif status == "pending":
            conn.execute(
                "UPDATE accounts SET status = 'pending_payment' WHERE id = ?",
                (sale["account_id"],),
            )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_sales(limit=20, offset=0, seller_id=None, status=None, tag=None):
    conn = connect()
    try:
        query = """
            SELECT s.*, a.username, a.password, a.status as account_status,
                   c.name as category_name, sl.name as seller_name
            FROM sales s
            JOIN accounts a ON a.id = s.account_id
            JOIN categories c ON c.id = a.category_id
            LEFT JOIN sellers sl ON sl.id = s.seller_id
            WHERE 1=1
        """
        params = []
        if seller_id is not None:
            query += " AND s.seller_id = ?"
            params.append(seller_id)
        if status:
            query += " AND s.payment_status = ?"
            params.append(status)
        if tag:
            query += " AND s.tags LIKE ?"
            params.append(f"%{tag}%")
        query += " ORDER BY s.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def count_sales(seller_id=None, status=None):
    conn = connect()
    try:
        query = "SELECT COUNT(*) as cnt FROM sales WHERE 1=1"
        params = []
        if seller_id is not None:
            query += " AND seller_id = ?"
            params.append(seller_id)
        if status:
            query += " AND payment_status = ?"
            params.append(status)
        row = conn.execute(query, params).fetchone()
        return row["cnt"]
    finally:
        conn.close()


def get_sale_by_id(sale_id):
    conn = connect()
    try:
        resolved_id = _resolve_sale_id(conn, sale_id)
        if resolved_id is None:
            return None
        row = conn.execute(
            """SELECT s.*, a.username, a.password, a.email, a.email_password,
                      a.has_2fa, a.is_verified, a.status as account_status,
                      c.name as category_name, sl.name as seller_name, sl.user_id as seller_user_id
               FROM sales s
               JOIN accounts a ON a.id = s.account_id
               JOIN categories c ON c.id = a.category_id
               LEFT JOIN sellers sl ON sl.id = s.seller_id
               WHERE s.id = ?""",
            (resolved_id,),
        ).fetchone()
        return row
    finally:
        conn.close()


def get_sales_summary(seller_id=None, period=None):
    conn = connect()
    try:
        query = """
            SELECT
                COUNT(*) as total_sales,
                COALESCE(SUM(s.price), 0) as total_revenue,
                SUM(CASE WHEN s.payment_status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                COALESCE(SUM(CASE WHEN s.payment_status = 'pending' THEN s.price ELSE 0 END), 0) as pending_amount
            FROM sales s
            WHERE 1=1
        """
        params = []
        if seller_id is not None:
            query += " AND s.seller_id = ?"
            params.append(seller_id)
        if period == "today":
            query += " AND DATE(s.sold_at) = DATE('now', 'localtime')"
        elif period == "week":
            query += " AND s.sold_at >= DATE('now', 'localtime', '-7 days')"
        elif period == "month":
            query += " AND s.sold_at >= DATE('now', 'localtime', '-30 days')"
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


_UNSET = object()


def update_sale(sale_id, **fields):
    allowed = {"price", "payment_status", "notes"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not _UNSET}
    if not updates:
        return False
    conn = connect()
    try:
        resolved_id = _resolve_sale_id(conn, sale_id)
        if resolved_id is None:
            return False
        sale = conn.execute("SELECT id FROM sales WHERE id = ?", (resolved_id,)).fetchone()
        if not sale:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [resolved_id]
        conn.execute(f"UPDATE sales SET {set_clause} WHERE id = ?", values)
        if "payment_status" in updates:
            account = conn.execute(
                "SELECT account_id FROM sales WHERE id = ?", (resolved_id,)
            ).fetchone()
            if account:
                status_map = {"paid": "sold", "pending": "pending_payment"}
                new_status = status_map.get(updates["payment_status"])
                if new_status:
                    conn.execute(
                        "UPDATE accounts SET status = ? WHERE id = ?",
                        (new_status, account["account_id"]),
                    )
        conn.commit()
        return True
    finally:
        conn.close()


def void_sale(sale_id):
    conn = connect()
    try:
        resolved_id = _resolve_sale_id(conn, sale_id)
        if resolved_id is None:
            return False
        sale = conn.execute(
            "SELECT account_id FROM sales WHERE id = ?", (resolved_id,)
        ).fetchone()
        if not sale:
            return False
        conn.execute("DELETE FROM sales WHERE id = ?", (resolved_id,))
        conn.execute(
            "UPDATE accounts SET status = 'available' WHERE id = ?",
            (sale["account_id"],),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def create_draft_sale(account_id, seller_id):
    conn = connect()
    try:
        existing = conn.execute(
            "SELECT id FROM sales WHERE account_id = ?", (account_id,)
        ).fetchone()
        if existing:
            return existing["id"]
        sale_code = _generate_sale_code()
        cursor = conn.execute(
            """INSERT INTO sales (account_id, seller_id, buyer_name, price, payment_status, notes, sale_code)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (account_id, seller_id, "Unknown", 0, "pending", None, sale_code),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_revenue_by_day(days=30, seller_id=None):
    conn = connect()
    try:
        query = """
            SELECT DATE(s.sold_at) as day, SUM(s.price) as revenue, COUNT(*) as count
            FROM sales s
            WHERE s.sold_at >= DATE('now', 'localtime', ?)
        """
        params = [f"-{days} days"]
        if seller_id is not None:
            query += " AND s.seller_id = ?"
            params.append(seller_id)
        query += " GROUP BY day ORDER BY day"
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def get_sales_by_category(seller_id=None):
    conn = connect()
    try:
        query = """
            SELECT c.name as category, COUNT(*) as count, SUM(s.price) as revenue
            FROM sales s
            JOIN accounts a ON a.id = s.account_id
            JOIN categories c ON c.id = a.category_id
            WHERE 1=1
        """
        params = []
        if seller_id is not None:
            query += " AND s.seller_id = ?"
            params.append(seller_id)
        query += " GROUP BY c.name ORDER BY revenue DESC"
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def get_top_sellers(limit=10):
    conn = connect()
    try:
        query = """
            SELECT sl.name as seller_name, COUNT(*) as total_sales, SUM(s.price) as total_revenue
            FROM sales s
            JOIN sellers sl ON sl.id = s.seller_id
            GROUP BY sl.id
            ORDER BY total_revenue DESC
            LIMIT ?
        """
        return conn.execute(query, (limit,)).fetchall()
    finally:
        conn.close()


def get_payment_breakdown(seller_id=None):
    conn = connect()
    try:
        query = """
            SELECT s.payment_status, COUNT(*) as count, SUM(s.price) as amount
            FROM sales s
            WHERE 1=1
        """
        params = []
        if seller_id is not None:
            query += " AND s.seller_id = ?"
            params.append(seller_id)
        query += " GROUP BY s.payment_status"
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def transfer_sales(from_seller_id, to_seller_id):
    conn = connect()
    try:
        result = conn.execute(
            "UPDATE sales SET seller_id = ? WHERE seller_id = ?",
            (to_seller_id, from_seller_id),
        )
        conn.commit()
        return result.rowcount
    finally:
        conn.close()
