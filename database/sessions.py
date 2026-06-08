from database.connection import connect


def create_retrieval_session(user_id, category_id, requested_amount, retrieved_amount):
    conn = connect()
    try:
        cursor = conn.execute(
            """INSERT INTO retrieval_sessions
               (user_id, category_id, requested_amount, retrieved_amount)
               VALUES (?, ?, ?, ?)""",
            (user_id, category_id, requested_amount, retrieved_amount),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def add_retrieval_item(session_id, account_id, position):
    conn = connect()
    try:
        conn.execute(
            """INSERT INTO retrieval_items (session_id, account_id, position)
               VALUES (?, ?, ?)""",
            (session_id, account_id, position),
        )
        conn.commit()
    finally:
        conn.close()


def list_recent_sessions(limit=10):
    conn = connect()
    try:
        return conn.execute(
            """SELECT rs.*, c.name as category_name
               FROM retrieval_sessions rs
               JOIN categories c ON c.id = rs.category_id
               ORDER BY rs.id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    finally:
        conn.close()


def get_session(session_id):
    conn = connect()
    try:
        return conn.execute(
            """SELECT rs.*, c.name as category_name
               FROM retrieval_sessions rs
               JOIN categories c ON c.id = rs.category_id
               WHERE rs.id = ?""",
            (session_id,),
        ).fetchone()
    finally:
        conn.close()


def get_session_items(session_id):
    conn = connect()
    try:
        return conn.execute(
            """SELECT ri.*, a.username, a.password, c.name as category_name
               FROM retrieval_items ri
               JOIN accounts a ON a.id = ri.account_id
               JOIN categories c ON c.id = a.category_id
               WHERE ri.session_id = ?
               ORDER BY ri.position""",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()


def delete_session(session_id):
    conn = connect()
    try:
        conn.execute("DELETE FROM retrieval_sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


def get_item(item_id):
    conn = connect()
    try:
        return conn.execute(
            """SELECT ri.*, a.username, a.password, c.name as category_name
               FROM retrieval_items ri
               JOIN accounts a ON a.id = ri.account_id
               JOIN categories c ON c.id = a.category_id
               WHERE ri.id = ?""",
            (item_id,),
        ).fetchone()
    finally:
        conn.close()


def set_item_used(item_id, used):
    conn = connect()
    try:
        conn.execute(
            """UPDATE retrieval_items SET used = ?,
               used_at = CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END
               WHERE id = ?""",
            (1 if used else 0, 1 if used else 0, item_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_pending_items(limit=20, offset=0):
    conn = connect()
    try:
        return conn.execute(
            """SELECT ri.*, a.username, a.password, c.name as category_name
               FROM retrieval_items ri
               JOIN accounts a ON a.id = ri.account_id
               JOIN categories c ON c.id = a.category_id
               WHERE ri.used = 0
               ORDER BY ri.id DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
    finally:
        conn.close()


def count_pending_items():
    conn = connect()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM retrieval_items WHERE used = 0"
        ).fetchone()
        return row["cnt"]
    finally:
        conn.close()


def stats_summary():
    conn = connect()
    try:
        accounts = conn.execute(
            "SELECT COUNT(*) as total, SUM(CASE WHEN used = 1 THEN 1 ELSE 0 END) as used_count FROM accounts"
        ).fetchone()
        sessions = conn.execute(
            "SELECT COUNT(*) as total FROM retrieval_sessions"
        ).fetchone()
        categories = conn.execute(
            """SELECT c.name, COUNT(a.id) as count
               FROM categories c
               LEFT JOIN accounts a ON a.category_id = c.id
               GROUP BY c.id ORDER BY c.name"""
        ).fetchall()
        return {
            "total_accounts": accounts["total"],
            "used_accounts": accounts["used_count"],
            "total_sessions": sessions["total"],
            "categories": [dict(c) for c in categories],
        }
    finally:
        conn.close()
