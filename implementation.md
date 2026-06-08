# Implementation Plan — Reddit Account Seller Bot

## Overview

Transform the existing Telegram bot from a generic credential vault into a **Reddit account selling platform** with multi-user roles (Admin + Seller), sales tracking, payment management, buyer tracking, inventory management, revenue reports, scheduled reporting, and a fully UI-based interactive workflow.

**Currency:** INR (₹) — hardcoded throughout.  
**Timezone default:** `Asia/Kolkata`  
**High-value sale threshold:** ₹500 (triggers 🔥 notification to admin)

---

## Current State

### Files
| File | Lines | Description |
|------|-------|-------------|
| `bot.py` | ~2300 | All bot logic: commands, callbacks, formatting, keyboards, state |
| `database.py` | ~688 | All database functions (34 total, 32 used, 2 dead) |
| `config.py` | 18 | Env vars: `BOT_TOKEN`, `ALLOWED_USER_ID`, `BOT_NAME`, `SERVICE_NAME` |

### Database Schema (4 tables)
- **`categories`** — `id`, `name` (UNIQUE). Seed: `uncategorized`
- **`accounts`** — `id`, `username`, `password`, `category_id` (FK), `used` (0/1), `used_at`, `created_at`. Unique index on `(username, password, category_id)`
- **`retrieval_sessions`** — `id`, `user_id`, `category_id` (FK), `requested_amount`, `retrieved_amount`, `created_at`
- **`retrieval_items`** — `id`, `session_id` (FK CASCADE), `account_id` (FK CASCADE), `position`, `used`, `used_at`, `created_at`

### Current State Management (9 in-memory dicts)
`pending_adds`, `pending_bulk`, `pending_gets`, `pending_bulk_delete`, `pending_bulk_delete_confirm`, `pending_delete_confirm`, `pending_delete_category_confirm`, `pending_csv_extract`, `pending_search`

### Bug Fixes Already Applied
1. `handle_text` — added stage check for `pending_bulk` (KeyError crash fix)
2. `handle_text` — added stage check for `pending_gets` (KeyError crash fix)
3. `handle_text` — interactive search used/unused filter was silently dropped (now handled)
4. `database.py` — `set_item_used` cascading to account incorrectly (now multi-session aware)

---

## Target Architecture

```
manager-telegram-bot/
├── main.py                      # Entry point, app builder, signal handling
├── config.py                    # All settings (ADMIN_USER_ID, CURRENCY, etc.)
├── database/
│   ├── __init__.py              # Re-exports all DB functions
│   ├── connection.py            # connect(), init_db(), migrate(), schema_version
│   ├── categories.py            # Category CRUD + default_price
│   ├── accounts.py              # Account CRUD + search + status/notes/optional fields
│   ├── sales.py                 # Sale CRUD + revenue + tags
│   ├── sellers.py               # Seller CRUD (active/inactive)
│   └── sessions.py              # Retrieval/preview sessions (from original)
├── handlers/
│   ├── __init__.py              # register_handlers(app) — wires everything
│   ├── start.py                 # /start, /mainmenu, /ping
│   ├── accounts.py              # /add (UI wizard), /bulkadd, /getid, /delete, /bulkdelete, /extractcsv
│   ├── sell.py                  # /sell (UI), /bulksell, /sales, /sale, /markpaid, /voidsale
│   ├── preview.py               # /preview (was /getaccounts)
│   ├── search.py                # /search + perform_search + interactive filters
│   ├── categories.py            # /categories, /addcategory, /deletecategory
│   ├── inventory.py             # /inventory
│   ├── buyers.py                # /buyers, /buyer
│   ├── reports.py               # /report
│   ├── sellers.py               # /addseller, /removeseller, /listsellers
│   ├── export.py                # /export, /backup
│   ├── callbacks.py             # All CallbackQueryHandler dispatch
│   ├── messages.py              # handle_text, handle_csv_upload
│   ├── errors.py                # error_handler
│   └── help.py                  # /help command + subcommands
├── core/
│   ├── __init__.py
│   ├── permissions.py           # get_user_role(), require_admin(), require_seller()
│   ├── format.py                # fmt_account_block(), fmt_sale_block(), fmt_receipt(), esc()
│   ├── keyboards.py             # category_keyboard(), main_menu_keyboard(), pagination, etc.
│   ├── state.py                 # StateManager class with TTL expiry
│   └── help_content.py          # Help text content for all subcommands
├── utils/
│   ├── __init__.py
│   ├── parsers.py               # parse_bulk_lines(), search query tokenizer
│   ├── csv_utils.py             # CSV column detection, import/export helpers
│   ├── scheduler.py             # APScheduler — daily & weekly reports
│   └── notifications.py         # Admin notification helpers
├── data/                        # SQLite DB files (gitignored)
├── logs/                        # Log files (gitignored)
├── .env                         # Environment variables
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Database Schema (Final)

### `categories` — Modified
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `name` | TEXT | UNIQUE NOT NULL |
| `default_price` | REAL | DEFAULT 0 |

### `accounts` — Modified
| Column | Type | Required | Default |
|--------|------|----------|---------|
| `id` | INTEGER | auto | PRIMARY KEY AUTOINCREMENT |
| `username` | TEXT | **Yes** | NOT NULL |
| `password` | TEXT | **Yes** | NOT NULL |
| `email` | TEXT | No | NULL |
| `email_password` | TEXT | No | NULL |
| `has_2fa` | INTEGER | No | 0 (false) |
| `is_verified` | INTEGER | No | 0 (false) |
| `category_id` | INTEGER | **Yes** | FK -> categories(id) ON DELETE RESTRICT |
| `notes` | TEXT | No | NULL |
| `status` | TEXT | No | 'active' |
| `used` | INTEGER | No | 0 (legacy, keep for backwards compat) |
| `used_at` | TEXT | No | NULL |
| `created_at` | TEXT | No | CURRENT_TIMESTAMP |

**Unique index:** `(username, password, category_id)`  
**Index:** `ix_accounts_category_id`  
**Status values:** `active`, `sold`, `banned`, `locked`, `restricted`

### `sellers` — New
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `user_id` | INTEGER | UNIQUE NOT NULL |
| `name` | TEXT | NOT NULL |
| `added_by` | INTEGER | NOT NULL (admin's Telegram ID) |
| `active` | INTEGER | NOT NULL DEFAULT 1 |
| `created_at` | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP |

### `sales` — New
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `account_id` | INTEGER | NOT NULL UNIQUE, FK -> accounts(id) ON DELETE CASCADE |
| `seller_id` | INTEGER | NOT NULL, FK -> sellers(id) |
| `buyer_name` | TEXT | NOT NULL |
| `price` | REAL | NOT NULL DEFAULT 0 |
| `payment_status` | TEXT | NOT NULL DEFAULT 'pending' |
| `tags` | TEXT | NULL |
| `notes` | TEXT | NULL |
| `sold_at` | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP |

### `retrieval_sessions` — Keep as-is
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `user_id` | INTEGER | NOT NULL |
| `category_id` | INTEGER | NOT NULL, FK -> categories(id) ON DELETE RESTRICT |
| `requested_amount` | INTEGER | NOT NULL |
| `retrieved_amount` | INTEGER | NOT NULL |
| `created_at` | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP |

### `retrieval_items` — Keep as-is
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `session_id` | INTEGER | NOT NULL, FK -> retrieval_sessions(id) ON DELETE CASCADE |
| `account_id` | INTEGER | NOT NULL, FK -> accounts(id) ON DELETE CASCADE |
| `position` | INTEGER | NOT NULL |
| `used` | INTEGER | NOT NULL DEFAULT 0 |
| `used_at` | TEXT | NULL |
| `created_at` | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP |

**Indexes:** `ix_items_session_id`, `ix_items_used`

### `schema_version` — New (migration tracking)
| Column | Type |
|--------|------|
| `version` | INTEGER |

---

## Database Functions

### `database/connection.py`
| Function | Signature | Purpose |
|----------|-----------|---------|
| `connect()` | `() -> Connection` | Open SQLite connection with row_factory |
| `init_db()` | `() -> None` | Create tables, indexes, run migrations, seed uncategorized |
| `get_schema_version()` | `(conn) -> int` | Read current schema version |
| `set_schema_version()` | `(conn, version) -> None` | Update schema version |

### `database/categories.py`
| Function | Signature | Purpose |
|----------|-----------|---------|
| `add_category(name, default_price=0)` | `(str, float) -> tuple[bool, str]` | Create category |
| `delete_category(name)` | `(str) -> tuple[bool, str]` | Delete, move accounts to uncategorized |
| `list_categories()` | `() -> list[Row]` | All categories with account count + default_price |
| `get_category_name(category_id)` | `(int) -> str | None` | Name by ID |
| `get_category_id_by_name(name)` | `(str) -> int | None` | ID by name (case-insensitive) |
| `update_category_price(category_id, price)` | `(int, float) -> bool` | Set default price |

### `database/accounts.py`
| Function | Signature | Purpose |
|----------|-----------|---------|
| `add_account(username, password, category_id, email=None, email_password=None, has_2fa=False, is_verified=False, notes=None)` | `(...) -> tuple[bool, str, int | None]` | Insert account with optional fields |
| `add_accounts_bulk(items, category_id)` | `(Iterable[dict], int) -> dict` | Bulk insert with optional fields |
| `get_account_by_id(account_id)` | `(int) -> Row | None` | Full account details with category |
| `list_accounts(limit, offset, used=None, category_id=None, status=None)` | `(...) -> list[Row]` | Paginated with optional filters |
| `count_accounts(used=None, category_id=None, status=None)` | `(...) -> int` | Count with optional filters |
| `search_accounts(term, category, used, newest_first, username, password, status, notes_term)` | `(...) -> list[Row]` | Full-text search + filter |
| `set_account_sold(account_id, sold)` | `(int, bool) -> bool` | Mark sold/unsold (was set_account_used) |
| `set_account_status(account_id, status)` | `(int, str) -> bool` | Change status (active/banned/locked/restricted) |
| `update_account_notes(account_id, notes)` | `(int, str) -> bool` | Update notes |
| `update_account_optional_fields(account_id, email, email_password, has_2fa, is_verified)` | `(...) -> bool` | Update optional fields |
| `delete_account(account_id)` | `(int) -> bool` | Delete single |
| `delete_accounts_by_ids(ids)` | `(Iterable[int]) -> int` | Bulk delete by IDs |
| `delete_accounts_in_category(category_id)` | `(int) -> int` | Delete all in category |
| `get_accounts_for_category(category_id, limit)` | `(int, int) -> list[Row]` | Get by category |
| `get_unused_accounts_for_category(category_id, limit)` | `(int, int) -> list[Row]` | Get where status=active |
| `export_accounts_csv()` | `() -> bytes` | Full CSV export |

### `database/sales.py`
| Function | Signature | Purpose |
|----------|-----------|---------|
| `sell_account(account_id, seller_id, buyer, price, tags=None, notes=None)` | `(...) -> tuple[bool, str, int | None]` | Create sale + mark account as sold |
| `bulk_sell_accounts(ids, seller_id, buyer, price_each, tags=None, notes=None)` | `(...) -> dict` | Sell multiple to same buyer |
| `mark_payment(sale_id, status)` | `(int, str) -> bool` | Set paid/pending |
| `get_sales(limit, offset, seller_id=None, buyer=None, status=None, tag=None)` | `(...) -> list[Row]` | Paginated with filters |
| `get_sale_by_id(sale_id)` | `(int) -> Row | None` | Full sale detail with account + seller |
| `get_buyers(seller_id=None)` | `(int | None) -> list[Row]` | Buyer list with totals |
| `get_buyer_sales(buyer, seller_id=None, limit=20)` | `(...) -> list[Row]` | Buyer purchase history |
| `get_sales_summary(seller_id=None, period=None)` | `(...) -> dict` | Revenue + counts by period |
| `void_sale(sale_id)` | `(int) -> bool` | Delete sale, reset account to active |

### `database/sellers.py`
| Function | Signature | Purpose |
|----------|-----------|---------|
| `add_seller(user_id, name, added_by)` | `(int, str, int) -> tuple[bool, str]` | Register seller |
| `remove_seller(user_id)` | `(int) -> bool` | Soft-delete (active=0) |
| `list_sellers()` | `() -> list[Row]` | All sellers with sale counts + earnings |
| `get_seller_by_user_id(user_id)` | `(int) -> Row | None` | Lookup by Telegram ID |
| `get_seller_by_id(seller_id)` | `(int) -> Row | None` | Lookup by PK |
| `is_seller_active(user_id)` | `(int) -> bool` | Quick active check |

### `database/sessions.py` (unchanged from original)
`create_retrieval_session`, `add_retrieval_item`, `list_recent_sessions`, `get_session`, `get_session_items`, `delete_session`, `get_item`, `set_item_used`, `list_pending_items`, `count_pending_items`

---

## Role & Permission System

### Roles
| Role | Who | How Assigned |
|------|-----|-------------|
| **Admin** | Bot owner | `ADMIN_USER_ID` in `.env` |
| **Seller** | Registered sellers | Via `/addseller` by admin |
| **None** | Unauthorized | Cannot access any command |

### Permission Matrix
| Command | Admin | Seller | Type |
|---------|-------|--------|------|
| `/start`, `/help`, `/mainmenu`, `/ping` | ✅ | ✅ | Shared |
| `/add`, `/bulkadd`, `/extractcsv` | ✅ | ❌ | Account management |
| `/delete`, `/bulkdelete` | ✅ | ❌ | Account deletion |
| `/list`, `/search`, `/getid` | ✅ | ✅ | Browse |
| `/sell`, `/bulksell` | ✅ | ✅ | Selling |
| `/sales` | ✅ (all) | ✅ (own only) | Sales view |
| `/sale` | ✅ | ✅ | Sale detail |
| `/markpaid` | ✅ | ✅ | Payment tracking |
| `/voidsale` | ✅ | ❌ | Sale voiding |
| `/preview` (was /getaccounts) | ✅ | ✅ | Buyer preview |
| `/categories` | ✅ | ✅ | Read-only |
| `/addcategory`, `/deletecategory` | ✅ | ❌ | Category management |
| `/inventory` | ✅ | ✅ | View only |
| `/buyers` | ✅ (all) | ✅ (own only) | Buyer tracking |
| `/buyer` | ✅ (all) | ✅ (own only) | Buyer detail |
| `/report` | ✅ | ❌ | Revenue reports |
| `/addseller`, `/removeseller`, `/listsellers` | ✅ | ❌ | Seller management |
| `/export`, `/backup` | ✅ | ❌ | Data export |

### Permission Check Implementation
```python
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

def get_user_role(user_id: int) -> str | None:
    if user_id == ADMIN_USER_ID:
        return "admin"
    seller = get_seller_by_user_id(user_id)
    if seller and seller["active"]:
        return "seller"
    return None

def require_admin(update) -> bool:
    if get_user_role(update.effective_user.id) == "admin":
        return True
    logger.warning("Unauthorized admin access from user_id=%s", ...)
    return False

def require_seller(update) -> bool:
    if get_user_role(update.effective_user.id) in ("admin", "seller"):
        return True
    logger.warning("Unauthorized seller access from user_id=%s", ...)
    return False
```

---

## Commands — Full Reference

### Admin Commands (also available to seller where marked)

#### Account Management (Admin only)
| Command | Description | Flow |
|---------|-------------|------|
| `/add` | Add single account | 10-step UI wizard (username → password → email → email_pass → 2FA → verified → notes → category → confirm) |
| `/bulkadd` | Bulk import | Select category → paste lines (`user:pass,email,mailpass,2fa,verified,notes`) → /done → results |
| `/extractcsv` | CSV import | Select category → upload CSV → column mapping UI (tap to assign each field) → preview → confirm |
| `/delete` | Delete account | Shows list → select → confirm |
| `/bulkdelete` | Bulk delete | Enter IDs or category name → confirm |

#### Account Browsing (Admin + Seller)
| Command | Description | Flow |
|---------|-------------|------|
| `/list` | Browse accounts | Paginated list with filter buttons (All/Available/Sold/By Category) |
| `/search` | Search accounts | Shows search type buttons (term, username, password, ID, category, status, buyer, tag, notes) → enter value → results |
| `/getid` | View by ID | Enter ID → full account details |

#### Selling (Admin + Seller)
| Command | Description | Flow |
|---------|-------------|------|
| `/sell` | Sell one account | Shows available accounts → select → enter buyer → enter price (auto-filled from category default) → tags (optional) → confirm → receipt |
| `/bulksell` | Bulk sell | Enter buyer → enter price → select multiple accounts → confirm |
| `/sales` | View sales | Paginated list with filter buttons (All/Pending/Paid). Admin sees all, seller sees own |
| `/sale` | Sale detail | Enter ID or select from list → full sale info |
| `/markpaid` | Mark payment | Shows pending sales → select → toggles to paid |
| `/voidsale` | Void sale (Admin only) | Shows sales → select → confirm → account returns to stock |

#### Preview (Admin + Seller)
| Command | Description | Flow |
|---------|-------------|------|
| `/preview` | Pull accounts for buyer | Select category → enter count → shows accounts with Reddit links + "Sell" buttons |

#### Categories
| Command | Description | Permission |
|---------|-------------|------------|
| `/categories` | List categories | Admin + Seller (read-only for seller) |
| `/addcategory` | Create category | Admin only |
| `/deletecategory` | Delete category | Admin only |

#### Inventory (Admin + Seller, read-only for seller)
| Command | Description |
|---------|-------------|
| `/inventory` | Shows per-category breakdown: active/sold/banned/locked/restricted counts + total value |

#### Buyers (Admin sees all, seller sees own)
| Command | Description |
|---------|-------------|
| `/buyers` | List all buyers with total spent and purchase count |
| `/buyer <name>` | View buyer's purchase history |

#### Reports (Admin only)
| Command | Description |
|---------|-------------|
| `/report` | Revenue by period (Today/This Week/This Month/All Time) + pending payments + by-category breakdown |

#### Seller Management (Admin only)
| Command | Description |
|---------|-------------|
| `/addseller <user_id> <name>` | Register a seller |
| `/removeseller <user_id>` | Soft-delete a seller (keeps history) |
| `/listsellers` | List all sellers with sales count + earnings |

#### Utilities
| Command | Description | Permission |
|---------|-------------|------------|
| `/export` | Export all accounts as CSV with sale data | Admin only |
| `/backup` | Download timestamped DB backup | Admin only |
| `/ping` | Health check (responds "pong") | Admin + Seller |

---

## UI-Based Add Account Wizard (10 Steps)

```
Step 1  → "Send the Reddit username:"
Step 2  → "✅ Username: xxx\nSend the password:"
Step 3  → "✅ Password saved\nSend email (or /skip):"
Step 4  → "✅ Email: xxx\nSend email password (or /skip):"
Step 5  → "✅ Email password saved\nIs 2FA enabled?" [Yes] [No]
Step 6  → "✅ 2FA: Yes/No\nIs the account verified?" [Yes] [No]
Step 7  → "✅ Verified: Yes/No\nAny notes? (or /skip)"
Step 8  → "✅ Notes saved\nSelect category:" [category buttons]
Step 9  → Show confirmation block with all fields [✅ Save] [❌ Cancel]
Step 10 → "✅ Account saved! (ID: #42)"
```

**State tracking:** `state.set(user_id, "add_stage", step_name)` — each step advances the wizard.

---

## CSV Import Column Mapping Flow

```
Step 1 → Select category
Step 2 → Upload CSV file
Step 3 → Bot shows detected column headers as buttons
Step 4 → "Which column is the Reddit username?" [tap column name]
Step 5 → "Which column is the password?" [tap column name]
Step 6 → "Which column is the email? (or /skip)" [tap column name or /skip]
Step 7 → "Which column is email password? (or /skip)"
Step 8 → "Which column is 2FA status? (or /skip)"
Step 9 → "Which column is verified status? (or /skip)"
Step 10 → Show preview of first 3 rows → [✅ Import] [❌ Cancel]
```

---

## Help System (`/help [topic]`)

### Main `/help` — Role-Aware Topic List
Shows different topic lists for admin vs seller.

### Subcommands
| Topic | Content |
|-------|---------|
| `/help sell` | Selling accounts — quick sell, bulk sell, mark paid, void sale |
| `/help preview` | Previewing accounts for buyers |
| `/help accounts` | Adding/managing accounts — single, bulk, CSV, delete |
| `/help search` | Search syntax — all filters with examples |
| `/help categories` | Category management — create, list, delete |
| `/help sales` | Viewing sales — list, detail, mark paid, void |
| `/help buyers` | Buyer tracking — list, history |
| `/help inventory` | Inventory overview — counts by status |
| `/help reports` | Revenue reports — periods, breakdowns (admin only) |
| `/help sellers` | Seller management — add, remove, list (admin only) |
| `/help settings` | Bot configuration — .env variables |

---

## Notification System (`utils/notifications.py`)

Admin gets notified on these events:

| Event | Trigger | Format |
|-------|---------|--------|
| Sale made | Any `/sell` or `/bulksell` | `💰 New sale! #12 — john_doe — ₹500 — by Alice` |
| Payment received | `/markpaid` | `✅ Payment received! Sale #12 — ₹500 from john_doe` |
| High-value sale | Sale >= ₹500 | `🔥 High-value sale! #12 — ₹500 from john_doe — by Alice` |
| Sale voided | `/voidsale` | `♻️ Sale #12 voided — account returned to stock` |
| Seller registered | `/addseller` | `👤 New seller: Alice (ID: 123456789)` |
| Seller removed | `/removeseller` | `🚫 Seller removed: Bob (ID: 987654321)` |
| Bulk import | `/bulkadd` or CSV import | `📥 Bulk import: 15 added, 2 skipped in Finance` |
| Account status change | Status update | `⚠️ Account #42 status: active → banned` |

---

## Scheduling (`utils/scheduler.py`)

- **Daily report:** Sent at configurable hour/minute to admin via DM
- **Weekly report:** Sent on configurable day at same hour to admin via DM
- **Uses APScheduler** with `AsyncIOScheduler` and `CronTrigger`
- **Default timezone:** `Asia/Kolkata`

**Report format:**
```
📊 Daily Sales Report — 2026-06-08

💰 Revenue today: ₹2,500
📈 Sales today: 5
💳 Pending payments: 3 (₹1,500)
📦 Total inventory: 120 available, 45 sold

By seller:
• Alice: 3 sales, ₹1,500
• Bob: 2 sales, ₹1,000
```

---

## Formatting (`core/format.py`)

### Account Block
```
╭─ Account #42 ─────────────────
│ 👤 Username: reddit_user123
│ 🔑 Password: ••••••••
│ 📧 Email: user@gmail.com
│ 🔑 Email Pass: ••••••••
│ 🔐 2FA: Yes
│ ✅ Verified: Yes
│ 🔗 Profile: reddit.com/user/reddit_user123
│ 📂 Category: Finance
│ 📦 Status: active
│ 📝 Notes: —
╰──────────────────────────
```

### Sale Block
```
╭─ Sale #12 ─────────────────
│ 👤 Buyer: john_doe
│ 💰 Price: ₹500
│ 💳 Status: paid
│ 🏷️ Tags: vip
│ 📅 Sold: 2026-06-08
│ 👨‍💼 Seller: Alice
│ 🔗 Profile: reddit.com/user/reddit_user123
│ 📂 Category: Finance
╰──────────────────────────
```

### Buyer Receipt
```
╔══════════════════════════════════╗
║     🧾 Reddit Account Receipt    ║
╠══════════════════════════════════╣
║ Account: reddit_user123          ║
║ Password: MyP@ssw0rd             ║
║ Profile: reddit.com/user/reddit  ║
║──────────────────────────────────║
║ Price: ₹500                      ║
║ Sale ID: #12                     ║
║ Date: 2026-06-08                 ║
╚══════════════════════════════════╝
```

### Compact List Format
```
• #42 | reddit_user123 | Finance | active | ₹0
```

---

## Main Menu Layouts

### Admin Menu
```
➕ Add account    📂 Preview
💰 Sell           📈 Sales
👥 Sellers        📋 List
🔎 Search         📊 Report
📦 Inventory      ⚙️ Settings
```

### Seller Menu
```
📂 Preview        💰 Sell
📋 My Sales       🔎 Search
📦 Inventory      📋 List
```

---

## StateManager (`core/state.py`)

Replaces all 9 raw in-memory dicts with a TTL-aware class:

```python
class StateManager:
    def __init__(self, ttl_seconds=300):
        self._states: dict[int, dict] = {}
        self._timestamps: dict[int, float] = {}
        self.ttl = ttl_seconds

    def set(self, user_id, key, value)
    def get(self, user_id, key, default=None)
    def pop(self, user_id, key, default=None)
    def clear(self, user_id)
    def has(self, user_id, key) -> bool
    def _is_expired(self, user_id) -> bool
```

**TTL:** 5 minutes (auto-clears stale states to prevent memory leaks).

---

## Production Hardening

### Database Migrations
- `schema_version` table tracks current version
- `init_db()` creates V1 schema, then runs `migrate()` for incremental upgrades
- Migration V2: add sales/sellers tables, add accounts optional columns, add categories.default_price

### Logging
- Rotating file handler (5MB per file, 5 backups)
- Console handler for stdout
- Structured format: `%(asctime)s | %(levelname)s | %(name)s | %(message)s`
- Third-party loggers (telegram, urllib3) set to WARNING

### Input Validation
- Max username length: 64 chars
- Max password length: 128 chars
- Max email length: 128 chars
- Max notes length: 512 chars
- Max buyer name length: 64 chars
- All numeric IDs validated as positive integers
- All text HTML-escaped via `esc()` function

### Graceful Shutdown
- `signal.signal(SIGINT, shutdown)` / `signal.signal(SIGTERM, shutdown)`
- Scheduler shuts down cleanly
- DB connections close properly

### Backup
- `/backup` — admin-only command
- Creates timestamped copy: `data/backup_YYYYMMDD_HHMMSS.db`
- Sends as document to admin

### Health Check
- `/ping` — responds with `pong`
- Available to all authorized users

---

## Config (`config.py`)

```python
from dotenv import load_dotenv
load_dotenv()

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_NAME = os.getenv("BOT_NAME", "Reddit Account Vault").strip() or "Reddit Account Vault"
SERVICE_NAME = os.getenv("SERVICE_NAME", "Reddit Accounts").strip() or "Reddit Accounts"

CURRENCY = "₹"
HIGH_VALUE_THRESHOLD = 500

DAILY_REPORT_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "9"))
DAILY_REPORT_MINUTE = int(os.getenv("DAILY_REPORT_MINUTE", "0"))
WEEKLY_REPORT_DAY = os.getenv("WEEKLY_REPORT_DAY", "monday").lower()
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in .env")
if not ADMIN_USER_ID:
    raise RuntimeError("ADMIN_USER_ID is missing or invalid in .env")
```

### `.env` Template
```
BOT_TOKEN=your_token_here
ADMIN_USER_ID=123456789
BOT_NAME=Reddit Account Vault
SERVICE_NAME=Reddit Accounts
DAILY_REPORT_HOUR=9
DAILY_REPORT_MINUTE=0
WEEKLY_REPORT_DAY=monday
TIMEZONE=Asia/Kolkata
```

---

## requirements.txt
```
python-telegram-bot>=21.0
python-dotenv>=1.0.1
apscheduler>=3.10.0
```

---

## Implementation Order (31 Steps)

### Phase 1: Project Structure (Step 1)
1. Create directory skeleton: `database/`, `handlers/`, `core/`, `utils/`, `data/`, `logs/`
2. Create `__init__.py` in each package directory

### Phase 2: Config (Step 2)
3. Rewrite `config.py` with `ADMIN_USER_ID`, `CURRENCY="₹"`, `HIGH_VALUE_THRESHOLD=500`, scheduler settings

### Phase 3: Database Layer (Steps 3-8)
4. `database/connection.py` — `connect()`, `init_db()`, `migrate()`, schema versioning
5. `database/categories.py` — all category functions + `default_price`
6. `database/accounts.py` — all account functions + optional fields + status
7. `database/sales.py` — all new sale functions
8. `database/sellers.py` — all new seller functions
9. `database/sessions.py` — extracted retrieval session functions
10. `database/__init__.py` — re-export all public functions

### Phase 4: Core Utilities (Steps 9-13)
11. `core/permissions.py` — `get_user_role()`, `require_admin()`, `require_seller()`
12. `core/state.py` — `StateManager` class with TTL
13. `core/format.py` — `esc()`, `reddit_url()`, `fmt_account_block()`, `fmt_sale_block()`, `fmt_receipt()`
14. `core/keyboards.py` — `category_keyboard()`, `main_menu_keyboard()`, pagination, confirm keyboards
15. `core/help_content.py` — all help topic text content

### Phase 5: Handlers (Steps 14-25)
16. `handlers/start.py` — `/start`, `/mainmenu`, `/ping`
17. `handlers/accounts.py` — `/add` (10-step UI), `/bulkadd`, `/getid`, `/delete`, `/bulkdelete`, `/extractcsv`
18. `handlers/sell.py` — `/sell` (UI), `/bulksell`, `/sales`, `/sale`, `/markpaid`, `/voidsale`
19. `handlers/preview.py` — `/preview` (was /getaccounts)
20. `handlers/search.py` — `/search` + `perform_search` with new filters
21. `handlers/categories.py` — `/categories`, `/addcategory`, `/deletecategory`
22. `handlers/inventory.py` — `/inventory`
23. `handlers/buyers.py` — `/buyers`, `/buyer`
24. `handlers/reports.py` — `/report`
25. `handlers/sellers.py` — `/addseller`, `/removeseller`, `/listsellers`
26. `handlers/export.py` — `/export`, `/backup`
27. `handlers/callbacks.py` — all CallbackQueryHandler dispatch
28. `handlers/messages.py` — `handle_text`, `handle_csv_upload`
29. `handlers/errors.py` — `error_handler`
30. `handlers/help.py` — `/help` command + subcommand routing
31. `handlers/__init__.py` — `register_handlers(app)`

### Phase 6: Utilities (Steps 26-27)
32. `utils/parsers.py` — `parse_bulk_lines()`, search tokenizer
33. `utils/csv_utils.py` — CSV column detection, export helpers
34. `utils/scheduler.py` — APScheduler daily/weekly reports
35. `utils/notifications.py` — admin notification helpers

### Phase 7: Entry Point (Step 28-29)
36. `main.py` — app builder, handler registration, scheduler setup, signal handling
37. `requirements.txt` — add `apscheduler`

### Phase 8: Production Hardening (Step 30-31)
38. Add input validation in all handlers
39. Add graceful shutdown in `main.py`
40. Update `.gitignore` for `data/`, `logs/`, `.env`
41. Write `README.md` with full docs

---

## Summary of Changes from Original

| Aspect | Original | New |
|--------|----------|-----|
| **File count** | 3 (.py files) | ~30 files |
| **DB tables** | 4 | 6 (+ sales, sellers) + schema_version |
| **DB functions** | 34 | ~50 |
| **Bot commands** | 22 | ~30 |
| **Roles** | Single user (ALLOWED_USER_ID) | Admin + Seller + None |
| **State management** | 9 raw dicts | StateManager with TTL |
| **Account fields** | username, password | + email, email_password, has_2fa, is_verified, notes, status |
| **Currency** | None | ₹ (INR, hardcoded) |
| **Sales tracking** | `used` flag only | Full sales table with buyer, price, payment, tags |
| **UI approach** | Mixed (args + inline) | Fully UI-based (wizards, inline keyboards) |
| **Scheduling** | None | Daily/weekly reports via APScheduler |
| **Notifications** | None | Admin notified on all key events |
| **Help system** | Single /start message | 12 subcommands with detailed docs |
| **Migrations** | None | Schema version table + incremental migrations |
| **Backups** | None | `/backup` command |
| **Health check** | None | `/ping` command |
