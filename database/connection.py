import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "reddit_accounts.db")


def connect():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def get_schema_version(conn):
    try:
        row = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
        return row["version"] if row else 0
    except sqlite3.OperationalError:
        return 0


def set_schema_version(conn, version):
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))


def migrate(conn, current_version):
    if current_version < 2:
        logger.info("Migrating schema from V1 to V2...")
        try:
            conn.execute("ALTER TABLE categories ADD COLUMN default_price REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        optional_cols = [
            ("email", "TEXT"),
            ("email_password", "TEXT"),
            ("has_2fa", "INTEGER DEFAULT 0"),
            ("is_verified", "INTEGER DEFAULT 0"),
            ("notes", "TEXT"),
            ("status", "TEXT DEFAULT 'active'"),
        ]
        for col_name, col_type in optional_cols:
            try:
                conn.execute(f"ALTER TABLE accounts ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sellers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                added_by INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL UNIQUE,
                seller_id INTEGER NOT NULL,
                buyer_name TEXT NOT NULL,
                price REAL NOT NULL DEFAULT 0,
                payment_status TEXT NOT NULL DEFAULT 'pending',
                tags TEXT,
                notes TEXT,
                sold_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (seller_id) REFERENCES sellers(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER
            )
        """)

        set_schema_version(conn, 2)
        conn.commit()
        logger.info("Migration to V2 complete.")

    if current_version < 3:
        logger.info("Migrating schema from V2 to V3...")
        # Migrate status values: active -> available, keep sold
        conn.execute("UPDATE accounts SET status = 'available' WHERE status = 'active'")
        # Remove redundant 'used' column concept by normalizing status
        try:
            conn.execute("UPDATE accounts SET status = 'sold' WHERE used = 1 AND status != 'sold'")
        except sqlite3.OperationalError:
            pass
        # Drop old statuses that are no longer used
        conn.execute("UPDATE accounts SET status = 'available' WHERE status IN ('banned', 'locked', 'restricted')")
        set_schema_version(conn, 3)
        conn.commit()
        logger.info("Migration to V3 complete.")

    if current_version < 4:
        logger.info("Migrating schema from V3 to V4...")
        try:
            conn.execute("ALTER TABLE sales RENAME TO sales_old")
            conn.execute("""
                CREATE TABLE sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL UNIQUE,
                    seller_id INTEGER,
                    buyer_name TEXT NOT NULL DEFAULT 'Unknown',
                    price REAL NOT NULL DEFAULT 0,
                    payment_status TEXT NOT NULL DEFAULT 'pending',
                    tags TEXT,
                    notes TEXT,
                    sold_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                    FOREIGN KEY (seller_id) REFERENCES sellers(id)
                )
            """)
            conn.execute("""
                INSERT INTO sales (id, account_id, seller_id, buyer_name, price, payment_status, tags, notes, sold_at)
                SELECT id, account_id, seller_id, buyer_name, price, payment_status, tags, notes, sold_at
                FROM sales_old
            """)
            conn.execute("DROP TABLE sales_old")
        except sqlite3.OperationalError as e:
            logger.warning("V4 migration partial: %s", e)
        set_schema_version(conn, 4)
        conn.commit()
        logger.info("Migration to V4 complete.")

    if current_version < 5:
        logger.info("Migrating schema from V4 to V5...")
        try:
            conn.execute("ALTER TABLE sales ADD COLUMN sale_code TEXT")
            rows = conn.execute("SELECT id FROM sales WHERE sale_code IS NULL").fetchall()
            for row in rows:
                code = "SALE-" + "".join(
                    __import__("secrets").choice(
                        __import__("string").ascii_uppercase + __import__("string").digits
                    )
                    for _ in range(8)
                )
                conn.execute("UPDATE sales SET sale_code = ? WHERE id = ?", (code, row["id"]))
        except sqlite3.OperationalError as e:
            logger.warning("V5 migration partial: %s", e)
        set_schema_version(conn, 5)
        conn.commit()
        logger.info("Migration to V5 complete.")


def init_db():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            default_price REAL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            email_password TEXT,
            has_2fa INTEGER DEFAULT 0,
            is_verified INTEGER DEFAULT 0,
            category_id INTEGER NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'available',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
        )
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_unique_values
        ON accounts (username, password, category_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_accounts_category_id
        ON accounts (category_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_accounts_status
        ON accounts (status)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_code TEXT UNIQUE NOT NULL,
            account_id INTEGER NOT NULL UNIQUE,
            seller_id INTEGER,
            buyer_name TEXT NOT NULL DEFAULT 'Unknown',
            price REAL NOT NULL DEFAULT 0,
            payment_status TEXT NOT NULL DEFAULT 'pending',
            tags TEXT,
            notes TEXT,
            sold_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY (seller_id) REFERENCES sellers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sellers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            added_by INTEGER NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS retrieval_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            requested_amount INTEGER NOT NULL,
            retrieved_amount INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS retrieval_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            used INTEGER DEFAULT 0,
            used_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES retrieval_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_items_session_id
        ON retrieval_items (session_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_items_used
        ON retrieval_items (used)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO categories (name, default_price) VALUES ('uncategorized', 0)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS command_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            seller_name TEXT,
            command TEXT NOT NULL,
            command_args TEXT,
            status TEXT NOT NULL DEFAULT 'success',
            error_reason TEXT,
            error_detail TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_command_logs_user_id
        ON command_logs (user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_command_logs_created_at
        ON command_logs (created_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_command_logs_command
        ON command_logs (command)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            reason TEXT,
            type TEXT NOT NULL DEFAULT 'add',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES sellers(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_dues_seller_id
        ON dues (seller_id)
    """)

    current_version = get_schema_version(conn)
    if current_version == 0:
        set_schema_version(conn, 1)
        conn.commit()
        current_version = 1

    migrate(conn, current_version)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")
