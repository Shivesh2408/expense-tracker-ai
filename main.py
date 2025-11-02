import argparse
from datetime import datetime, timedelta, date
from typing import Optional

from db import ExpenseDB
from categorizer import CategoryRules
from predictor import Predictor
from bot import ChatBot


def parse_date(value: str) -> str:
    try:
        value_lower = value.lower()
        if value_lower == "today":
            return date.today().isoformat()
        if value_lower == "yesterday":
            return (date.today() - timedelta(days=1)).isoformat()
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except Exception as error:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}': {error}")


def add_command(args: argparse.Namespace, db: ExpenseDB, rules: CategoryRules) -> None:
    category: Optional[str] = args.category
    if not category:
        category = rules.categorize(args.description)
    expense_id = db.add_expense(
        date_iso=args.date,
        amount=args.amount,
        description=args.description,
        category=category,
    )
    print(f"Added expense #{expense_id} | {args.date} | {args.amount:.2f} | {category} | {args.description}")


def list_command(args: argparse.Namespace, db: ExpenseDB) -> None:
    expenses = db.list_expenses(start_date=args.start, end_date=args.end, category=args.category, limit=args.limit)
    if not expenses:
        print("No expenses matched.")
        return
    print("id  | date       | amount   | category     | description")
    print("-" * 70)
    for exp in expenses:
        print(f"{exp['id']:<3} | {exp['date']} | {exp['amount']:<8.2f} | {exp['category']:<12} | {exp['description']}")


def summary_command(args: argparse.Namespace, db: ExpenseDB) -> None:
    period = args.period
    summary = db.get_summary(period=period)
    print(f"Summary ({period})")
    print("Total: {:.2f}".format(summary["total"]))
    print("By category:")
    for category, amount in sorted(summary["by_category"].items(), key=lambda x: -x[1]):
        print(f"- {category}: {amount:.2f}")


def predict_command(args: argparse.Namespace, db: ExpenseDB) -> None:
    predictor = Predictor(db)
    months_count = args.months
    forecast = predictor.predict_next_month(months_back=months_count)
    print("Prediction for next month (total): {:.2f}".format(forecast["total_next_month"]))
    print("Per category (next month):")
    for category, amount in sorted(forecast["per_category_next_month"].items(), key=lambda x: -x[1]):
        print(f"- {category}: {amount:.2f}")


def export_command(args: argparse.Namespace, db: ExpenseDB) -> None:
    export_path = db.export_csv(path=args.path)
    print(f"Exported to {export_path}")


def categories_command(args: argparse.Namespace, rules: CategoryRules) -> None:
    if args.action == "show":
        rules_dict = rules.get_rules()
        print("Category rules (keyword -> category):")
        for category, keywords in rules_dict.items():
            print(f"- {category}: {', '.join(keywords)}")
    elif args.action == "add":
        rules.add_keyword(category=args.category, keyword=args.keyword)
        rules.save()
        print(f"Added keyword '{args.keyword}' to category '{args.category}'.")
    elif args.action == "remove":
        rules.remove_keyword(category=args.category, keyword=args.keyword)
        rules.save()
        print(f"Removed keyword '{args.keyword}' from category '{args.category}'.")


def chat_command(_: argparse.Namespace, db: ExpenseDB, rules: CategoryRules) -> None:
    bot = ChatBot(db=db, rules=rules)
    print("Type 'exit' to quit chat.")
    while True:
        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_text or user_text.lower() in {"exit", "quit"}:
            break
        response = bot.respond(user_text)
        print(f"Bot: {response}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Expense Tracker and Predictor (Simple Python CLI)")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add a new expense")
    add_p.add_argument("amount", type=float, help="Amount spent")
    add_p.add_argument("description", type=str, help="Short description")
    add_p.add_argument("--date", type=parse_date, default=date.today().isoformat(), help="YYYY-MM-DD or 'today'/'yesterday'")
    add_p.add_argument("--category", type=str, default=None, help="Optional category; otherwise auto-categorized")

    list_p = sub.add_parser("list", help="List expenses")
    list_p.add_argument("--start", type=parse_date, default=None)
    list_p.add_argument("--end", type=parse_date, default=None)
    list_p.add_argument("--category", type=str, default=None)
    list_p.add_argument("--limit", type=int, default=50)

    summary_p = sub.add_parser("summary", help="Show totals and by-category for a period")
    summary_p.add_argument("period", choices=["day", "week", "month", "all"], help="Aggregate period")

    predict_p = sub.add_parser("predict", help="Predict next month totals")
    predict_p.add_argument("--months", type=int, default=6, help="Number of past months to learn from")

    export_p = sub.add_parser("export", help="Export all expenses to CSV")
    export_p.add_argument("path", type=str, help="Output CSV file path")

    cats_p = sub.add_parser("categories", help="Manage categorization keywords")
    cats_p.add_argument("action", choices=["show", "add", "remove"]) 
    cats_p.add_argument("--category", type=str, help="Category name (for add/remove)")
    cats_p.add_argument("--keyword", type=str, help="Keyword to add/remove")

    sub.add_parser("chat", help="Chat with the expense bot")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    db = ExpenseDB(db_path="expenses.db")
    rules = CategoryRules(path="categories.json")

    if args.command == "add":
        add_command(args, db, rules)
    elif args.command == "list":
        list_command(args, db)
    elif args.command == "summary":
        summary_command(args, db)
    elif args.command == "predict":
        predict_command(args, db)
    elif args.command == "export":
        export_command(args, db)
    elif args.command == "categories":
        categories_command(args, rules)
    elif args.command == "chat":
        chat_command(args, db, rules)


if __name__ == "__main__":
    main()



