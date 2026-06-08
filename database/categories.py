import sqlite3
from database.connection import connect


def normalize_name(name):
    return " ".join(name.split())


def add_category(name, default_price=0):
    name = normalize_name(name)
    if not name:
        return False, "⚠️ Category name cannot be empty."
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO categories (name, default_price) VALUES (?, ?)",
            (name, default_price),
        )
        conn.commit()
        return True, f"📂 Category '{name}' created."
    except sqlite3.IntegrityError:
        return False, f"📂 Category '{name}' already exists."
    finally:
        conn.close()


def delete_category(name):
    name = normalize_name(name)
    conn = connect()
    try:
        row = conn.execute(
            "SELECT id FROM categories WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        if not row:
            return False, f"🔍 Category '{name}' not found."
        cat_id = row["id"]
        if name.lower() == "uncategorized":
            return False, "⚠️ Cannot delete the default category."
        default = conn.execute(
            "SELECT id FROM categories WHERE LOWER(name) = 'uncategorized'"
        ).fetchone()
        if not default:
            conn.execute(
                "INSERT OR IGNORE INTO categories (name, default_price) VALUES ('uncategorized', 0)"
            )
            default = conn.execute(
                "SELECT id FROM categories WHERE LOWER(name) = 'uncategorized'"
            ).fetchone()
        if default:
            conn.execute(
                "UPDATE accounts SET category_id = ? WHERE category_id = ?",
                (default["id"], cat_id),
            )
        conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        conn.commit()
        return True, f"🗑️ Category '{name}' deleted. Accounts moved to 'uncategorized'."
    finally:
        conn.close()


def list_categories():
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.name, c.default_price,
                   COUNT(a.id) as account_count
            FROM categories c
            LEFT JOIN accounts a ON a.category_id = c.id
            GROUP BY c.id
            ORDER BY c.name
            """
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_category_name(category_id):
    conn = connect()
    try:
        row = conn.execute(
            "SELECT name FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        return row["name"] if row else None
    finally:
        conn.close()


def get_category_id_by_name(name):
    conn = connect()
    try:
        row = conn.execute(
            "SELECT id FROM categories WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


def update_category_price(category_id, price):
    conn = connect()
    try:
        cursor = conn.execute(
            "UPDATE categories SET default_price = ? WHERE id = ?",
            (price, category_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
