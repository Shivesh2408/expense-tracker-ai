import csv
import os
import sqlite3
from datetime import date, timedelta
from typing import Dict, List, Optional


class ExpenseDB:
    def __init__(self, db_path: str = "expenses.db") -> None:
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def add_expense(self, date_iso: str, amount: float, description: str, category: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO expenses(date, amount, description, category) VALUES(?, ?, ?, ?)",
                (date_iso, amount, description, category),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def list_expenses(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        query = "SELECT id, date, amount, description, category FROM expenses"
        clauses: List[str] = []
        params: List = []
        if start_date:
            clauses.append("date >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("date <= ?")
            params.append(end_date)
        if category:
            clauses.append("LOWER(category) = LOWER(?)")
            params.append(category)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY date DESC, id DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def _date_range_for_period(self, period: str) -> (str, str):
        today = date.today()
        if period == "day":
            start = today
        elif period == "week":
            start = today - timedelta(days=today.weekday())
        elif period == "month":
            start = today.replace(day=1)
        elif period == "all":
            return ("0001-01-01", "9999-12-31")
        else:
            raise ValueError("Invalid period")
        return (start.isoformat(), today.isoformat())

    def get_summary(self, period: str) -> Dict:
        start_date, end_date = self._date_range_for_period(period)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            total_row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE date BETWEEN ? AND ?",
                (start_date, end_date),
            ).fetchone()
            by_category_rows = conn.execute(
                "SELECT category, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE date BETWEEN ? AND ? GROUP BY category",
                (start_date, end_date),
            ).fetchall()
        by_category = {row["category"]: float(row["total"]) for row in by_category_rows}
        return {"total": float(total_row["total"]), "by_category": by_category}

    def monthly_totals(self) -> Dict[str, float]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT substr(date, 1, 7) AS ym, SUM(amount) AS total
                FROM expenses
                GROUP BY ym
                ORDER BY ym
                """
            ).fetchall()
        return {row["ym"]: float(row["total"]) for row in rows}

    def monthly_totals_by_category(self) -> Dict[str, Dict[str, float]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT substr(date, 1, 7) AS ym, category, SUM(amount) AS total
                FROM expenses
                GROUP BY ym, category
                ORDER BY ym, category
                """
            ).fetchall()
        result: Dict[str, Dict[str, float]] = {}
        for row in rows:
            ym = row["ym"]
            category = row["category"]
            total = float(row["total"])
            if ym not in result:
                result[ym] = {}
            result[ym][category] = total
        return result

    def export_csv(self, path: str) -> str:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, date, amount, description, category FROM expenses ORDER BY date, id").fetchall()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "date", "amount", "description", "category"])
            for row in rows:
                writer.writerow([row["id"], row["date"], row["amount"], row["description"], row["category"]])
        return os.path.abspath(path)



