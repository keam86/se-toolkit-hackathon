import logging
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from dotenv import load_dotenv

from database.connection import init_db, async_session
from models.expense import Expense, Category, UserSettings
from bot.llm_parser import parse_expense, get_financial_advice
from bot.keyboards import (
    expense_actions_keyboard,
    expenses_list_keyboard,
    category_keyboard,
    edit_expense_keyboard,
    confirm_delete_keyboard,
)
from bot.formatters import (
    format_expenses_table,
    format_expense_detail,
    format_category_summary,
)

load_dotenv()

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DEFAULT_CATEGORIES = ["Food", "Transport", "Entertainment", "Shopping",
                      "Utilities", "Health", "Education", "Other"]


# ── FSM States ──────────────────────────────────────────────
class EditExpenseState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_description = State()
    waiting_for_category = State()


class AddCategoryState(StatesGroup):
    waiting_for_name = State()


class BudgetState(StatesGroup):
    waiting_for_budget = State()


# ── Helpers ─────────────────────────────────────────────────
async def get_or_create_category(name: str, user_id: int = None) -> Category:
    """Get or create a category by name."""
    async with async_session() as session:
        result = await session.execute(select(Category).where(Category.name.ilike(name)))
        cat = result.scalar_one_or_none()
        if cat:
            return cat
        cat = Category(name=name, user_id=user_id)
        session.add(cat)
        await session.commit()
        await session.refresh(cat)
        return cat


async def get_categories(user_id: int = None) -> list:
    """Get all categories (system defaults + user custom)."""
    async with async_session() as session:
        result = await session.execute(
            select(Category).where(
                (Category.user_id.is_(None)) | (Category.user_id == user_id)
            ).order_by(Category.name)
        )
        return result.scalars().all()


async def get_user_budget(user_id: int) -> float | None:
    """Get user's monthly budget, or None if not set."""
    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()
        if settings:
            return settings.monthly_budget
        return None


async def set_user_budget(user_id: int, budget: float):
    """Set or update user's monthly budget."""
    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()
        if settings:
            settings.monthly_budget = budget
        else:
            settings = UserSettings(user_id=user_id, monthly_budget=budget)
            session.add(settings)
        await session.commit()


# ── Command: /start ─────────────────────────────────────────
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Hi! I'm your expense tracker bot.\n\n"
        "Just send me a message like *\"coffee 250 rub\"* and I'll log it.\n\n"
        "*Commands:*\n"
        "/all — View all expenses (with IDs)\n"
        "/delete <id> — Remove expense by ID\n"
        "/category — Pick a category to filter\n"
        "/budget — Set your monthly budget\n"
        "/advice — Get financial tips\n"
        "/sort — Filter by multiple categories\n"
        "/addcategory — Add a custom category",
        parse_mode="Markdown",
    )


# ── Natural Language Expense Handler ────────────────────────
async def handle_expense_message(message: types.Message):
    parsed = await parse_expense(message.text)
    if not parsed:
        await message.answer(
            "❌ I couldn't understand that as an expense. "
            "Try something like: *\"coffee 250 rub\"*",
            parse_mode="Markdown",
        )
        return

    amount = parsed.get("amount")
    currency = parsed.get("currency", "RUB")
    category_name = parsed.get("category", "Other")
    description = parsed.get("description", "")

    # Ensure category exists
    cat = await get_or_create_category(category_name)

    # Save to DB
    expense = Expense(
        user_id=message.from_user.id,
        amount=amount,
        currency=currency,
        category_id=cat.id,
        description=description,
    )
    async with async_session() as session:
        session.add(expense)
        await session.commit()
        await session.refresh(expense)

    # Calculate total spending and balance
    async with async_session() as session:
        result = await session.execute(
            select(func.sum(Expense.amount)).where(Expense.user_id == message.from_user.id)
        )
        total_spent = result.scalar() or 0.0

    budget = await get_user_budget(message.from_user.id)
    balance = (budget - total_spent) if budget is not None else None
    over_budget = budget is not None and total_spent > budget

    response = f"✅ Expense logged!\n\n"
    response += f"📝 {description}\n"
    response += f"💰 {amount} {currency}\n"
    response += f"📂 {category_name}\n"

    if balance is not None:
        if balance >= 0:
            response += f"\n💵 Balance: {balance:,.2f}"
        else:
            response += f"\n🚨 Balance: {balance:,.2f} (over budget)"

    if over_budget:
        response = f"⚠️ !! This expense goes beyond the budget !! ⚠️\n\n" + response

    await message.answer(
        response,
        reply_markup=expense_actions_keyboard(expense.id),
    )


# ── Command: /delete ────────────────────────────────────────
async def cmd_delete(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "🗑 Use /delete <id> to remove an expense.\n"
            "Example: /delete 5\n\n"
            "Use /all to see expense IDs."
        )
        return

    try:
        expense_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID must be a number. Example: /delete 5")
        return

    async with async_session() as session:
        result = await session.execute(
            select(Expense).where(
                Expense.id == expense_id,
                Expense.user_id == message.from_user.id
            )
        )
        expense = result.scalar_one_or_none()
        if expense:
            desc = expense.description or "expense"
            await session.delete(expense)
            await session.commit()
            await message.answer(f"🗑 Deleted: {desc} — {expense.amount} {expense.currency}")
        else:
            await message.answer(f"❌ Expense #{expense_id} not found.")


# ── Command: /all ───────────────────────────────────────────
async def cmd_all(message: types.Message):
    budget = await get_user_budget(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(Expense)
            .where(Expense.user_id == message.from_user.id)
            .order_by(Expense.timestamp.desc())
        )
        expenses = result.scalars().all()

    text = format_expenses_table(expenses, "All Expenses", budget=budget)
    await message.answer(text, parse_mode="Markdown")


# ── Command: /category ──────────────────────────────────────
async def cmd_category(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        # Direct category filter: /category Food
        cat_name = args[1].strip()
        async with async_session() as session:
            result = await session.execute(select(Category).where(Category.name.ilike(cat_name)))
            cat = result.scalar_one_or_none()
            if not cat:
                await message.answer(f"❌ Category \"{cat_name}\" not found.")
                return
            result = await session.execute(
                select(Expense)
                .where(Expense.user_id == message.from_user.id, Expense.category_id == cat.id)
                .order_by(Expense.timestamp.desc())
            )
            expenses = result.scalars().all()
        text = format_expenses_table(expenses, f"Category: {cat.name}")
        await message.answer(text, parse_mode="Markdown")
    else:
        # Show category picker
        cats = await get_categories(message.from_user.id)
        await message.answer("📂 Choose a category:", reply_markup=category_keyboard(cats))


# ── Callback: Category selected ─────────────────────────────
async def cb_category(callback: types.CallbackQuery):
    cat_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        result = await session.execute(
            select(Expense)
            .where(Expense.user_id == callback.from_user.id, Expense.category_id == cat_id)
            .order_by(Expense.timestamp.desc())
        )
        expenses = result.scalars().all()
        result = await session.execute(select(Category).where(Category.id == cat_id))
        cat = result.scalar_one_or_none()

    cat_name = cat.name if cat else "Unknown"
    text = format_expenses_table(expenses, f"Category: {cat_name}")
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


# ── Command: /advice ────────────────────────────────────────
async def cmd_advice(message: types.Message):
    # Check if budget is set
    budget = await get_user_budget(message.from_user.id)
    if budget is None:
        await message.answer(
            "⚠️ Please set your monthly budget first using:\n"
            "/budget <amount>\n\n"
            "Example: /budget 50000"
        )
        return

    args = message.text.split(maxsplit=1)
    async with async_session() as session:
        if len(args) > 1:
            # Category-specific advice
            cat_name = args[1].strip()
            result = await session.execute(select(Category).where(Category.name.ilike(cat_name)))
            cat = result.scalar_one_or_none()
            if not cat:
                await message.answer(f"❌ Category \"{cat_name}\" not found.")
                return
            result = await session.execute(
                select(Expense)
                .where(Expense.user_id == message.from_user.id, Expense.category_id == cat.id)
            )
            expenses = result.scalars().all()
            summary_title = f"Spending in category: {cat.name}"
        else:
            # All expenses advice
            result = await session.execute(
                select(Expense).where(Expense.user_id == message.from_user.id)
            )
            expenses = result.scalars().all()
            summary_title = "All spending"

    if not expenses:
        await message.answer("📭 No expenses to analyze yet. Start logging some expenses first!")
        return

    summary = format_category_summary(expenses, budget=budget)
    prompt = f"{summary_title}:\n\n{summary}\n\nPlease give me financial advice."

    await message.answer("🤔 Analyzing your spending...")
    advice = await get_financial_advice(prompt)
    await message.answer(f"💡 *Financial Advice*\n\n{advice}", parse_mode="Markdown")


# ── Command: /addcategory ───────────────────────────────────
async def cmd_addcategory(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        name = args[1].strip()
        cat = await get_or_create_category(name, user_id=message.from_user.id)
        await message.answer(f"✅ Category \"{cat.name}\" added!")
    else:
        await message.answer(
            "📝 Send the category name after the command.\n"
            "Example: /addcategory Subscriptions"
        )


# ── Command: /budget ────────────────────────────────────────
async def cmd_budget(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        try:
            budget = float(args[1].replace(",", "."))
            if budget <= 0:
                await message.answer("❌ Budget must be a positive number.")
                return
            await set_user_budget(message.from_user.id, budget)
            await message.answer(f"✅ Monthly budget set to *{budget:,.2f}*", parse_mode="Markdown")
        except ValueError:
            await message.answer("❌ Please enter a valid number. Example: /budget 50000")
    else:
        current = await get_user_budget(message.from_user.id)
        current_str = f"Current: {current:,.2f}\n\n" if current is not None else ""
        await message.answer(
            f"💰 *Monthly Budget*\n\n"
            f"{current_str}"
            f"Send your monthly budget like:\n"
            f"/budget 50000",
            parse_mode="Markdown",
        )


# ── Command: /sort ──────────────────────────────────────────
async def cmd_sort(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "📊 Use /sort with category names.\n"
            "Example: /sort Food Transport Entertainment"
        )
        return

    cat_names = [c.strip() for c in args[1].split()]
    async with async_session() as session:
        result = await session.execute(
            select(Category).where(Category.name.in_(cat_names))
        )
        cats = result.scalars().all()

    if not cats:
        await message.answer("❌ None of those categories found.")
        return

    cat_ids = [c.id for c in cats]
    result = await session.execute(
        select(Expense)
        .where(Expense.user_id == message.from_user.id, Expense.category_id.in_(cat_ids))
        .order_by(Expense.timestamp.desc())
    )
    expenses = result.scalars().all()

    cat_names_found = ", ".join(c.name for c in cats)
    text = format_expenses_table(expenses, f"Categories: {cat_names_found}")
    await message.answer(text, parse_mode="Markdown")


# ── Callback: Delete expense ────────────────────────────────
async def cb_delete(callback: types.CallbackQuery):
    expense_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup(
        reply_markup=confirm_delete_keyboard(expense_id)
    )
    await callback.answer()


async def cb_confirm_delete(callback: types.CallbackQuery):
    expense_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        result = await session.execute(select(Expense).where(Expense.id == expense_id))
        expense = result.scalar_one_or_none()
        if expense:
            await session.delete(expense)
            await session.commit()
            await callback.message.edit_text("🗑 Expense deleted.")
        else:
            await callback.message.edit_text("❌ Expense not found.")
    await callback.answer()


# ── Callback: Edit expense ──────────────────────────────────
async def cb_edit(callback: types.CallbackQuery):
    expense_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup(
        reply_markup=edit_expense_keyboard(expense_id)
    )
    await callback.answer()


# ── Callback: Edit amount ───────────────────────────────────
async def cb_edit_amount(callback: types.CallbackQuery, state: FSMContext):
    expense_id = int(callback.data.split(":")[1])
    await state.update_data(expense_id=expense_id)
    await state.set_state(EditExpenseState.waiting_for_amount)
    await callback.message.answer("💰 Send the new amount:")
    await callback.answer()


# ── Callback: Edit description ──────────────────────────────
async def cb_edit_desc(callback: types.CallbackQuery, state: FSMContext):
    expense_id = int(callback.data.split(":")[1])
    await state.update_data(expense_id=expense_id)
    await state.set_state(EditExpenseState.waiting_for_description)
    await callback.message.answer("📝 Send the new description:")
    await callback.answer()


# ── Callback: Edit category ─────────────────────────────────
async def cb_edit_category(callback: types.CallbackQuery, state: FSMContext):
    expense_id = int(callback.data.split(":")[1])
    await state.update_data(expense_id=expense_id)
    cats = await get_categories(callback.from_user.id)
    await state.set_state(EditExpenseState.waiting_for_category)
    await callback.message.answer("📂 Choose a new category:", reply_markup=category_keyboard(cats))
    await callback.answer()


# ── FSM Handler: New amount ─────────────────────────────────
async def handle_new_amount(message: types.Message, state: FSMContext):
    try:
        new_amount = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("❌ Please send a valid number.")
        return

    data = await state.get_data()
    expense_id = data["expense_id"]

    async with async_session() as session:
        result = await session.execute(select(Expense).where(Expense.id == expense_id))
        expense = result.scalar_one_or_none()
        if expense:
            expense.amount = new_amount
            await session.commit()
            await message.answer(f"✅ Amount updated to {new_amount} {expense.currency}")
        else:
            await message.answer("❌ Expense not found.")

    await state.clear()


# ── FSM Handler: New description ────────────────────────────
async def handle_new_desc(message: types.Message, state: FSMContext):
    data = await state.get_data()
    expense_id = data["expense_id"]

    async with async_session() as session:
        result = await session.execute(select(Expense).where(Expense.id == expense_id))
        expense = result.scalar_one_or_none()
        if expense:
            expense.description = message.text
            await session.commit()
            await message.answer(f"✅ Description updated to \"{message.text}\"")
        else:
            await message.answer("❌ Expense not found.")

    await state.clear()


# ── FSM Handler: New category (from callback or message) ────
async def handle_new_category(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    expense_id = data.get("expense_id")

    if not expense_id:
        # Direct category filter from /category command
        return await cb_category(callback)

    async with async_session() as session:
        result = await session.execute(select(Expense).where(Expense.id == expense_id))
        expense = result.scalar_one_or_none()
        if expense:
            expense.category_id = cat_id
            await session.commit()
            result = await session.execute(select(Category).where(Category.id == cat_id))
            cat = result.scalar_one_or_none()
            await callback.message.answer(f"✅ Category updated to \"{cat.name}\"")
        else:
            await callback.message.answer("❌ Expense not found.")

    await state.clear()
    await callback.answer()


# ── Callback: Cancel ────────────────────────────────────────
async def cb_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Cancelled.")
    await callback.answer()


# ── Callback: Expense detail ────────────────────────────────
async def cb_detail(callback: types.CallbackQuery):
    expense_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        result = await session.execute(select(Expense).where(Expense.id == expense_id))
        expense = result.scalar_one_or_none()
    if expense:
        text = format_expense_detail(expense)
        await callback.message.edit_text(text, parse_mode="Markdown",
                                         reply_markup=expense_actions_keyboard(expense_id))
    else:
        await callback.message.edit_text("❌ Expense not found.")
    await callback.answer()


# ── Callback: Pagination ────────────────────────────────────
async def cb_page(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    # Re-fetch expenses for pagination (simplified — stores user_id in callback)
    await callback.answer("Pagination coming soon!", show_alert=False)


# ── Bot Setup ───────────────────────────────────────────────
def create_dp() -> Dispatcher:
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Commands
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_all, Command("all"))
    dp.message.register(cmd_delete, Command("delete"))
    dp.message.register(cmd_category, Command("category"))
    dp.message.register(cmd_budget, Command("budget"))
    dp.message.register(cmd_advice, Command("advice"))
    dp.message.register(cmd_addcategory, Command("addcategory"))
    dp.message.register(cmd_sort, Command("sort"))

    # FSM handlers — MUST be before catch-all to intercept editing input
    dp.message.register(handle_new_amount, EditExpenseState.waiting_for_amount)
    dp.message.register(handle_new_desc, EditExpenseState.waiting_for_description)
    dp.callback_query.register(handle_new_category,
                               F.data.startswith("cat:"),
                               EditExpenseState.waiting_for_category)

    # Natural language expense (fallback — no command, no FSM state)
    dp.message.register(handle_expense_message, F.text)

    # Callbacks
    dp.callback_query.register(cb_category, F.data.startswith("cat:"))
    dp.callback_query.register(cb_delete, F.data.startswith("delete:"))
    dp.callback_query.register(cb_confirm_delete, F.data.startswith("confirm_delete:"))
    dp.callback_query.register(cb_edit, F.data.startswith("edit:"))
    dp.callback_query.register(cb_edit_amount, F.data.startswith("edit_amount:"))
    dp.callback_query.register(cb_edit_desc, F.data.startswith("edit_desc:"))
    dp.callback_query.register(cb_edit_category, F.data.startswith("edit_category:"))
    dp.callback_query.register(cb_detail, F.data.startswith("detail:"))
    dp.callback_query.register(cb_page, F.data.startswith("page:"))
    dp.callback_query.register(cb_cancel, F.data == "cancel")

    return dp


async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = create_dp()
    logger.info("Starting bot...")
    await dp.start_polling(bot)
