# Expense Tracker Bot — Project Specification

## Overview

A personal expense tracker that lets users send Telegram messages in natural language (e.g., "coffee 250 rub") to a bot powered by an LLM. The LLM parses the message, extracts expense details, stores them in a database, and displays spending data directly in the Telegram chat. **The entire interaction happens inside Telegram — no web pages or external dashboards.**

## End User

People who want a simple, frictionless way to track daily expenses without navigating complex UIs or forms.

## Problem Solved

**Key Feature:** Natural language to structured data conversion.

Traditional expense trackers require manual form filling, category selection, and date picking. This project removes that friction by allowing users to simply type what they spent money on in plain language — the LLM handles the parsing, categorization, and storage automatically.

## Feature Roadmap

### V1 — Core Functionality

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Add expense via natural language** | Send a message like "coffee 250 rub" → LLM parses → stored in DB → confirmation sent |
| 2 | **Remove / Refactor existing expense** | Command to list recent expenses with inline buttons to delete or edit (amount, category, description) |
| 3 | **View full expense table** | `/all` command — displays the complete expense history as a formatted table in chat |
| 4 | **View expenses by category** | `/category Food` — filters and displays only expenses matching a specific category |

### V2 — Advanced Features

| # | Feature | Description |
|---|---------|-------------|
| 5 | **LLM financial recommendations (all expenses)** | `/advice` — LLM analyzes all spending and provides personalized saving/budget tips |
| 6 | **LLM financial recommendations (per category)** | `/advice Food` — LLM analyzes spending in a single category and gives targeted advice |
| 7 | **Add new expense category** | `/addcategory Transport` — user-defined categories beyond the default set |
| 8 | **Sort by multiple categories** | `/sort Food Transport` — view expenses filtered by two or more categories at once |

## Core Features

1. **Telegram-Only Interface** — 100% inside Telegram, no web UI whatsoever
2. **LLM-Powered Parsing** — Extracts: amount, currency, category, description, date
3. **Database Storage** — Persistent record of all expenses
4. **In-Chat Expense Display** — Formatted tables, totals, and breakdowns sent as Telegram messages
5. **Multi-Currency Support** — Rubles, USD, EUR, etc.
6. **Smart Categorization** — LLM auto-assigns categories based on context
7. **Inline Keyboards** — Interactive buttons for filtering, editing, and deleting expenses

## Proposed Tech Stack

### Backend

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Language** | Python 3.11+ | Rich ecosystem for bots, LLMs, and data processing |
| **Telegram Bot Framework** | `aiogram` 3.x | Modern async Telegram bot library with inline keyboard support |
| **LLM Integration** | Qwen Code API (DashScope) | Primary LLM for natural language parsing |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Simple start, scalable later |
| **ORM** | SQLAlchemy 2.0 or SQLModel | Type-safe, async support |
| **Table Formatting** | `tabulate` or manual HTML/Markdown | Formatted expense tables in chat |

*(No web framework needed — everything happens inside Telegram.)*

### Infrastructure

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Containerization** | Docker + Docker Compose | Reproducible environment |
| **Environment Config** | `python-dotenv` | Manage secrets (bot token, API keys) |
| **Migrations** | Alembic | Database schema versioning |

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Telegram   │────▶│  Telegram    │────▶│    LLM      │
│    User      │     │   Bot        │     │  (Parser)   │
└─────────────┘     │  (aiogram)   │     └──────┬──────┘
      ◀─────────────└──────────────┘            │
           Formatted                            ▼
           Messages &                   ┌─────────────┐
           Inline Keyboards            │  Structured │
                                       │  JSON Data  │
                                       └──────┬──────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │  Database   │
                                       │ (SQLAlchemy)│
                                       └─────────────┘
```

## Data Model

### Expense Table

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID / Integer | Primary key |
| `user_id` | Integer | Telegram user ID |
| `amount` | Decimal | Expense amount |
| `currency` | String (3 chars) | e.g., "RUB", "USD", "EUR" |
| `category` | String | e.g., "Food", "Transport", "Entertainment" |
| `description` | String | Item/service description |
| `timestamp` | DateTime | When the expense occurred |
| `created_at` | DateTime | Record creation time |

## LLM Prompt Strategy

The LLM receives natural language and returns structured JSON:

**User Input:** `"coffee 250 rub"`

**System Prompt:**
```
You are an expense parser. Given a natural language message, extract:
- amount (number)
- currency (ISO 4217 code)
- category (one of: Food, Transport, Entertainment, Shopping, Utilities, Health, Other)
- description (short text)

Return ONLY valid JSON: {"amount": 250, "currency": "RUB", "category": "Food", "description": "coffee"}
```

## Project Structure

```
se-toolkit-hackathon/
├── bot/
│   ├── __init__.py
│   ├── main.py              # aiogram bot entry & dispatcher
│   ├── handlers.py          # Message & command handlers
│   ├── llm_parser.py        # LLM integration & JSON extraction
│   ├── keyboards.py         # Inline keyboards for navigation
│   └── formatters.py        # Expense table/summary formatting
├── models/
│   ├── __init__.py
│   └── expense.py           # SQLAlchemy models
├── database/
│   ├── __init__.py
│   └── connection.py        # DB setup & session management
├── migrations/              # Alembic migrations
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Environment Variables

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
DASHSCOPE_API_KEY=your_qwen_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
DATABASE_URL=sqlite+aiosqlite:///./expenses.db
```

## Next Steps

1. Set up project scaffolding (aiogram + SQLAlchemy)
2. Implement database models and migrations
3. Build LLM parser with structured JSON output (Qwen/DashScope)
4. Create Telegram bot handlers for V1 features (add, remove, view all, view by category)
5. Implement inline keyboards for expense management
6. Add V2 features (LLM advice, custom categories, multi-category sorting)
7. Deploy with Docker Compose
