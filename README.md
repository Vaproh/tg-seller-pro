# Reddit Account Selling Bot

A Telegram bot for managing and selling Reddit accounts. Built with python-telegram-bot v21+, SQLite, and APScheduler.

## Features

- **Account Management** — Add single, bulk, or CSV import
- **Selling** — Sell individually or in bulk with buyer tracking
- **Payment Tracking** — Pending/paid status with 4-hour reminders
- **Inventory** — Real-time stock overview by category and status
- **Search** — Multi-filter search by username, category, status, buyer, etc.
- **Reports** — Daily, weekly, and custom period revenue reports
- **Multi-seller** — Admin + seller roles with permission controls
- **Scheduled Reports** — Auto daily/weekly reports + pending payment alerts

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/Vaproh/manager-telegram-bot.git
cd manager-telegram-bot
pip install -r requirements.txt
```

### 2. Create `.env`

```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_USER_ID=your_telegram_user_id
```

Optional:
```env
DAILY_REPORT_HOUR=9
DAILY_REPORT_MINUTE=0
WEEKLY_REPORT_DAY=monday
TIMEZONE=Asia/Kolkata
```

### 3. Run

```bash
python main.py
```

## Docker Deployment

### Using deploy script (recommended)

```bash
# Deploy (pull + build + start)
./deploy.sh deploy

# Other commands
./deploy.sh restart    # Restart bot
./deploy.sh stop       # Stop bot
./deploy.sh start      # Start bot
./deploy.sh logs       # View logs
./deploy.sh status     # Container status
./deploy.sh test       # Run test suite
./deploy.sh rebuild    # Full rebuild from scratch
```

### Manual Docker

```bash
# Build and start
docker compose up -d --build

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Commands

### Account Management
| Command | Description |
|---------|-------------|
| `/add` | Add single account (step-by-step wizard) |
| `/bulkadd` | Bulk import (user:pass format) |
| `/extractcsv` | Import from CSV file |
| `/delete` | Delete account (by ID or filter) |
| `/bulkdelete` | Bulk delete by IDs or category |

### Browsing
| Command | Description |
|---------|-------------|
| `/list` | Browse accounts with filters |
| `/search` | Search with multi-filters |
| `/getid <id>` | View account details |

### Selling
| Command | Description |
|---------|-------------|
| `/sell` | Sell one account (available only) |
| `/bulksell` | Bulk sell (select or by number) |
| `/sales` | View all sales |
| `/sale <id>` | View sale detail |
| `/markpaid` | Mark pending sale as paid |
| `/voidsale` | Cancel a sale (admin) |

### Status Management
| Command | Description |
|---------|-------------|
| `/marksold <id>` | Mark account as sold |
| `/markunsold <id>` | Mark account as available |
| `/markpendingpayment <id>` | Mark as pending payment |

### Other
| Command | Description |
|---------|-------------|
| `/preview` | Show accounts to buyer |
| `/categories` | List all categories |
| `/addcategory <name>` | Create category |
| `/deletecategory <name>` | Delete category |
| `/inventory` | Stock overview |
| `/buyers` | List all buyers |
| `/buyer <name>` | Buyer purchase history |
| `/report` | Revenue reports |
| `/addseller <id> <name>` | Register seller (admin) |
| `/removeseller <id>` | Remove seller (admin) |
| `/listsellers` | List all sellers |
| `/export` | Download CSV (admin) |
| `/backup` | Download database (admin) |
| `/help` | Help with inline topic browser |

## Account Statuses

| Status | Meaning |
|--------|---------|
| 🟢 `available` | Ready to sell |
| 🔴 `sold` | Already sold |
| 🟡 `pending_payment` | Sold, waiting for payment |

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | — | Telegram bot token |
| `ADMIN_USER_ID` | Yes | — | Admin Telegram ID |
| `DAILY_REPORT_HOUR` | No | `9` | Hour for daily report |
| `WEEKLY_REPORT_DAY` | No | `monday` | Day for weekly report |
| `TIMEZONE` | No | `Asia/Kolkata` | Timezone |

## Project Structure

```
├── main.py                 # Entry point
├── config.py               # Environment config
├── requirements.txt        # Dependencies (incl. pytest)
├── .env.example            # Env template
├── Dockerfile              # Docker build (Python 3.12-slim)
├── docker-compose.yml      # Container config + volume mounts
├── .dockerignore           # Docker build exclusions
├── deploy.sh               # Deploy script (deploy/restart/stop/test/logs)
├── bot.md                  # Full documentation
├── database/               # SQLite database layer
│   ├── connection.py       # DB connection + migrations (WAL mode)
│   ├── categories.py       # Category CRUD
│   ├── accounts.py         # Account CRUD + search
│   ├── sales.py            # Sale CRUD + revenue
│   ├── sellers.py          # Seller CRUD
│   └── sessions.py         # Legacy retrieval sessions
├── handlers/               # Telegram command handlers
│   ├── callbacks/          # Button handlers (split by domain)
│   │   ├── __init__.py     # Chain dispatch
│   │   ├── menu.py, add.py, sell.py, list.py
│   │   ├── sales.py, csv.py, search.py, misc.py
│   ├── messages.py         # Free-text input handlers
│   ├── sell.py             # Sell flow
│   ├── accounts.py         # Add/delete/list
│   ├── search.py           # Search flow
│   ├── help.py             # Help system
│   └── ...
├── core/                   # Shared utilities
│   ├── filters.py          # Reusable filter system
│   ├── format.py           # Text formatting (_truncate, esc, etc.)
│   ├── keyboards.py        # Inline keyboards
│   ├── permissions.py      # Role checks
│   ├── state.py            # State manager (TTL)
│   └── help_content.py     # Help text
├── utils/                  # Utilities
│   ├── scheduler.py        # APScheduler jobs
│   ├── notifications.py    # Admin notifications
│   ├── csv_utils.py        # CSV import/export
│   └── parsers.py          # Input parsers
└── tests/                  # pytest test suite (116 tests)
    ├── conftest.py         # Test fixtures
    └── test_*.py           # 10 test modules
```

## License

Private use only.

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_database.py -v

# Run with deploy script
./deploy.sh test
```

116 tests covering database operations, sell flow, filters, formatting, state management, and more.
