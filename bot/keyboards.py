from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def expense_actions_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for a single expense (delete/edit)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Edit", callback_data=f"edit:{expense_id}"),
                InlineKeyboardButton(text="🗑 Delete", callback_data=f"delete:{expense_id}"),
            ]
        ]
    )


def expenses_list_keyboard(expenses: list, page: int = 0, page_size: int = 5) -> InlineKeyboardMarkup:
    """Paginated inline keyboard for a list of expenses."""
    total_pages = (len(expenses) + page_size - 1) // page_size if expenses else 1
    start = page * page_size
    end = start + page_size
    page_expenses = expenses[start:end]

    buttons = []
    for exp in page_expenses:
        label = f"{exp.description or 'Expense'} — {exp.amount} {exp.currency}"
        buttons.append([
            InlineKeyboardButton(text=label, callback_data=f"detail:{exp.id}")
        ])

    # Navigation buttons
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"page:{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"page:{page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def category_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Inline keyboard with category buttons."""
    buttons = []
    for cat in categories:
        buttons.append([
            InlineKeyboardButton(text=cat.name, callback_data=f"cat:{cat.id}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def edit_expense_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    """Keyboard for choosing what field to edit."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Amount", callback_data=f"edit_amount:{expense_id}")],
            [InlineKeyboardButton(text="📂 Category", callback_data=f"edit_category:{expense_id}")],
            [InlineKeyboardButton(text="📝 Description", callback_data=f"edit_desc:{expense_id}")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")],
        ]
    )


def confirm_delete_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    """Keyboard to confirm deletion."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Yes, delete", callback_data=f"confirm_delete:{expense_id}"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="cancel"),
            ]
        ]
    )
