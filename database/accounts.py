import sqlite3
import csv
import io
from database.connection import connect


def add_account(username, password, category_id, email=None, email_password=None,
                has_2fa=False, is_verified=False, notes=None):
    conn = connect()
    try:
        cursor = conn.execute(
            """INSERT INTO accounts
               (username, password, category_id, email, email_password, has_2fa, is_verified, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                username, password, category_id,
                email, email_password,
                1 if has_2fa else 0,
                1 if is_verified else 0,
                notes,
            ),
        )
        conn.commit()
        return True, "Account added.", cursor.lastrowid
    except sqlite3.IntegrityError:
        return False, "Duplicate account (same username, password, and category).", None
    finally:
        conn.close()


def add_accounts_bulk(items, category_id):
    added = 0
    skipped = 0
    conn = connect()
    try:
        for item in items:
            try:
                conn.execute(
                    """INSERT INTO accounts
                       (username, password, category_id, email, email_password, has_2fa, is_verified, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item.get("username", ""),
                        item.get("password", ""),
                        category_id,
                        item.get("email"),
                        item.get("email_password"),
                        1 if item.get("has_2fa") else 0,
                        1 if item.get("is_verified") else 0,
                        item.get("notes"),
                    ),
                )
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
        conn.commit()
        return {"added": added, "skipped": skipped}
    finally:
        conn.close()


def get_account_by_id(account_id):
    conn = connect()
    try:
        row = conn.execute(
            """SELECT a.*, c.name as category_name
               FROM accounts a
               JOIN categories c ON c.id = a.category_id
               WHERE a.id = ?""",
            (account_id,),
        ).fetchone()
        return row
    finally:
        conn.close()


def list_accounts(limit=20, offset=0, status=None, category_id=None,
                  status_list=None, id_list=None):
    conn = connect()
    try:
        query = """
            SELECT a.*, c.name as category_name
            FROM accounts a
            JOIN categories c ON c.id = a.category_id
            WHERE 1=1
        """
        params = []
        if status is not None:
            query += " AND a.status = ?"
            params.append(status)
        if status_list is not None:
            placeholders = ",".join("?" * len(status_list))
            query += f" AND a.status IN ({placeholders})"
            params.extend(status_list)
        if category_id is not None:
            query += " AND a.category_id = ?"
            params.append(category_id)
        if id_list is not None:
            placeholders = ",".join("?" * len(id_list))
            query += f" AND a.id IN ({placeholders})"
            params.extend(id_list)
        query += " ORDER BY a.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def get_available_account_ids(limit):
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id FROM accounts WHERE status = 'available' ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [r["id"] for r in rows]
    finally:
        conn.close()


def count_accounts(status=None, category_id=None, status_list=None, id_list=None):
    conn = connect()
    try:
        query = "SELECT COUNT(*) as cnt FROM accounts WHERE 1=1"
        params = []
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        if status_list is not None:
            placeholders = ",".join("?" * len(status_list))
            query += f" AND status IN ({placeholders})"
            params.extend(status_list)
        if category_id is not None:
            query += " AND category_id = ?"
            params.append(category_id)
        if id_list is not None:
            placeholders = ",".join("?" * len(id_list))
            query += f" AND id IN ({placeholders})"
            params.extend(id_list)
        row = conn.execute(query, params).fetchone()
        return row["cnt"]
    finally:
        conn.close()


def search_accounts(term=None, category=None, status=None, newest_first=True,
                    username=None, password=None, notes_term=None,
                    buyer=None, tag=None, category_id=None, status_list=None,
                    id_list=None):
    conn = connect()
    try:
        query = """
            SELECT a.*, c.name as category_name
            FROM accounts a
            JOIN categories c ON c.id = a.category_id
            WHERE 1=1
        """
        params = []
        if term:
            query += " AND (a.username LIKE ? OR a.password LIKE ? OR a.notes LIKE ?)"
            t = f"%{term}%"
            params.extend([t, t, t])
        if username:
            query += " AND a.username LIKE ?"
            params.append(f"%{username}%")
        if password:
            query += " AND a.password LIKE ?"
            params.append(f"%{password}%")
        if category:
            query += " AND LOWER(c.name) = LOWER(?)"
            params.append(category)
        if category_id is not None:
            query += " AND a.category_id = ?"
            params.append(category_id)
        if status:
            query += " AND a.status = ?"
            params.append(status)
        if status_list is not None:
            placeholders = ",".join("?" * len(status_list))
            query += f" AND a.status IN ({placeholders})"
            params.extend(status_list)
        if id_list is not None:
            placeholders = ",".join("?" * len(id_list))
            query += f" AND a.id IN ({placeholders})"
            params.extend(id_list)
        if notes_term:
            query += " AND a.notes LIKE ?"
            params.append(f"%{notes_term}%")
        if buyer or tag:
            query += " AND a.id IN (SELECT s.account_id FROM sales s WHERE 1=1"
            if buyer:
                query += " AND LOWER(s.buyer_name) = LOWER(?)"
                params.append(buyer)
            if tag:
                query += " AND s.tags LIKE ?"
                params.append(f"%{tag}%")
            query += ")"
        order = "DESC" if newest_first else "ASC"
        query += f" ORDER BY a.id {order}"
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def set_account_status(account_id, status):
    conn = connect()
    try:
        cursor = conn.execute(
            "UPDATE accounts SET status = ? WHERE id = ?",
            (status, account_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_account_notes(account_id, notes):
    conn = connect()
    try:
        cursor = conn.execute(
            "UPDATE accounts SET notes = ? WHERE id = ?",
            (notes, account_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_account_optional_fields(account_id, email, email_password, has_2fa, is_verified):
    conn = connect()
    try:
        cursor = conn.execute(
            """UPDATE accounts SET email = ?, email_password = ?,
               has_2fa = ?, is_verified = ? WHERE id = ?""",
            (email, email_password, 1 if has_2fa else 0, 1 if is_verified else 0, account_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_account(account_id):
    conn = connect()
    try:
        cursor = conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_accounts_by_ids(ids):
    conn = connect()
    try:
        placeholders = ",".join("?" * len(ids))
        cursor = conn.execute(
            f"DELETE FROM accounts WHERE id IN ({placeholders})", list(ids)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def delete_accounts_in_category(category_id):
    conn = connect()
    try:
        cursor = conn.execute(
            "DELETE FROM accounts WHERE category_id = ?", (category_id,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def get_accounts_for_category(category_id, limit=5):
    conn = connect()
    try:
        return conn.execute(
            """SELECT a.*, c.name as category_name
               FROM accounts a
               JOIN categories c ON c.id = a.category_id
               WHERE a.category_id = ?
               ORDER BY a.id DESC LIMIT ?""",
            (category_id, limit),
        ).fetchall()
    finally:
        conn.close()


def get_available_accounts_for_category(category_id, limit=5):
    conn = connect()
    try:
        return conn.execute(
            """SELECT a.*, c.name as category_name
               FROM accounts a
               JOIN categories c ON c.id = a.category_id
               WHERE a.category_id = ? AND a.status = 'available'
               ORDER BY a.id DESC LIMIT ?""",
            (category_id, limit),
        ).fetchall()
    finally:
        conn.close()


def export_accounts_csv():
    conn = connect()
    try:
        rows = conn.execute(
            """SELECT a.id, a.username, a.password, a.email, a.email_password,
                      a.has_2fa, a.is_verified, c.name as category, a.notes,
                      a.status, a.created_at
               FROM accounts a
               JOIN categories c ON c.id = a.category_id
               ORDER BY a.id"""
        ).fetchall()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "username", "password", "email", "email_password",
            "has_2fa", "is_verified", "category", "notes",
            "status", "created_at"
        ])
        for row in rows:
            writer.writerow([
                row["id"], row["username"], row["password"],
                row["email"], row["email_password"],
                row["has_2fa"], row["is_verified"],
                row["category"], row["notes"],
                row["status"], row["created_at"],
            ])
        return output.getvalue().encode("utf-8")
    finally:
        conn.close()
