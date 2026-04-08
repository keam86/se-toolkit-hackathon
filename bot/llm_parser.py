import json
import os
import logging
import asyncio
from typing import Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen-plus")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))  # Timeout in seconds

client = AsyncOpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
)

EXPENSE_PARSER_SYSTEM_PROMPT = """\
You are an expense parser. Given a natural language message about a purchase, extract the following fields and return ONLY valid JSON:

- amount (number, required)
- currency (ISO 4217 3-letter code, default "RUB" if not specified)
- category (one of: Food, Transport, Entertainment, Shopping, Utilities, Health, Education, Other)
- description (short text describing the item/service, required)

Rules:
- If the message doesn't contain expense information, return: {"error": "not_an_expense"}
- Infer currency from context: "rub"/"руб" → "RUB", "$"/"usd"/"доллар" → "USD", "€"/"eur"/"евро" → "EUR"
- Choose the most appropriate category based on context
- Keep description concise (1-5 words)

Example input: "coffee 250 rub"
Example output: {"amount": 250, "currency": "RUB", "category": "Food", "description": "coffee"}
"""

ADVICE_SYSTEM_PROMPT = """\
You are a personal financial advisor. Analyze the provided expense data and give concise, actionable financial recommendations based on the user's monthly budget.

Rules:
- Compare total spending against the monthly budget and show the remaining amount or overspend
- Calculate and show the percentage of budget used per category
- Be specific and practical — reference actual numbers from the data
- Suggest areas to cut back or optimize, especially categories exceeding their fair share
- If spending is under budget, acknowledge good habits and suggest saving the remainder
- If spending is over budget, provide clear steps to get back on track
- Keep response under 300 words
- Use clear formatting with bullet points and emojis
- Respond in the same language the user typically uses (Russian if expenses are in RUB, English otherwise)
"""


async def parse_expense(message: str) -> Optional[dict]:
    """Parse a natural language expense message into structured data."""
    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": EXPENSE_PARSER_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        result = json.loads(response.choices[0].message.content)
        if "error" in result:
            logger.warning(f"LLM returned error: {result['error']}")
            return None
        return result
    except Exception as e:
        logger.error(f"LLM parsing error: {e}")
        return None


async def get_financial_advice(expenses_summary: str) -> str:
    """Get financial advice from LLM based on expense data."""
    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": ADVICE_SYSTEM_PROMPT},
                {"role": "user", "content": expenses_summary},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM advice error: {e}")
        return "Sorry, I couldn't generate financial advice at this time. Please try again later."
