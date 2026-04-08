# Expense Tracker Bot

A Telegram bot that lets you track expenses by sending natural language messages like "coffee 250 rub". An LLM (Qwen) parses the message, stores it in a database, and lets you view, edit, and analyze your spending — all inside Telegram.

## End Users

People who want a simple, frictionless way to track daily expenses without navigating complex forms or dashboards.

## Problem Solved

Traditional expense trackers require manual form filling, category selection, and date picking. This bot removes that friction — just type what you spent money on in plain language and the LLM handles the rest.

## Features

### V1 (Core)
- ✅ Add expense via natural language ("coffee 250 rub")
- ✅ Remove/edit existing expenses with inline buttons
- ✅ `/all` — View full expense table in chat
- ✅ `/category` — Filter by category (with inline picker)

### V2 (Advanced)
- ✅ `/advice` — LLM-powered financial recommendations on all spending
- ✅ `/advice <category>` — Category-specific financial advice
- ✅ `/addcategory <name>` — Add custom user-defined categories
- ✅ `/sort cat1 cat2 ...` — Filter by multiple categories at once

## Tech Stack

| Component | Technology |
|-----------|------------|
| Bot Framework | aiogram 3.x (Python) |
| LLM | Qwen via DashScope API |
| Database | SQLite (async via aiosqlite) |
| ORM | SQLAlchemy 2.0 |
| Deployment | Docker + Docker Compose |

## Usage

1. Start the bot with `/start`
2. Send any expense message: `lunch 450 rub`, `taxi 200 usd`, `netflix subscription 15 eur`
3. Use commands to manage:
   - `/all` — See all expenses
   - `/category Food` — Filter by category
   - `/category` — Pick from inline keyboard
   - `/advice` — Get financial tips
   - `/sort Food Transport` — Multi-category view
   - `/addcategory Subscriptions` — Add custom category
4. Use inline buttons on any expense to edit or delete it

## Deployment

### Prerequisites

- Python 3.11+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- DashScope API key (for Qwen LLM)

### Local Run

```bash
# 1. Clone and create env
cp .env.example .env
# Edit .env with your tokens

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the bot
python -m bot.main
```

### Docker

```bash
# 1. Create .env file
cp .env.example .env
# Edit .env with your tokens

# 2. Build and run
docker compose up --build
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `DASHSCOPE_API_KEY` | API key for Qwen/DashScope |
| `LLM_BASE_URL` | LLM API endpoint (default: DashScope) |
| `LLM_MODEL` | Model name (default: qwen-plus) |
| `DATABASE_URL` | Async DB URL (default: sqlite+aiosqlite:///./data/expenses.db) |

## Project Structure

```
├── bot/
│   ├── main.py              # Entry point
│   ├── handlers.py          # All command & callback handlers
│   ├── llm_parser.py        # Qwen LLM integration (expense parsing + advice)
│   ├── keyboards.py         # Inline keyboard builders
│   └── formatters.py        # Expense table/summary formatting
├── models/
│   └── expense.py           # SQLAlchemy models (Expense, Category)
├── database/
│   └── connection.py        # Async DB setup & seeding
├── data/                    # SQLite database (git-ignored)
├── migrations/              # Alembic migrations (future)
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
# Mrrrplaning-bot
