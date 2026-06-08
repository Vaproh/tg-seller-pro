import sqlite3
from database.connection import connect


def add_seller(user_id, name, added_by):
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO sellers (user_id, name, added_by) VALUES (?, ?, ?)",
            (user_id, name, added_by),
        )
        conn.commit()
        return True, f"Seller '{name}' registered."
    except sqlite3.IntegrityError:
        return False, f"User {user_id} is already a seller."
    finally:
        conn.close()


def remove_seller(user_id):
    conn = connect()
    try:
        cursor = conn.execute(
            "UPDATE sellers SET active = 0 WHERE user_id = ?", (user_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def list_sellers():
    conn = connect()
    try:
        return conn.execute(
            """SELECT s.*,
                      COUNT(sa.id) as sale_count,
                      COALESCE(SUM(sa.price), 0) as total_earnings
               FROM sellers s
               LEFT JOIN sales sa ON sa.seller_id = s.id
               GROUP BY s.id
               ORDER BY s.name"""
        ).fetchall()
    finally:
        conn.close()


def get_seller_by_user_id(user_id):
    conn = connect()
    try:
        return conn.execute(
            "SELECT * FROM sellers WHERE user_id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()


def get_seller_by_id(seller_id):
    conn = connect()
    try:
        return conn.execute(
            "SELECT * FROM sellers WHERE id = ?", (seller_id,)
        ).fetchone()
    finally:
        conn.close()


def is_seller_active(user_id):
    conn = connect()
    try:
        row = conn.execute(
            "SELECT active FROM sellers WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row is not None and row["active"] == 1
    finally:
        conn.close()
