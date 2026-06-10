from database.connection import connect
import logging

logger = logging.getLogger(__name__)

LOGS_PER_PAGE = 5

VALID_STATUSES = ("success", "failed", "denied", "cancelled")

ERROR_CATEGORIES = {
    "validation": "validation",
    "permission": "permission",
    "database": "database",
    "system": "system",
}


def record_command(user_id, username, seller_name, command, status="success",
                   command_args=None, error_reason=None, error_detail=None):
    if status not in VALID_STATUSES:
        status = "failed"
        error_reason = error_reason or f"Invalid status: {status}"
    conn = connect()
    try:
        conn.execute(
            """INSERT INTO command_logs
               (user_id, username, seller_name, command, command_args, status, error_reason, error_detail)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, seller_name, command, command_args, status, error_reason, error_detail),
        )
        conn.commit()
    except Exception as e:
        logger.error("Failed to record command log: %s", e)
    finally:
        conn.close()


def get_logs(limit=LOGS_PER_PAGE, offset=0, seller=None, command=None,
             status=None, date=None, category=None):
    conn = connect()
    try:
        query = "SELECT * FROM command_logs WHERE 1=1"
        params = []
        if seller:
            query += " AND (username LIKE ? OR seller_name LIKE ?)"
            params.extend([f"%{seller}%", f"%{seller}%"])
        if command:
            query += " AND command LIKE ?"
            params.append(f"%{command}%")
        if status:
            query += " AND status = ?"
            params.append(status)
        if date:
            query += " AND DATE(created_at) = DATE(?)"
            params.append(date)
        if category:
            query += " AND error_detail LIKE ?"
            params.append(f"%[{category}]%")
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def count_logs(seller=None, command=None, status=None, date=None, category=None):
    conn = connect()
    try:
        query = "SELECT COUNT(*) as cnt FROM command_logs WHERE 1=1"
        params = []
        if seller:
            query += " AND (username LIKE ? OR seller_name LIKE ?)"
            params.extend([f"%{seller}%", f"%{seller}%"])
        if command:
            query += " AND command LIKE ?"
            params.append(f"%{command}%")
        if status:
            query += " AND status = ?"
            params.append(status)
        if date:
            query += " AND DATE(created_at) = DATE(?)"
            params.append(date)
        if category:
            query += " AND error_detail LIKE ?"
            params.append(f"%[{category}]%")
        row = conn.execute(query, params).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()
