import re
from datetime import date, timedelta
from typing import Optional

from db import ExpenseDB
from categorizer import CategoryRules
from predictor import Predictor


class ChatBot:
    def __init__(self, db: ExpenseDB, rules: CategoryRules) -> None:
        self.db = db
        self.rules = rules
        self.predictor = Predictor(db)

    def _parse_add_intent(self, text: str) -> Optional[str]:
        amount_match = re.search(r"(add|spent)\s+(\d+(?:\.\d{1,2})?)", text, re.IGNORECASE)
        if not amount_match:
            return None
        amount = float(amount_match.group(2))
        desc_match = re.search(r"(?:on|for)\s+([a-zA-Z0-9 ,.-]+)", text, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else "misc"
        date_iso = date.today().isoformat()
        if "yesterday" in text.lower():
            date_iso = (date.today() - timedelta(days=1)).isoformat()
        category = self.rules.categorize(description)
        expense_id = self.db.add_expense(date_iso=date_iso, amount=amount, description=description, category=category)
        return f"Added expense #{expense_id}: {amount:.2f} {category} - {description} on {date_iso}"

    def _parse_summary_intent(self, text: str) -> Optional[str]:
        lowered = text.lower()
        if "today" in lowered:
            period = "day"
        elif "week" in lowered:
            period = "week"
        elif "month" in lowered:
            period = "month"
        elif "all" in lowered or "total" in lowered:
            period = "all"
        else:
            return None
        summary = self.db.get_summary(period)
        parts = [f"Total {period}: {summary['total']:.2f}"]
        if summary["by_category"]:
            parts.append(", ".join(f"{k} {v:.2f}" for k, v in summary["by_category"].items()))
        return "; ".join(parts)

    def _parse_predict_intent(self, text: str) -> Optional[str]:
        if "predict" not in text.lower():
            return None
        forecast = self.predictor.predict_next_month()
        out = [f"Next month total: {forecast['total_next_month']:.2f}"]
        if forecast["per_category_next_month"]:
            out.append(
                "Per category: " + ", ".join(f"{k} {v:.2f}" for k, v in forecast["per_category_next_month"].items())
            )
        return "; ".join(out)

    def _parse_biggest_category_intent(self, text: str) -> Optional[str]:
        if not re.search(r"(biggest|largest|most)\s+(spend|expense|category)", text, re.IGNORECASE):
            return None
        summary = self.db.get_summary("month")
        if not summary["by_category"]:
            return "No data yet."
        cat, amt = max(summary["by_category"].items(), key=lambda kv: kv[1])
        return f"Biggest category this month: {cat} ({amt:.2f})"

    def respond(self, text: str) -> str:
        handlers = [
            self._parse_add_intent,
            self._parse_summary_intent,
            self._parse_predict_intent,
            self._parse_biggest_category_intent,
        ]
        for handler in handlers:
            result = handler(text)
            if result:
                return result
        return "I can add expenses (e.g., 'spent 120 on food yesterday'), show summaries (today/week/month), or predict next month."



