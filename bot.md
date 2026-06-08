# Reddit Account Selling Bot — Complete Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Database Schema](#database-schema)
5. [Role & Permission System](#role--permission-system)
6. [Commands Reference](#commands-reference)
7. [Detailed Command Flows](#detailed-command-flows)
8. [State Management](#state-management)
9. [Formatting & Output](#formatting--output)
10. [Notification System](#notification-system)
11. [Scheduled Reports](#scheduled-reports)
12. [Error Handling & Production Hardening](#error-handling--production-hardening)
13. [File Structure](#file-structure)

---

## Overview

A Telegram bot for selling Reddit accounts. Supports two user roles (Admin and Seller), tracks sales with buyer information, payment status, and generates revenue reports. Built with `python-telegram-bot` v21+, SQLite, and APScheduler.

**Currency:** INR (₹) — hardcoded throughout.
**High-value sale threshold:** ₹500 — triggers admin notification.

---

## Architecture

```
main.py                          Entry point, app builder, signal handling
config.py                        All env vars and constants
database/
  __init__.py                    Re-exports all DB functions
  connection.py                  connect(), init_db(), migrate(), schema versioning
  categories.py                  Category CRUD + default_price
  accounts.py                    Account CRUD + search + status/notes/optional fields
  sales.py                       Sale CRUD + revenue + tags
  sellers.py                     Seller CRUD (active/inactive)
  sessions.py                    Retrieval sessions (legacy from original bot)
handlers/
  __init__.py                    register_handlers(app) — wires all handlers
  start.py                       /start, /mainmenu, /ping
  accounts.py                    /add (wizard), /bulkadd, /getid, /delete, /bulkdelete, /extractcsv, /list
  sell.py                        /sell, /bulksell, /sales, /sale, /markpaid, /voidsale
  preview.py                     /preview (pull accounts for buyer)
  search.py                      /search with interactive filters
  categories.py                  /categories, /addcategory, /deletecategory
  inventory.py                   /inventory
  buyers.py                      /buyers, /buyer
  reports.py                     /report
  sellers.py                     /addseller, /removeseller, /listsellers
  export.py                      /export, /backup
  callbacks.py                   ALL callback query dispatch (button taps)
  messages.py                    handle_text (free-text input), handle_csv_upload
  errors.py                      error_handler
  help.py                        /help with subcommands
core/
  __init__.py
  permissions.py                 get_user_role(), require_admin(), require_seller()
  format.py                      esc(), reddit_url(), fmt_account_block(), fmt_sale_block(), fmt_receipt(), fmt_compact()
  keyboards.py                   category_keyboard(), main_menu_keyboard(), pagination, confirm, yes/no, filter keyboards
  state.py                       StateManager class with TTL expiry
  help_content.py                All help text for 12 topics
utils/
  __init__.py
  parsers.py                     parse_bulk_lines(), search query tokenizer
  csv_utils.py                   CSV column detection, import/export helpers
  scheduler.py                   APScheduler — daily & weekly reports
  notifications.py               Admin notification message builders
```

---

## Configuration

All config lives in `.env` and is loaded by `config.py`:

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `BOT_TOKEN` | str | — | **Yes** | Telegram bot token from @BotFather |
| `ADMIN_USER_ID` | int | — | **Yes** | Telegram user ID of the bot owner |
| `DAILY_REPORT_HOUR` | int | `9` | No | Hour for daily report (0-23) |
| `DAILY_REPORT_MINUTE` | int | `0` | No | Minute for daily report |
| `WEEKLY_REPORT_DAY` | str | `monday` | No | Day for weekly report |
| `TIMEZONE` | str | `Asia/Kolkata` | No | Timezone for scheduler |

**Hardcoded constants in `config.py`:**

| Constant | Value | Purpose |
|----------|-------|---------|
| `CURRENCY` | `₹` | Currency symbol displayed everywhere |
| `HIGH_VALUE_THRESHOLD` | `500` | Sales ≥ ₹500 trigger admin notification |
| `MAX_USERNAME_LEN` | `64` | Max Reddit username length |
| `MAX_PASSWORD_LEN` | `128` | Max password length |
| `MAX_EMAIL_LEN` | `128` | Max email length |
| `MAX_NOTES_LEN` | `512` | Max notes length |
| `MAX_BUYER_LEN` | `64` | Max buyer name length |

---

## Database Schema

SQLite database at `data/reddit_accounts.db`. 6 tables + schema_version.

### `categories`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `name` | TEXT | UNIQUE NOT NULL |
| `default_price` | REAL | DEFAULT 0 |

Default row: `('uncategorized', 0)` — seeded on init. Cannot be deleted.

### `accounts`

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `id` | INTEGER | auto | PRIMARY KEY |
| `username` | TEXT | — | NOT NULL |
| `password` | TEXT | — | NOT NULL |
| `email` | TEXT | NULL | Optional |
| `email_password` | TEXT | NULL | Optional |
| `has_2fa` | INTEGER | 0 | Boolean (0/1) |
| `is_verified` | INTEGER | 0 | Boolean (0/1) |
| `category_id` | INTEGER | — | FK → categories(id) ON DELETE RESTRICT |
| `notes` | TEXT | NULL | Optional |
| `status` | TEXT | `'active'` | One of: `active`, `sold`, `banned`, `locked`, `restricted` |
| `used` | INTEGER | 0 | Legacy flag, kept for backwards compat |
| `used_at` | TEXT | NULL | Timestamp when sold |
| `created_at` | TEXT | CURRENT_TIMESTAMP | |

**Unique index:** `(username, password, category_id)` — prevents exact duplicates.
**Index:** `ix_accounts_category_id` on `(category_id)`.

### `sellers`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `user_id` | INTEGER | UNIQUE NOT NULL — Telegram user ID |
| `name` | TEXT | NOT NULL |
| `added_by` | INTEGER | NOT NULL — admin's Telegram ID |
| `active` | INTEGER | DEFAULT 1 — soft-delete uses 0 |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP |

### `sales`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `account_id` | INTEGER | NOT NULL UNIQUE, FK → accounts(id) ON DELETE CASCADE |
| `seller_id` | INTEGER | NOT NULL, FK → sellers(id) |
| `buyer_name` | TEXT | NOT NULL |
| `price` | REAL | NOT NULL DEFAULT 0 |
| `payment_status` | TEXT | DEFAULT `'pending'` — values: `pending`, `paid` |
| `tags` | TEXT | NULL — freeform tags like `"vip"`, `"bulk"` |
| `notes` | TEXT | NULL |
| `sold_at` | TEXT | DEFAULT CURRENT_TIMESTAMP |

### `retrieval_sessions` / `retrieval_items`

Legacy tables from the original bot. Used by `/preview` to track which accounts were pulled for a buyer. Items cascade-delete when session is deleted.

### `schema_version`

| Column | Type |
|--------|------|
| `version` | INTEGER |

Tracks migrations. Current version: **2**. On startup, `init_db()` creates V1 schema then runs `migrate()` for incremental upgrades.

---

## Role & Permission System

### Roles

| Role | Who | How Assigned |
|------|-----|-------------|
| **Admin** | Bot owner | `ADMIN_USER_ID` in `.env` — exactly one user |
| **Seller** | Registered sellers | Via `/addseller <user_id> <name>` by admin |
| **None** | Unauthorized | Cannot access any command |

### Permission Check (`core/permissions.py`)

```python
def get_user_role(user_id):
    if user_id == ADMIN_USER_ID:
        return "admin"
    seller = get_seller_by_user_id(user_id)
    if seller and seller["active"]:
        return "seller"
    return None

def require_admin(update) → bool    # only admin
def require_seller(update) → bool   # admin + seller
```

### Permission Matrix

| Command | Admin | Seller | Type |
|---------|-------|--------|------|
| `/start`, `/help`, `/mainmenu`, `/ping` | ✅ | ✅ | Shared |
| `/add`, `/bulkadd`, `/extractcsv` | ✅ | ❌ | Account creation |
| `/delete`, `/bulkdelete` | ✅ | ❌ | Account deletion |
| `/list`, `/search`, `/getid` | ✅ | ✅ | Browse |
| `/sell`, `/bulksell` | ✅ | ✅ | Selling |
| `/sales` | ✅ (all) | ✅ (own only) | Sales view |
| `/sale` | ✅ | ✅ | Sale detail |
| `/markpaid` | ✅ | ✅ (own only) | Payment toggle |
| `/voidsale` | ✅ | ❌ | Sale voiding |
| `/preview` | ✅ | ✅ | Buyer preview |
| `/categories` | ✅ | ✅ | Read-only |
| `/addcategory`, `/deletecategory` | ✅ | ❌ | Category mgmt |
| `/inventory` | ✅ | ✅ | View only |
| `/buyers`, `/buyer` | ✅ (all) | ✅ (own only) | Buyer tracking |
| `/report` | ✅ | ❌ | Revenue reports |
| `/addseller`, `/removeseller`, `/listsellers` | ✅ | ❌ | Seller mgmt |
| `/export`, `/backup` | ✅ | ❌ | Data export |

---

## Commands Reference

### Account Management (Admin only)

#### `/add` — Add single account (10-step wizard)

Interactive wizard that walks through every field:

| Step | Bot asks | User sends | State key |
|------|----------|------------|-----------|
| 1 | "Send the Reddit username:" | text | `add_username` |
| 2 | "Send the password:" | text | `add_password` |
| 3 | "Send email (or /skip):" | text or /skip | `add_email` |
| 4 | "Send email password (or /skip):" | text or /skip | `add_email_password` |
| 5 | "Is 2FA enabled?" [Yes] [No] | button tap | `add_2fa` |
| 6 | "Is the account verified?" [Yes] [No] | button tap | `add_verified` |
| 7 | "Any notes? (or /skip)" | text or /skip | `add_notes` |
| 8 | "Select category:" [category buttons] | button tap | `add_category_id` |
| 9 | Confirmation block with all fields | [✅ Save] [❌ Cancel] | — |
| 10 | "✅ Account saved! (ID: #42)" | — | — |

**Implementation:** `handlers/messages.py` handles text input for steps 1-4, 7. `handlers/callbacks.py` handles button taps for steps 5, 6, 8, 9. State is tracked via `core/state.py` `StateManager` with 5-minute TTL.

#### `/bulkadd` — Bulk import accounts

1. Select category via inline keyboard (`bulkcat:` callback prefix)
2. Bot says: "Send accounts in format: `user:pass` — one per line. Send /done when finished."
3. User sends multiple lines of `username:password` pairs
4. Each text message appends to `bulk_lines` state (capped at 100KB)
5. User sends `/done` → `parse_bulk_lines()` parses → `add_accounts_bulk()` inserts
6. Bot reports: "📥 Bulk import: X added, Y skipped in CategoryName"
7. Admin gets notification

**Parse format:** `user:pass` or `user:pass,email,mailpass,2fa,verified,notes`

#### `/extractcsv` — CSV import

1. Select category (`csvcat:` prefix)
2. Upload CSV file (max 5MB)
3. `detect_columns()` auto-maps headers (username, password, email, etc.)
4. Shows preview of first 3 accounts
5. User taps [✅ Import] or [❌ Cancel]
6. `build_accounts_from_csv()` → `add_accounts_bulk()`

#### `/delete <id>` — Delete single account

Shows confirmation keyboard. On confirm → `delete_account(id)`.

#### `/bulkdelete` — Bulk delete

User enters comma-separated IDs OR a category name. Confirmation keyboard. On confirm → `delete_accounts_by_ids()` or `delete_accounts_in_category()`.

#### `/list` — Browse accounts

Paginated list (10 per page). Filter buttons:
- **All** — all accounts
- **Available** — status=active
- **Sold** — status=sold (used=1)
- **By Category** — shows category picker → filters by that category

Each page shows: `• #ID | username | category | status | ₹price`

### Account Browsing (Admin + Seller)

#### `/getid <id>` — View account by ID

Returns full account block with all fields (password hidden via spoiler tag).

#### `/search` — Search accounts

Interactive flow:
1. Tap search type: Username, Password, Category, Status, Buyer, Tag, Notes, General
2. Enter search value
3. Results shown (max 20)

**Search types and implementation:**
- Username/Password/Notes → `LIKE %term%` on respective columns
- Category → exact match (case-insensitive)
- Status → exact match on status column
- General → searches username, password, AND notes simultaneously
- Buyer/Tag → searches the sales table JOINed to accounts

### Selling (Admin + Seller)

#### `/sell` — Sell one account

1. Shows available accounts (status=active, max 20) as inline buttons
2. Tap to select → "Enter buyer name:"
3. Enter buyer name → "Enter price (or /skip for default):"
   - Default price comes from the account's category `default_price`
   - Price validation: must be numeric, ≥ 0
4. "Add tags? (or /skip)" → freeform text
5. Confirmation block → [✅ Confirm] [❌ Cancel]
6. On confirm: `sell_account()` inserts into sales table + sets account status to 'sold'
7. Bot sends receipt with Reddit profile link
8. Admin gets notification: "💰 New sale! #ID — buyer — ₹price — by SellerName"
9. If price ≥ ₹500: additional "🔥 High-value sale!" notification

**Implementation:** `handlers/sell.py` handles the command + text input. `handlers/callbacks.py` handles `sellselect:`, `sellconfirm`, `sellcancel`. State tracked via `sell_stage`, `sell_account_id`, `sell_buyer`, `sell_price`, `sell_tags`.

#### `/bulksell` — Bulk sell to one buyer

1. Enter buyer name
2. Enter price per account
3. Shows available accounts as toggleable buttons (✅ marks selected)
4. Tap accounts to toggle selection
5. [✅ Confirm (N selected)] [❌ Cancel]
6. `bulk_sell_accounts()` processes all selected
7. Admin notification

#### `/sales` — View sales

Paginated list (10 per page). Filter buttons: All / Pending / Paid.
Admin sees all sales. Seller sees only their own.

Format: `• #ID | buyer | ₹price | status | seller_name`

#### `/sale <id>` — Sale detail

Full sale block with all fields including account info, seller, category.

#### `/markpaid` — Toggle payment status

Shows pending sales. Tap one to toggle between `paid` and `pending`.
**Permission check:** Sellers can only mark their own sales (verified via `sale["seller_user_id"] == user_id`).

#### `/voidsale <id>` — Void a sale (Admin only)

Confirmation keyboard. On confirm: deletes sale record, resets account to `status='active'`, `used=0`.

### Preview

#### `/preview` — Pull accounts for buyer

1. Select category (or "All")
2. Enter count
3. Bot shows that many active accounts with Reddit profile links
4. Each account has a "💰 Sell #ID (username)" button → starts sell flow

### Categories

#### `/categories` — List all

Shows each category with account count and default price.

#### `/addcategory <name>` — Create (Admin only)

Usage: `/addcategory Finance`
Also accepts default price: not yet implemented in args, but category has `default_price` field.

#### `/deletecategory <name>` — Delete (Admin only)

Moves all accounts in that category to 'uncategorized'. Cannot delete 'uncategorized' itself.

### Inventory

#### `/inventory` — Stock overview

Shows per-category breakdown:
- 🟢 Active accounts
- 🔴 Sold accounts
- ⛔ Banned / 🔒 Locked / ⚠️ Restricted
- 💰 Total revenue
- Per-category active/sold counts

### Buyers

#### `/buyers` — List all buyers

Shows buyer name, total purchases, total spent, pending amount.
Admin sees all buyers. Seller sees only their own.

#### `/buyer <name>` — Buyer purchase history

Lists all sales to that buyer with: sale ID, category, price, status, date.

### Reports (Admin only)

#### `/report` — Revenue reports

Select period: Today / This Week / This Month / All Time

Shows:
- Total revenue for period
- Sales count for period
- Pending payments count + amount
- Total inventory (available + sold)
- Per-seller breakdown (name, sales count, earnings)
- Per-category breakdown
- All-time total revenue

### Seller Management (Admin only)

#### `/addseller <user_id> <name>` — Register seller

Creates seller record. Admin gets notification: "👤 New seller: Name (ID: user_id)"

#### `/removeseller <user_id>` — Soft-delete

Sets `active=0`. Keeps sales history intact. Admin gets notification.

#### `/listsellers` — List all

Shows each seller with 🟢/🔴 status, sales count, total earnings.

### Utilities

#### `/export` — Export accounts CSV

Admin only. Downloads CSV with all account fields + sale data.

#### `/backup` — Download database backup

Admin only. Creates timestamped copy: `backup_YYYYMMDD_HHMMSS.db` and sends as document.

#### `/ping` — Health check

Responds with "pong". Available to all authorized users.

#### `/help [topic]` — Help system

Main help shows different topic lists for admin vs seller.
12 subcommands: sell, preview, accounts, search, categories, sales, buyers, inventory, reports, sellers, settings.

### Main Menu

Tapping `/start` or `/mainmenu` shows an inline keyboard:

**Admin menu:**
```
➕ Add account    📂 Preview
💰 Sell           📈 Sales
👥 Sellers        📋 List
🔎 Search         📊 Report
📦 Inventory      ⚙️ Settings
```

**Seller menu:**
```
📂 Preview        💰 Sell
📋 My Sales       🔎 Search
📦 Inventory      📋 List
```

---

## Detailed Command Flows

### Add Account Wizard (Step-by-step implementation)

```
User: /add
  ↓
handlers/accounts.py:add_cmd()
  → state.set(user_id, "add_stage", "username")
  → reply "Send the Reddit username:"

User: "cool_redditor"
  ↓
handlers/messages.py:handle_text() — stage == "username"
  → validates len(text) <= 64
  → state.set(user_id, "add_username", "cool_redditor")
  → state.set(user_id, "add_stage", "password")
  → reply "✅ Username: cool_redditor\nSend the password:"

User: "MyP@ssw0rd"
  ↓
handlers/messages.py:handle_text() — stage == "password"
  → validates len(text) <= 128
  → state.set(user_id, "add_password", "MyP@ssw0rd")
  → state.set(user_id, "add_stage", "email")
  → reply "✅ Password saved\nSend email (or /skip):"

User: "user@gmail.com"
  ↓
handlers/messages.py:handle_text() — stage == "email"
  → state.set(user_id, "add_email", "user@gmail.com")
  → state.set(user_id, "add_stage", "email_password")
  → reply "✅ Email: user@gmail.com\nSend email password (or /skip):"

User: /skip
  ↓
handlers/messages.py:handle_text() — stage == "email_password"
  → state.set(user_id, "add_email_password", None)
  → state.set(user_id, "add_stage", "2fa")
  → reply "Is 2FA enabled?" + yes_no_keyboard("add2fa")

User: taps "Yes"
  ↓
handlers/callbacks.py:handle_callback() — data == "add2fa:yes"
  → state.set(user_id, "add_2fa", True)
  → state.set(user_id, "add_stage", "verified")
  → edit_message "✅ 2FA: Yes\nIs the account verified?" + yes_no_keyboard("addverified")

User: taps "No"
  ↓
handlers/callbacks.py:handle_callback() — data == "addverified:no"
  → state.set(user_id, "add_verified", False)
  → state.set(user_id, "add_stage", "notes")
  → edit_message "✅ Verified: No\nAny notes? (or /skip)"

User: "premium account"
  ↓
handlers/messages.py:handle_text() — stage == "notes"
  → validates len(text) <= 512
  → state.set(user_id, "add_notes", "premium account")
  → state.set(user_id, "add_stage", "category")
  → reply "✅ Notes saved\nSelect category:" + category_keyboard("addcat")

User: taps "Finance (15)"
  ↓
handlers/callbacks.py:handle_callback() — data == "addcat:2"
  → state.set(user_id, "add_category_id", 2)
  → state.set(user_id, "add_stage", "confirm")
  → builds confirmation preview with all fields
  → edit_message preview + confirm_keyboard("addconfirm", "addcancel")

User: taps "✅ Confirm"
  ↓
handlers/callbacks.py:handle_callback() — data == "addconfirm"
  → pops all state keys (add_username, add_password, etc.)
  → calls add_account(username, password, category_id, email=..., ...)
  → database/accounts.py:add_account() → INSERT INTO accounts
  → edit_message "✅ Account saved! (ID: #42)"
```

### Sell Flow (Step-by-step implementation)

```
User: /sell
  ↓
handlers/sell.py:sell_cmd()
  → verifies user is registered seller
  → lists active accounts (limit 20)
  → state.set(user_id, "sell_stage", "select_account")
  → reply with sell_accounts_keyboard(accounts, "sellselect")

User: taps "#1 | test_user"
  ↓
handlers/callbacks.py:handle_callback() — data == "sellselect:1"
  → state.set(user_id, "sell_account_id", 1)
  → state.set(user_id, "sell_stage", "buyer")
  → edit_message "Account: test_user\n\nEnter buyer name:"

User: "john_doe"
  ↓
handlers/messages.py:handle_text() — sell_stage == "buyer"
  → validates len(text) <= 64
  → state.set(user_id, "sell_buyer", "john_doe")
  → looks up category default_price
  → state.set(user_id, "sell_stage", "price")
  → reply "Buyer: john_doe\nDefault price: ₹500\nEnter price (or /skip for default):"

User: "750"
  ↓
handlers/messages.py:handle_text() — sell_stage == "price"
  → parses float, validates >= 0
  → state.set(user_id, "sell_price", 750)
  → state.set(user_id, "sell_stage", "tags")
  → reply "Add tags? (or /skip)"

User: "vip bulk"
  ↓
handlers/messages.py:handle_text() — sell_stage == "tags"
  → state.set(user_id, "sell_tags", "vip bulk")
  → builds confirmation preview
  → state.set(user_id, "sell_stage", "confirm")
  → reply confirmation + confirm_keyboard("sellconfirm", "sellcancel")

User: taps "✅ Confirm"
  ↓
handlers/callbacks.py:handle_callback() — data == "sellconfirm"
  → pops sell_account_id, sell_buyer, sell_price, sell_tags
  → calls sell_account(account_id, seller_id, buyer, price, tags=...)
  → database/sales.py:sell_account() → INSERT INTO sales + UPDATE accounts SET status='sold'
  → builds receipt via fmt_receipt()
  → edit_message receipt
  → notify_admin("💰 New sale! #12 — john_doe — ₹750 — by Alice")
  → if price >= 500: notify_admin("🔥 High-value sale! ...")
```

---

## State Management

### StateManager (`core/state.py`)

Replaces 9 raw in-memory dicts from the original bot with a single class:

```python
class StateManager:
    def __init__(self, ttl_seconds=300):
        self._states: dict[int, dict] = {}      # user_id → {key: value}
        self._timestamps: dict[int, float] = {}  # user_id → last_activity
        self.ttl = ttl_seconds                    # 5 minutes

    def set(user_id, key, value)     # Store value
    def get(user_id, key, default)   # Retrieve value (returns default if expired)
    def pop(user_id, key, default)   # Retrieve + delete
    def clear(user_id)               # Wipe all state for user
    def has(user_id, key) → bool     # Check existence
```

**TTL:** 5 minutes. If a user hasn't interacted for 5 minutes, all their state is automatically cleared on next access. Additionally, `_maybe_cleanup()` runs every 60 seconds on `set()` calls and proactively removes expired users from memory.

**State keys used per flow:**

| Flow | Keys |
|------|------|
| Add wizard | `add_stage`, `add_username`, `add_password`, `add_email`, `add_email_password`, `add_2fa`, `add_verified`, `add_notes`, `add_category_id` |
| Bulk add | `bulk_stage`, `bulk_category`, `bulk_lines` |
| Sell | `sell_stage`, `sell_account_id`, `sell_buyer`, `sell_price`, `sell_tags` |
| Bulk sell | `bulksell_stage`, `bulksell_buyer`, `bulksell_price`, `bulksell_selected` |
| Preview | `preview_stage`, `preview_category` |
| Search | `search_stage`, `search_type` |
| List filter | `list_filter`, `list_page` |
| Sales filter | `sales_filter`, `sales_page` |
| Bulk delete | `bulk_delete_mode`, `bulk_delete_input` |
| CSV import | `csv_stage`, `csv_category`, `csv_headers`, `csv_data`, `csv_mapping` |
| Delete confirm | `delete_confirm` |
| Void confirm | `void_confirm` |

---

## Formatting & Output

All output uses HTML parse mode (`ParseMode.HTML`).

### Account Block (`core/format.py`)

```
╭─ Account #42 ────────────────
│ 👤 Username: cool_redditor
│ 🔑 Password: <tg-spoiler>MyP@ss</tg-spoiler>
│ 📧 Email: user@gmail.com
│ 🔑 Email Pass: <tg-spoiler>emailpass</tg-spoiler>
│ 🔐 2FA: Yes
│ ✅ Verified: Yes
│ 🔗 Profile: https://reddit.com/user/cool_redditor
│ 📂 Category: Finance
│ 📦 Status: active
│ 📝 Notes: premium account
╰──────────────────────────
```

### Sale Block

```
╭─ Sale #12 ────────────────
│ 👤 Buyer: john_doe
│ 💰 Price: ₹750
│ 💳 Status: paid
│ 🏷️ Tags: vip bulk
│ 📅 Sold: 2026-06-08
│ 👨‍💼 Seller: Alice
│ 🔗 Profile: https://reddit.com/user/cool_redditor
│ 📂 Category: Finance
╰──────────────────────────
```

### Buyer Receipt

```
╔══════════════════════════════════╗
║     🧾 Reddit Account Receipt    ║
╠══════════════════════════════════╣
║ Account: cool_redditor
║ Password: <tg-spoiler>MyP@ss</tg-spoiler>
║ Profile: reddit.com/user/cool_redditor
║──────────────────────────────────║
║ Price: ₹750
║ Sale ID: #12
║ Date: 2026-06-08
╚══════════════════════════════════╝
```

### Compact List Format

```
• #42 | cool_redditor | Finance | active | ₹500
```

### Input Validation

All user-supplied text goes through `esc()` which wraps `html.escape()`. Passwords are wrapped in `<tg-spoiler>` tags. Length limits enforced at every input step. Prices validated as non-negative floats. File uploads capped at 5MB.

---

## Notification System

All notifications sent to `ADMIN_USER_ID` via `utils/notifications.py`.

| Event | Trigger | Message Format |
|-------|---------|----------------|
| Sale made | `/sell` confirm | `💰 New sale! #12 — john_doe — ₹750 — by Alice` |
| Payment received | `/markpaid` toggle to paid | `✅ Payment received! Sale #12 — ₹750 from john_doe` |
| High-value sale | sale price ≥ ₹500 | `🔥 High-value sale! #12 — ₹750 from john_doe — by Alice` |
| Sale voided | `/voidsale` confirm | `♻️ Sale #12 voided — account returned to stock` |
| Seller registered | `/addseller` | `👤 New seller: Alice (ID: 123456789)` |
| Seller removed | `/removeseller` | `🚫 Seller removed: Bob (ID: 987654321)` |
| Bulk import | `/bulkadd` /done or CSV confirm | `📥 Bulk import: 15 added, 2 skipped in Finance` |
| CSV import | CSV confirm | `📥 CSV import: 15 added, 2 skipped in Finance` |

---

## Scheduled Reports

APScheduler with `AsyncIOScheduler` + `CronTrigger`. Timezone: `Asia/Kolkata`.

### Daily Report (default: 9:00 AM)

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

### Weekly Report (default: Monday 9:00 AM)

Same format but covers the last 7 days, plus all-time total.

---

## Error Handling & Production Hardening

### Logging

- **File:** `logs/reddit-seller-bot.log` — rotating, 5MB per file, 5 backups
- **Console:** stdout
- **Format:** `%(asctime)s | %(levelname)s | %(name)s | %(message)s`
- Third-party loggers (telegram, urllib3, asyncio) set to WARNING

### Graceful Shutdown

`signal.signal(SIGINT, shutdown)` and `signal.signal(SIGTERM, shutdown)` registered in `main.py`. On signal:
1. Logs "Shutdown signal received"
2. Calls `scheduler.shutdown(wait=False)`
3. Process exits

### Database Migrations

`schema_version` table tracks current version. `init_db()` creates V1 schema, then runs `migrate()` for incremental upgrades. V1→V2 migration:
- Adds `default_price` to categories
- Adds `email`, `email_password`, `has_2fa`, `is_verified`, `notes`, `status` to accounts
- Creates `sellers` table
- Creates `sales` table
- Creates `schema_version` table

Each ALTER TABLE is wrapped in try/except to handle already-applied migrations.

### Input Limits

| Field | Max Length |
|-------|-----------|
| Username | 64 chars |
| Password | 128 chars |
| Email | 128 chars |
| Notes | 512 chars |
| Buyer name | 64 chars |
| CSV upload | 5MB |
| Bulk input | 100KB |
| Message output | 4000 chars (truncated) |

### State Cleanup

`StateManager._maybe_cleanup()` runs every 60 seconds, removes all users with no activity for >5 minutes. Prevents memory leaks from abandoned flows.

---

## File Structure

```
manager-telegram-bot/
├── main.py                      # Entry point, app builder, signal handling
├── config.py                    # All settings from .env
├── requirements.txt             # python-telegram-bot, python-dotenv, apscheduler
├── .env                         # Environment variables (gitignored)
├── .gitignore                   # data/, logs/, .env*, __pycache__/, .venv/
├── README.md                    # Setup instructions
├── bot.md                       # This file
├── database/
│   ├── __init__.py              # Re-exports all DB functions
│   ├── connection.py            # connect(), init_db(), migrate()
│   ├── categories.py            # Category CRUD
│   ├── accounts.py              # Account CRUD + search
│   ├── sales.py                 # Sale CRUD + revenue
│   ├── sellers.py               # Seller CRUD
│   └── sessions.py              # Retrieval sessions (legacy)
├── handlers/
│   ├── __init__.py              # register_handlers(app)
│   ├── start.py                 # /start, /mainmenu, /ping
│   ├── accounts.py              # /add, /bulkadd, /getid, /delete, /bulkdelete, /extractcsv, /list
│   ├── sell.py                  # /sell, /bulksell, /sales, /sale, /markpaid, /voidsale
│   ├── preview.py               # /preview
│   ├── search.py                # /search
│   ├── categories.py            # /categories, /addcategory, /deletecategory
│   ├── inventory.py             # /inventory
│   ├── buyers.py                # /buyers, /buyer
│   ├── reports.py               # /report
│   ├── sellers.py               # /addseller, /removeseller, /listsellers
│   ├── export.py                # /export, /backup
│   ├── callbacks.py             # All CallbackQueryHandler dispatch
│   ├── messages.py              # handle_text, handle_csv_upload
│   ├── errors.py                # error_handler
│   └── help.py                  # /help
├── core/
│   ├── __init__.py
│   ├── permissions.py           # get_user_role(), require_admin(), require_seller()
│   ├── format.py                # esc(), fmt_account_block(), fmt_sale_block(), fmt_receipt()
│   ├── keyboards.py             # All inline keyboard builders
│   ├── state.py                 # StateManager with TTL
│   └── help_content.py          # Help text for 12 topics
├── utils/
│   ├── __init__.py
│   ├── parsers.py               # parse_bulk_lines(), search tokenizer
│   ├── csv_utils.py             # CSV column detection, import/export
│   ├── scheduler.py             # APScheduler daily/weekly reports
│   └── notifications.py         # Admin notification builders
├── data/                        # SQLite DB files (gitignored)
└── logs/                        # Log files (gitignored)
```
