import sqlite3
from database.connection import connect
from database.accounts import set_account_sold, get_account_by_id


def sell_account(account_id, seller_id, buyer, price, tags=None, notes=None):
    conn = connect()
    try:
        account = get_account_by_id(account_id)
        if not account:
            return False, "Account not found.", None
        if account["status"] != "active":
            return False, f"Account is '{account['status']}', not active.", None
        cursor = conn.execute(
            """INSERT INTO sales (account_id, seller_id, buyer_name, price, tags, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (account_id, seller_id, buyer, price, tags, notes),
        )
        conn.execute(
            "UPDATE accounts SET status = 'sold', used = 1, used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (account_id,),
        )
        conn.commit()
        return True, "Sale recorded.", cursor.lastrowid
    except sqlite3.IntegrityError:
        return False, "Account already sold.", None
    finally:
        conn.close()


def bulk_sell_accounts(ids, seller_id, buyer, price_each, tags=None, notes=None):
    added = 0
    skipped = 0
    conn = connect()
    try:
        for aid in ids:
            account = conn.execute("SELECT id, status FROM accounts WHERE id = ?", (aid,)).fetchone()
            if not account or account["status"] != "active":
                skipped += 1
                continue
            try:
                conn.execute(
                    """INSERT INTO sales (account_id, seller_id, buyer_name, price, tags, notes)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (aid, seller_id, buyer, price_each, tags, notes),
                )
                conn.execute(
                    "UPDATE accounts SET status = 'sold', used = 1, used_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (aid,),
                )
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
        conn.commit()
        return {"added": added, "skipped": skipped}
    finally:
        conn.close()


def mark_payment(sale_id, status):
    conn = connect()
    try:
        cursor = conn.execute(
            "UPDATE sales SET payment_status = ? WHERE id = ?",
            (status, sale_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_sales(limit=20, offset=0, seller_id=None, buyer=None, status=None, tag=None):
    conn = connect()
    try:
        query = """
            SELECT s.*, a.username, a.password, a.status as account_status,
                   c.name as category_name, sl.name as seller_name
            FROM sales s
            JOIN accounts a ON a.id = s.account_id
            JOIN categories c ON c.id = a.category_id
            JOIN sellers sl ON sl.id = s.seller_id
            WHERE 1=1
        """
        params = []
        if seller_id is not None:
            query += " AND s.seller_id = ?"
            params.append(seller_id)
        if buyer:
            query += " AND LOWER(s.buyer_name) = LOWER(?)"
            params.append(buyer)
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
        row = conn.execute(
            """SELECT s.*, a.username, a.password, a.email, a.email_password,
                      a.has_2fa, a.is_verified, a.status as account_status,
                      c.name as category_name, sl.name as seller_name, sl.user_id as seller_user_id
               FROM sales s
               JOIN accounts a ON a.id = s.account_id
               JOIN categories c ON c.id = a.category_id
               JOIN sellers sl ON sl.id = s.seller_id
               WHERE s.id = ?""",
            (sale_id,),
        ).fetchone()
        return row
    finally:
        conn.close()


def get_buyers(seller_id=None):
    conn = connect()
    try:
        query = """
            SELECT s.buyer_name,
                   COUNT(*) as total_sales,
                   SUM(s.price) as total_spent,
                   SUM(CASE WHEN s.payment_status = 'pending' THEN s.price ELSE 0 END) as pending_amount
            FROM sales s
            WHERE 1=1
        """
        params = []
        if seller_id is not None:
            query += " AND s.seller_id = ?"
            params.append(seller_id)
        query += " GROUP BY LOWER(s.buyer_name) ORDER BY total_spent DESC"
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def get_buyer_sales(buyer, seller_id=None, limit=20):
    conn = connect()
    try:
        query = """
            SELECT s.*, a.username, c.name as category_name, sl.name as seller_name
            FROM sales s
            JOIN accounts a ON a.id = s.account_id
            JOIN categories c ON c.id = a.category_id
            JOIN sellers sl ON sl.id = s.seller_id
            WHERE LOWER(s.buyer_name) = LOWER(?)
        """
        params = [buyer]
        if seller_id is not None:
            query += " AND s.seller_id = ?"
            params.append(seller_id)
        query += " ORDER BY s.id DESC LIMIT ?"
        params.append(limit)
        return conn.execute(query, params).fetchall()
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


def void_sale(sale_id):
    conn = connect()
    try:
        sale = conn.execute(
            "SELECT account_id FROM sales WHERE id = ?", (sale_id,)
        ).fetchone()
        if not sale:
            return False
        conn.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
        conn.execute(
            "UPDATE accounts SET status = 'active', used = 0, used_at = NULL WHERE id = ?",
            (sale["account_id"],),
        )
        conn.commit()
        return True
    finally:
        conn.close()
