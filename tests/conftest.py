import os
import sys
import tempfile
import pytest

# Point to project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Override env before any project imports
os.environ["BOT_TOKEN"] = "test:fake-token-for-tests"
os.environ["ADMIN_USER_ID"] = "12345"


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Each test gets a fresh in-memory-like DB via a temp file."""
    import database.connection as conn_mod

    db_path = str(tmp_path / "test.db")
    conn_mod.DB_PATH = db_path

    from database import init_db

    init_db()
    yield db_path
    # cleanup is automatic via tmp_path


@pytest.fixture
def db():
    from database.connection import connect

    conn = connect()
    yield conn
    conn.close()


@pytest.fixture
def seed_accounts(db):
    """Create sample categories and accounts for tests."""
    db.execute("INSERT INTO categories (name, default_price) VALUES ('cat_a', 100)")
    db.execute("INSERT INTO categories (name, default_price) VALUES ('cat_b', 200)")
    db.execute(
        "INSERT INTO accounts (username, password, category_id, status) VALUES (?, ?, ?, ?)",
        ("user1", "pass1", 1, "available"),
    )
    db.execute(
        "INSERT INTO accounts (username, password, category_id, status) VALUES (?, ?, ?, ?)",
        ("user2", "pass2", 1, "available"),
    )
    db.execute(
        "INSERT INTO accounts (username, password, category_id, status) VALUES (?, ?, ?, ?)",
        ("user3", "pass3", 2, "sold"),
    )
    db.execute(
        "INSERT INTO sellers (user_id, name, added_by) VALUES (?, ?, ?)",
        (999, "TestSeller", 12345),
    )
    db.commit()
    yield
