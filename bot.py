import re
from datetime import date, timedelta, datetime
from typing import Optional, List, Dict

from db import ExpenseDB
from categorizer import CategoryRules
from predictor import Predictor


class ChatBot:
    def __init__(self, db: ExpenseDB, rules: CategoryRules) -> None:
        self.db = db
        self.rules = rules
        self.predictor = Predictor(db)

    def _parse_add_intent(self, text: str) -> Optional[str]:
        """Enhanced add expense parser with multiple patterns"""
        lowered = text.lower()
        
        # Pattern 1: "spent 100 on food", "spent 50 for taxi"
        pattern1 = r"(?:spent|spend|paid|spending)\s+(?:₹|rs|rupees?)?\s*(\d+(?:\.\d{1,2})?)\s+(?:on|for|at)\s+(.+?)(?:\s+(?:yesterday|today|on\s+\d{4}-\d{2}-\d{2}))?$"
        
        # Pattern 2: "add expense 100 food", "add 50 taxi"
        pattern2 = r"(?:add|adding|record|enter)\s+(?:expense\s+)?(?:₹|rs|rupees?)?\s*(\d+(?:\.\d{1,2})?)\s+(.+?)(?:\s+(?:yesterday|today|on\s+\d{4}-\d{2}-\d{2}))?$"
        
        # Pattern 3: "100 on food", "50 for coffee"
        pattern3 = r"^(?:₹|rs|rupees?)?\s*(\d+(?:\.\d{1,2})?)\s+(?:on|for|at)\s+(.+)$"
        
        amount = None
        description = None
        date_iso = date.today().isoformat()
        
        # Try pattern 1
        match = re.search(pattern1, lowered, re.IGNORECASE)
        if match:
            amount = float(match.group(1))
            description = match.group(2).strip()
        
        # Try pattern 2
        if not match:
            match = re.search(pattern2, lowered, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                description = match.group(2).strip()
        
        # Try pattern 3
        if not match:
            match = re.search(pattern3, text, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                description = match.group(2).strip()
        
        if not amount or not description:
            return None
        
        # Parse date
        if "yesterday" in lowered:
            date_iso = (date.today() - timedelta(days=1)).isoformat()
        elif "today" in lowered:
            date_iso = date.today().isoformat()
        else:
            # Try to extract date like "on 2025-11-05" or "on 05/11/2025"
            date_match = re.search(r"on\s+(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
            if date_match:
                date_iso = date_match.group(1)
        
        # Clean description
        description = re.sub(r"\s+(?:yesterday|today|on\s+\d{4}-\d{2}-\d{2}).*$", "", description, flags=re.IGNORECASE).strip()
        
        if not description or description == "":
            description = "misc"
        
        category = self.rules.categorize(description)
        expense_id = self.db.add_expense(date_iso=date_iso, amount=amount, description=description, category=category)
        return f"✅ Added expense #{expense_id}: ₹{amount:.2f} ({category}) - {description} on {date_iso}"

    def _parse_summary_intent(self, text: str) -> Optional[str]:
        """Enhanced summary parser with better period detection"""
        lowered = text.lower()
        
        # Check for summary keywords
        if not any(word in lowered for word in ["summary", "total", "spent", "spending", "how much", "show", "expenses"]):
            return None
        
        # Determine period
        period = None
        if any(word in lowered for word in ["today", "this day"]):
            period = "day"
        elif any(word in lowered for word in ["this week", "week", "weekly"]):
            period = "week"
        elif any(word in lowered for word in ["this month", "month", "monthly"]):
            period = "month"
        elif any(word in lowered for word in ["all", "total", "everything", "ever"]):
            period = "all"
        else:
            # Default to month if no period specified
            period = "month"
        
        summary = self.db.get_summary(period)
        if summary["total"] == 0:
            return f"No expenses found for {period}."
        
        parts = [f"📊 Total for {period}: ₹{summary['total']:.2f}"]
        
        if summary["by_category"]:
            cat_parts = []
            sorted_cats = sorted(summary["by_category"].items(), key=lambda x: -x[1])
            for cat, amt in sorted_cats:
                percentage = (amt / summary["total"]) * 100
                cat_parts.append(f"{cat}: ₹{amt:.2f} ({percentage:.1f}%)")
            parts.append("By category: " + ", ".join(cat_parts))
        
        return "\n".join(parts)

    def _parse_list_intent(self, text: str) -> Optional[str]:
        """List expenses with filters"""
        lowered = text.lower()
        
        if not any(word in lowered for word in ["list", "show", "display", "expenses", "transactions", "history"]):
            return None
        
        # Parse category filter
        category = None
        for cat in ["food", "travel", "shopping", "bills", "entertainment", "health", "other"]:
            if cat in lowered:
                category = cat.capitalize()
                break
        
        # Parse date filters
        start_date = None
        end_date = None
        
        if "last week" in lowered or "past week" in lowered:
            end_date = date.today().isoformat()
            start_date = (date.today() - timedelta(days=7)).isoformat()
        elif "last month" in lowered or "past month" in lowered:
            end_date = date.today().isoformat()
            start_date = (date.today() - timedelta(days=30)).isoformat()
        
        expenses = self.db.list_expenses(start_date=start_date, end_date=end_date, category=category, limit=10)
        
        if not expenses:
            return "No expenses found matching your criteria."
        
        result = [f"📋 Found {len(expenses)} expense(s):"]
        for exp in expenses[:10]:  # Limit to 10 for readability
            result.append(f"  • {exp['date']}: ₹{exp['amount']:.2f} ({exp['category']}) - {exp['description']}")
        
        if len(expenses) > 10:
            result.append(f"\n... and {len(expenses) - 10} more. Visit /list for full list.")
        
        return "\n".join(result)

    def _parse_category_intent(self, text: str) -> Optional[str]:
        """Category-specific queries"""
        lowered = text.lower()
        
        # Check for category-specific questions
        for cat in ["food", "travel", "shopping", "bills", "entertainment", "health", "other"]:
            if cat in lowered and any(word in lowered for word in ["how much", "spent", "total", "spending"]):
                category = cat.capitalize()
                summary = self.db.get_summary("month")
                amount = summary["by_category"].get(category, 0)
                if amount == 0:
                    return f"No expenses found for {category} this month."
                percentage = (amount / summary["total"]) * 100 if summary["total"] > 0 else 0
                return f"💰 {category} expenses this month: ₹{amount:.2f} ({percentage:.1f}% of total)"
        
        return None

    def _parse_predict_intent(self, text: str) -> Optional[str]:
        """Enhanced prediction with better formatting"""
        lowered = text.lower()
        
        if not any(word in lowered for word in ["predict", "forecast", "next month", "future", "estimate"]):
            return None
        
        forecast = self.predictor.predict_next_month()
        out = [f"🔮 Prediction for next month: ₹{forecast['total_next_month']:.2f}"]
        
        if forecast["per_category_next_month"]:
            cat_parts = []
            sorted_cats = sorted(forecast["per_category_next_month"].items(), key=lambda x: -x[1])
            for cat, amt in sorted_cats:
                cat_parts.append(f"{cat}: ₹{amt:.2f}")
            out.append("Per category: " + ", ".join(cat_parts))
        else:
            out.append("(Not enough historical data for category breakdown)")
        
        return "\n".join(out)

    def _parse_biggest_category_intent(self, text: str) -> Optional[str]:
        """Enhanced biggest category query"""
        if not re.search(r"(biggest|largest|most|highest|top)\s+(spend|spending|expense|category|cost)", text, re.IGNORECASE):
            return None
        
        summary = self.db.get_summary("month")
        if not summary["by_category"]:
            return "No expense data available yet."
        
        sorted_cats = sorted(summary["by_category"].items(), key=lambda kv: -kv[1])
        top_3 = sorted_cats[:3]
        
        result = ["🏆 Top spending categories this month:"]
        for i, (cat, amt) in enumerate(top_3, 1):
            percentage = (amt / summary["total"]) * 100 if summary["total"] > 0 else 0
            result.append(f"  {i}. {cat}: ₹{amt:.2f} ({percentage:.1f}%)")
        
        return "\n".join(result)

    def _parse_stats_intent(self, text: str) -> Optional[str]:
        """General statistics"""
        lowered = text.lower()
        
        if not any(word in lowered for word in ["stat", "insight", "analyze", "breakdown", "overview"]):
            return None
        
        summary = self.db.get_summary("month")
        if summary["total"] == 0:
            return "No expense data available yet."
        
        # Get recent expenses count
        recent = self.db.list_expenses(limit=100)
        count = len(recent)
        
        # Average daily spending
        monthly_summary = self.db.get_summary("month")
        days_in_month = date.today().day
        avg_daily = monthly_summary["total"] / days_in_month if days_in_month > 0 else 0
        
        result = [
            f"📈 Statistics:",
            f"  • Total expenses this month: ₹{monthly_summary['total']:.2f}",
            f"  • Average daily spending: ₹{avg_daily:.2f}",
            f"  • Total transactions: {count}",
            f"  • Categories: {len(monthly_summary['by_category'])}"
        ]
        
        return "\n".join(result)

    def _parse_help_intent(self, text: str) -> Optional[str]:
        """Help and guidance"""
        lowered = text.lower()
        
        if not any(word in lowered for word in ["help", "what can", "how do", "commands", "examples"]):
            return None
        
        return """🤖 I can help you with:
• Add expenses: "spent 100 on food", "add 50 for taxi", "100 on coffee"
• View summaries: "show summary", "total this month", "how much today"
• List expenses: "list expenses", "show my transactions", "show food expenses"
• Category queries: "how much on food", "travel expenses"
• Predictions: "predict next month", "forecast"
• Top categories: "biggest category", "top spending"
• Statistics: "show stats", "insights"

Try: "spent 150 on groceries" or "show summary this month"
"""

    def respond(self, text: str) -> str:
        """Main response handler with improved intent detection"""
        if not text or not text.strip():
            return "Please enter a message. Type 'help' for examples."
        
        text = text.strip()
        
        # Handler priority order
        handlers = [
            self._parse_help_intent,
            self._parse_add_intent,
            self._parse_list_intent,
            self._parse_category_intent,
            self._parse_summary_intent,
            self._parse_biggest_category_intent,
            self._parse_stats_intent,
            self._parse_predict_intent,
        ]
        
        for handler in handlers:
            result = handler(text)
            if result:
                return result
        
        # Default response with suggestions
        return "🤔 I didn't understand that. Try:\n• 'spent 100 on food' to add expense\n• 'show summary' for totals\n• 'help' for more examples"
