from database.connection import connect

DUES_PER_PAGE = 5


def add_due(seller_id, amount, reason=None):
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO dues (seller_id, amount, reason, type) VALUES (?, ?, ?, 'add')",
            (seller_id, amount, reason),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def remove_due(seller_id, amount, reason=None):
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO dues (seller_id, amount, reason, type) VALUES (?, ?, ?, 'remove')",
            (seller_id, amount, reason),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_dues_balance(seller_id):
    conn = connect()
    try:
        row = conn.execute(
            """SELECT COALESCE(SUM(CASE WHEN type='add' THEN amount ELSE 0 END), 0)
                      - COALESCE(SUM(CASE WHEN type='remove' THEN amount ELSE 0 END), 0)
                      as balance
               FROM dues WHERE seller_id = ?""",
            (seller_id,),
        ).fetchone()
        return row["balance"] if row else 0
    finally:
        conn.close()


def get_all_dues_balances():
    conn = connect()
    try:
        rows = conn.execute(
            """SELECT s.name as seller_name, s.user_id,
                      COALESCE(SUM(CASE WHEN d.type='add' THEN d.amount ELSE 0 END), 0)
                      - COALESCE(SUM(CASE WHEN d.type='remove' THEN d.amount ELSE 0 END), 0)
                      as balance
               FROM sellers s
               LEFT JOIN dues d ON d.seller_id = s.id
               GROUP BY s.id
               HAVING balance > 0
               ORDER BY balance DESC"""
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_dues_history(seller_id=None, limit=DUES_PER_PAGE, offset=0):
    conn = connect()
    try:
        query = """
            SELECT d.*, s.name as seller_name
            FROM dues d
            JOIN sellers s ON s.id = d.seller_id
            WHERE 1=1
        """
        params = []
        if seller_id is not None:
            query += " AND d.seller_id = ?"
            params.append(seller_id)
        query += " ORDER BY d.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def count_dues(seller_id=None):
    conn = connect()
    try:
        query = "SELECT COUNT(*) as cnt FROM dues WHERE 1=1"
        params = []
        if seller_id is not None:
            query += " AND seller_id = ?"
            params.append(seller_id)
        row = conn.execute(query, params).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()
