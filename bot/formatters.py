from typing import List
from models.expense import Expense


def format_expense(expense: Expense) -> str:
    """Format a single expense as a readable line."""
    desc = expense.description or "N/A"
    cat = expense.category.name if expense.category else "N/A"
    return f"#{expense.id} • {desc} — **{expense.amount} {expense.currency}** ({cat})"


def format_expenses_table(expenses: List[Expense], title: str = "Expenses", budget: float = None) -> str:
    """Format a list of expenses as a readable table."""
    if not expenses:
        return f"📋 *{title}*\n\nNo expenses found."

    lines = [f"📋 *{title}*\n"]
    total = 0.0
    for exp in expenses:
        lines.append(format_expense(exp))
        total += exp.amount

    lines.append(f"\n💰 *Total: {total:.2f}*")
    lines.append(f"📊 *Count: {len(expenses)}*")

    if budget is not None:
        remaining = budget - total
        pct_used = (total / budget * 100) if budget > 0 else 0
        if remaining >= 0:
            lines.append(f"📋 Budget: {budget:.2f} ({pct_used:.0f}% used)")
            lines.append(f"✅ Balance: {remaining:.2f}")
        else:
            lines.append(f"📋 Budget: {budget:.2f} ({pct_used:.0f}% used)")
            lines.append(f"🚨 Over budget by: {abs(remaining):.2f}")

    lines.append(f"💡 Use /delete <id> to remove an expense")
    return "\n".join(lines)


def format_expense_detail(expense: Expense) -> str:
    """Format detailed info about a single expense."""
    cat = expense.category.name if expense.category else "N/A"
    desc = expense.description or "N/A"
    return (
        f"🧾 *Expense Details*\n\n"
        f"🆔 ID: {expense.id}\n"
        f"📝 Description: {desc}\n"
        f"💰 Amount: {expense.amount} {expense.currency}\n"
        f"📂 Category: {cat}\n"
        f"📅 Date: {expense.timestamp.strftime('%Y-%m-%d %H:%M')}"
    )


def format_category_summary(expenses: List[Expense], budget: float = None) -> str:
    """Format expenses grouped by category."""
    if not expenses:
        return "No expenses to summarize."

    categories = {}
    total = 0.0
    for exp in expenses:
        cat_name = exp.category.name if exp.category else "Other"
        if cat_name not in categories:
            categories[cat_name] = {"count": 0, "total": 0.0}
        categories[cat_name]["count"] += 1
        categories[cat_name]["total"] += exp.amount
        total += exp.amount

    lines = ["📊 *Spending by Category*\n"]
    for cat_name, data in sorted(categories.items(), key=lambda x: x[1]["total"], reverse=True):
        pct = (data["total"] / total * 100) if total > 0 else 0
        lines.append(f"• {cat_name}: {data['total']:.2f} ({pct:.0f}%) — {data['count']} items")

    lines.append(f"\n💰 *Grand Total: {total:.2f}*")

    if budget is not None:
        remaining = budget - total
        pct_used = (total / budget * 100) if budget > 0 else 0
        if remaining >= 0:
            lines.append(f"📋 Budget: {budget:.2f} ({pct_used:.0f}% used)")
            lines.append(f"✅ Remaining: {remaining:.2f}")
        else:
            lines.append(f"📋 Budget: {budget:.2f} ({pct_used:.0f}% used)")
            lines.append(f"🚨 Overspent by: {abs(remaining):.2f}")

    return "\n".join(lines)
