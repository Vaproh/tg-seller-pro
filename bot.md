# Reddit Account Selling Bot — Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Database Schema](#database-schema)
5. [Roles & Permissions](#roles--permissions)
6. [Commands Reference](#commands-reference)
7. [Sell Flow](#sell-flow)
8. [Filtering System](#filtering-system)
9. [CSV Import](#csv-import)
10. [State Management](#state-management)
11. [Scheduled Jobs](#scheduled-jobs)
12. [Notifications](#notifications)
13. [File Structure](#file-structure)

---

## Overview

A Telegram bot for selling Reddit accounts. Two roles (Admin and Seller), tracks sales with buyer info, payment status, and generates revenue reports.

- **Currency:** ₹ (INR, hardcoded)
- **High-value threshold:** ₹500 (triggers admin alert)
- **Pending payment reminder:** every 4 hours
- **Tech:** python-telegram-bot v21+, SQLite, APScheduler

---

## Architecture

```
main.py                 Entry point, app builder, signal handling
config.py               All env vars and constants

database/               SQLite layer
  connection.py           connect(), init_db(), migrate() (V1→V3)
  categories.py           Category CRUD + default_price
  accounts.py             Account CRUD + search + filters
  sales.py                Sale CRUD + revenue + payment
  sellers.py              Seller CRUD (active/inactive)
  sessions.py             Legacy retrieval sessions

handlers/               Telegram handlers
  __init__.py             register_handlers(app)
  callbacks/              Button tap handlers (split by domain)
    __init__.py           try_handle() chain dispatch
    menu.py               menu:back callback
    add.py                Add account wizard (add2fa, addverified, addcat, addconfirm, addcancel)
    sell.py               Sell flow + bulk sell (sellconfirm, bulksellcancel, etc.)
    list.py               List, delete, inventory, mark status, bulk delete, category delete
    sales.py              Sales view + sale status (markpaid, marksaleunsold, sellervoidconfirm, voidconfirm)
    csv.py                CSV import (csvcol, csvbool, csvskip, csvconfirm, csvcancel)
    search.py             Search callbacks
    misc.py               Stats, sellers, report, settings, export, backup, help, preview
  messages.py             Free-text input + CSV upload
  sell.py                 /sell, /bulksell, /sales, /sale, /markpaid, /voidsale, /marksold, /markunsold, /markpendingpayment
  accounts.py             /add, /bulkadd, /getid, /delete, /bulkdelete, /extractcsv, /list
  search.py               /search with multi-filters
  preview.py              /preview (pull accounts for buyer)
  categories.py           /categories, /addcategory, /deletecategory
  inventory.py            /inventory
  buyers.py               /buyers, /buyer
  reports.py              /report
  sellers.py              /addseller, /removeseller, /listsellers
  export.py               /export, /backup
  start.py                /start, /mainmenu, /ping
  help.py                 /help with topic keyboard
  errors.py               error_handler

core/                   Shared modules
  permissions.py          get_user_role(), require_admin(), require_seller()
  format.py               esc(), fmt_account_block(), fmt_sale_block(), fmt_receipt()
  keyboards.py            main_menu_keyboard(), category_keyboard(), confirm, etc.
  filters.py              Reusable filter system (shared across sell/list/delete/search/inventory)
  state.py                StateManager with 5-min TTL
  help_content.py         Help text for 14 topics + 30+ command topics

utils/                  Utilities
  scheduler.py            APScheduler — daily, weekly, pending payment jobs
  notifications.py        Admin notification builders
  csv_utils.py            CSV column detection + import/export
  parsers.py              parse_bulk_lines(), CSV parser, search tokenizer
```

---

## Configuration

`.env` file loaded by `config.py`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | — | Telegram bot token from @BotFather |
| `ADMIN_USER_ID` | Yes | — | Telegram user ID of bot owner |
| `DAILY_REPORT_HOUR` | No | `9` | Hour for daily report (0-23) |
| `DAILY_REPORT_MINUTE` | No | `0` | Minute for daily report |
| `WEEKLY_REPORT_DAY` | No | `monday` | Day for weekly report |
| `TIMEZONE` | No | `Asia/Kolkata` | Timezone for scheduler |

**Hardcoded constants:**

| Constant | Value | Purpose |
|----------|-------|---------|
| `CURRENCY` | `₹` | Currency symbol |
| `HIGH_VALUE_THRESHOLD` | `500` | Sales ≥ ₹500 trigger alert |
| `MAX_USERNAME_LEN` | `64` | Max username length |
| `MAX_PASSWORD_LEN` | `128` | Max password length |
| `MAX_EMAIL_LEN` | `128` | Max email length |
| `MAX_NOTES_LEN` | `512` | Max notes length |
| `MAX_BUYER_LEN` | `64` | Max buyer name length |

---

## Database Schema

SQLite at `data/reddit_accounts.db`. Schema version: **3**.

### `categories`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PRIMARY KEY |
| `name` | TEXT | UNIQUE NOT NULL |
| `default_price` | REAL | DEFAULT 0 |

Default row: `('uncategorized', 0)` — cannot be deleted.

### `accounts`

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `id` | INTEGER | auto | PRIMARY KEY |
| `username` | TEXT | — | NOT NULL |
| `password` | TEXT | — | NOT NULL |
| `email` | TEXT | NULL | Optional |
| `email_password` | TEXT | NULL | Optional |
| `has_2fa` | INTEGER | 0 | Boolean |
| `is_verified` | INTEGER | 0 | Boolean |
| `category_id` | INTEGER | — | FK → categories |
| `notes` | TEXT | NULL | Optional |
| `status` | TEXT | `'available'` | `available`, `sold`, `pending_payment` |
| `created_at` | TEXT | timestamp | |

**Unique index:** `(username, password, category_id)` — prevents duplicates.

### `sellers`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PRIMARY KEY |
| `user_id` | INTEGER | UNIQUE — Telegram user ID |
| `name` | TEXT | Display name |
| `added_by` | INTEGER | Admin's Telegram ID |
| `active` | INTEGER | 1=active, 0=removed (soft delete) |
| `created_at` | TEXT | |

### `sales`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PRIMARY KEY |
| `account_id` | INTEGER | UNIQUE, FK → accounts |
| `seller_id` | INTEGER | FK → sellers |
| `buyer_name` | TEXT | |
| `price` | REAL | |
| `payment_status` | TEXT | `pending` or `paid` |
| `notes` | TEXT | NULL |
| `sold_at` | TEXT | |

### Other tables

- `retrieval_sessions` / `retrieval_items` — legacy from original bot
- `schema_version` — tracks migrations

### Migrations

- **V1→V2:** Added categories.default_price, accounts optional fields, sellers, sales tables
- **V2→V3:** Migrated statuses (`active` → `available`), removed `used` column

---

## Roles & Permissions

| Role | Who | Assigned by |
|------|-----|-------------|
| **Admin** | Bot owner | `ADMIN_USER_ID` in `.env` |
| **Seller** | Team members | `/addseller` by admin |
| **None** | Unauthorized | Cannot use any command |

**Permission matrix:**

| Command | Admin | Seller |
|---------|-------|--------|
| `/add`, `/bulkadd`, `/extractcsv` | ✅ | ❌ |
| `/delete`, `/bulkdelete` | ✅ | ❌ |
| `/list`, `/search`, `/getid` | ✅ | ✅ |
| `/sell`, `/bulksell` | ✅ | ✅ |
| `/sales` | ✅ all | ✅ own |
| `/sale` | ✅ | ✅ |
| `/markpaid` | ✅ | ✅ own |
| `/voidsale` | ✅ | ❌ |
| `/marksold`, `/markunsold`, `/markpendingpayment` | ✅ | ✅ |
| `/preview` | ✅ | ✅ |
| `/categories` | ✅ | ✅ |
| `/addcategory`, `/deletecategory` | ✅ | ❌ |
| `/inventory` | ✅ | ✅ |
| `/buyers`, `/buyer` | ✅ all | ✅ own |
| `/report` | ✅ | ❌ |
| `/addseller`, `/removeseller`, `/listsellers` | ✅ | ❌ |
| `/export`, `/backup` | ✅ | ❌ |

---

## Commands Reference

### Account Management (Admin only)

**`/add`** — 10-step wizard:
Username → Password → Email → Email Pass → 2FA → Verified → Notes → Category → Confirm

**`/bulkadd`** — Select category → paste `user:pass` lines → `/done`

**`/extractcsv`** — Select category → upload CSV → map columns (with Yes/No buttons for 2FA/Verified or select from CSV) → preview → import

**`/delete`** — Pass ID (`/delete 123`) or use filter menu to browse and select

**`/bulkdelete`** — Enter comma-separated IDs or a category name

### Browsing (Admin + Seller)

**`/list`** — Browse accounts, 5 per page with filter buttons:
- 🟢 Available / 🔴 Sold / 🟡 Pending / 📂 Category / 🔢 By ID
- Format: `• ID: 1  |  User: xxx  |  Category: xxx`

**`/search`** — Tap search type → enter value → results
- Types: 👤 Username, 🔑 Password, 📂 Category, 📊 Status, 👤 Buyer, 🏷️ Tag, 📝 Notes, 🔍 General, 🔢 By ID
- Status search shows 2 results + count
- Category/status: tap from list

**`/getid <id>`** — Full account details with password hidden

### Selling (Admin + Seller)

**`/sell`** — Sell one account:
1. Shows 🟢 available accounts (filtered)
2. Pick buyer (from previous buyers list or type new)
3. Enter price (required)
4. Choose 🟢 Sold or 🟡 Pending Payment
5. Confirm → receipt sent

**`/bulksell`** — Choose mode:
- **Select:** tap accounts to toggle, then Done
- **Number:** enter count, auto-picks available
- Then: buyer → price → status → confirm

**`/sales`** — View sales with filters (🟡 Pending / ✅ Paid / 📋 All)
- 5 per page, admin sees all, seller sees own

**`/sale <id>`** — Full sale detail with actions:
- ✅ Mark Paid / 🟡 Mark Pending / 🔴 Mark Unsold / ♻️ Void

**`/markpaid`** — Shows pending sales, tap to mark as paid

**`/voidsale <id>`** — Cancel sale, account returns to available

**`/marksold <id>`** — Mark account 🔴 sold
**`/markunsold <id>`** — Mark account 🟢 available
**`/markpendingpayment <id>`** — Mark account 🟡 pending

### Other

**`/preview`** — Select category → enter count → shows accounts with Reddit links + quick-sell buttons

**`/categories`** — List all with account counts

**`/addcategory <name>`** — Create new category
**`/deletecategory <name>`** — Delete (accounts move to uncategorized)

**`/inventory`** — Overview: 🟢 available / 🔴 sold / 🟡 pending per category + total revenue

**`/buyers`** — List all buyers with total spent
**`/buyer <name>`** — Purchase history for one buyer

**`/report`** — Pick period → revenue, sales count, pending, per-seller, per-category

**`/addseller <user_id> <name>`** — Register team member
**`/removeseller <user_id>`** — Remove (soft delete)
**`/listsellers`** — List all with stats

**`/export`** — Download accounts as CSV
**`/backup`** — Download database file

**`/help`** — Shows command list + inline keyboard to browse 14 topics + per-command help (`/help sell`)

---

## Sell Flow

```
/sell
  ↓
Shows 🟢 available accounts with filter buttons
  ↓
User taps account
  ↓
Shows buyer list (from previous sales) + "Type new" button
  ↓
User picks buyer or types name
  ↓
"Enter price (₹):"
  ↓
User types price
  ↓
"Mark as:" → [🟢 Sold] [🟡 Pending Payment]
  ↓
User picks status
  ↓
Confirmation preview → [✅ Confirm] [❌ Cancel]
  ↓
On confirm:
  → sell_account() in database/sales.py
  → Sets account status to 'sold' or 'pending_payment'
  → Shows receipt with price + status
  → Admin notification
  → If ≥ ₹500: high-value alert
```

---

## Filtering System

Shared across `/list`, `/sell`, `/bulksell`, `/delete`, `/inventory`.

**Filter buttons:**
- 📋 All — show everything
- 🟢 Available — only unsold
- 🔴 Sold — only sold
- 🟡 Pending — only waiting for payment
- 📂 Category — tap to pick category
- 🔢 By ID — type comma-separated IDs

**Sell flows** default to 🟢 available only.

**Pagination:** 5 results per page, ⬅️ ➡️ navigation.

**Implementation:** `core/filters.py` provides:
- `apply_list_filters(filter_str, limit, offset)` — universal filter
- `filter_page_keyboard(prefix, page, total_pages, ...)` — keyboard builder
- `fmt_account_list_page(accounts, page, total_pages, title)` — formatted output
- `parse_filter_state(filter_str)` / `build_filter_state(...)` — filter string handling

---

## CSV Import

**Flow:**
1. `/extractcsv` → pick category → upload CSV
2. Bot detects columns, shows mapping UI
3. Map: username (required), password (required), email, email password
4. For 2FA/Verified: **Yes/No buttons** or **select from CSV column**
5. Map notes (optional)
6. Preview first 3 accounts → Confirm

**Column mapping UI:**
- Tap a column header to map it
- "⏭️ Skip" to skip optional fields
- "Yes/No" buttons for boolean fields (sets all rows to that value)
- "Select from CSV" shows column headers to pick from

---

## State Management

`StateManager` with 5-minute TTL. Prevents memory leaks via periodic cleanup.

**Key state flows:**

| Flow | Keys |
|------|------|
| Add wizard | `add_stage`, `add_username`, `add_password`, `add_email`, etc. |
| Sell | `sell_stage`, `sell_account_id`, `sell_buyer`, `sell_price`, `sell_payment_status` |
| Bulk sell | `bulksell_stage`, `bulksell_selected`, `bulksell_buyer`, `bulksell_price` |
| Search | `search_stage`, `search_type` |
| List/Delete/Inventory filters | `list_filter`, `list_page`, `delete_filter`, etc. |
| CSV import | `csv_stage`, `csv_mapping`, `csv_headers`, `csv_data` |
| ID input | `sell_ids_input`, `list_ids_input`, `del_ids_input` |

---

## Scheduled Jobs

APScheduler `AsyncIOScheduler` with three jobs:

| Job | Schedule | What it does |
|-----|----------|--------------|
| Daily report | Configured hour/minute | Revenue, sales, inventory breakdown |
| Weekly report | Configured day + hour | Same but for the week + all-time total |
| Pending payment | Every 4 hours | Lists all pending sales with IDs, buyers, amounts |

All sent to `ADMIN_USER_ID`.

---

## Notifications

| Event | Message |
|-------|---------|
| New sale | `💰 New sale! #ID — buyer — ₹price (status) — by seller` |
| Payment received | `✅ Payment received! Sale #ID — ₹price from buyer` |
| High-value sale | `🔥 High-value sale! #ID — ₹price from buyer — by seller` |
| Sale voided | `♻️ Sale #ID voided — account returned to available stock` |
| Bulk sell | `💰 Bulk sell: N accounts to buyer — ₹price each (status) — by seller` |
| Seller added | `👤 New seller: Name (ID: user_id)` |
| Seller removed | `🚫 Seller removed: Name (ID: user_id)` |
| Bulk/CSV import | `📥 Import: N added, N skipped in Category` |

---

## File Structure

```
manager-telegram-bot/
├── main.py                 # Entry point
├── config.py               # Env config
├── requirements.txt        # Dependencies (incl. pytest)
├── .env.example            # Env template
├── .gitignore
├── Dockerfile              # Docker build (Python 3.12-slim)
├── docker-compose.yml      # Container config + volume mounts
├── .dockerignore           # Docker build exclusions
├── deploy.sh               # Deploy script (deploy/restart/stop/test/logs)
├── README.md               # Setup guide
├── bot.md                  # This file
├── database/
│   ├── __init__.py
│   ├── connection.py       # connect(), init_db(), migrate() — WAL mode, busy_timeout
│   ├── categories.py
│   ├── accounts.py
│   ├── sales.py
│   ├── sellers.py
│   └── sessions.py
├── handlers/
│   ├── __init__.py
│   ├── callbacks/          # Button handlers (split by domain)
│   │   ├── __init__.py     # try_handle() chain dispatch
│   │   ├── menu.py
│   │   ├── add.py
│   │   ├── sell.py
│   │   ├── list.py
│   │   ├── sales.py
│   │   ├── csv.py
│   │   ├── search.py
│   │   └── misc.py
│   ├── messages.py         # Text input + CSV upload
│   ├── sell.py
│   ├── accounts.py
│   ├── search.py
│   ├── preview.py
│   ├── categories.py
│   ├── inventory.py
│   ├── buyers.py
│   ├── reports.py
│   ├── sellers.py
│   ├── export.py
│   ├── start.py
│   ├── help.py
│   └── errors.py
├── core/
│   ├── __init__.py
│   ├── permissions.py
│   ├── format.py           # esc(), _truncate(), fmt_account_block(), fmt_sale_block(), fmt_receipt()
│   ├── keyboards.py
│   ├── filters.py          # Shared filter system
│   ├── state.py
│   └── help_content.py
├── utils/
│   ├── __init__.py
│   ├── scheduler.py
│   ├── notifications.py
│   ├── csv_utils.py
│   └── parsers.py
├── tests/                  # pytest test suite (116 tests)
│   ├── conftest.py         # Test fixtures (isolated DB per test)
│   ├── test_database.py
│   ├── test_sales.py
│   ├── test_categories.py
│   ├── test_format.py
│   ├── test_parsers.py
│   ├── test_csv_utils.py
│   ├── test_state.py
│   ├── test_filters.py
│   ├── test_permissions.py
│   └── test_handlers.py
├── data/                   # SQLite DB (gitignored)
└── logs/                   # Log files (gitignored)
```
