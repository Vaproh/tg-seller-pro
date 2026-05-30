# Credential Vault Bot

Private Telegram bot built with python-telegram-bot.

## Setup

Create a `.env` file:

```env
BOT_TOKEN=your_token_here
ALLOWED_USER_ID=123456789
BOT_NAME=Credential Vault
SERVICE_NAME=Service Name
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a `.env` file from the example:

```bash
copy .env.example .env
```

Run:

```bash
python bot.py
```

## Commands

- /start
- /add
- /bulkadd
- /getaccounts
- /getid
- /search
- /delete
- /categories

## Search filters

Use `category:<name>`, `status:used`, `status:unused`, `sort:newest`, `sort:oldest`, `username:<term>`, `password:<term>`, or `id:<number>`.
- /addcategory
- /deletecategory
- /logs
- /unused
- /markused
- /markunused
- /stats
- /export
