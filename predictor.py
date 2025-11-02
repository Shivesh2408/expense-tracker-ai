from __future__ import annotations

from typing import Dict, List, Tuple

from db import ExpenseDB


def _linear_regression(x_values: List[float], y_values: List[float]) -> Tuple[float, float]:
    n = float(len(x_values))
    if n == 0:
        return 0.0, 0.0
    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n
    denom = sum((x - x_mean) ** 2 for x in x_values)
    if denom == 0:
        return 0.0, y_mean
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values)) / denom
    intercept = y_mean - slope * x_mean
    return slope, intercept


class Predictor:
    def __init__(self, db: ExpenseDB) -> None:
        self.db = db

    def predict_next_month(self, months_back: int = 6) -> Dict:
        monthly_totals = self.db.monthly_totals()
        if not monthly_totals:
            return {"total_next_month": 0.0, "per_category_next_month": {}}

        keys_sorted = sorted(monthly_totals.keys())
        keys_recent = keys_sorted[-months_back:]
        y_values = [monthly_totals[k] for k in keys_recent]
        x_values = list(range(len(keys_recent)))

        slope, intercept = _linear_regression(x_values, y_values)
        next_x = len(x_values)
        total_next = max(0.0, slope * next_x + intercept)

        by_cat = self.db.monthly_totals_by_category()
        per_category_next: Dict[str, float] = {}
        if by_cat:
            all_categories = set()
            for month_map in by_cat.values():
                all_categories.update(month_map.keys())
            for category in sorted(all_categories):
                series_keys = [k for k in keys_recent if k in by_cat and category in by_cat[k]]
                if len(series_keys) >= 2:
                    y_cat = [by_cat[k][category] for k in series_keys]
                    x_cat = list(range(len(series_keys)))
                    s, b = _linear_regression(x_cat, y_cat)
                    per_category_next[category] = max(0.0, s * len(series_keys) + b)
        if not per_category_next:
            last_key = keys_recent[-1]
            last_cats = by_cat.get(last_key, {}) if by_cat else {}
            last_total = sum(last_cats.values()) or 1.0
            for category, cat_total in last_cats.items():
                per_category_next[category] = total_next * (cat_total / last_total)

        return {"total_next_month": total_next, "per_category_next_month": per_category_next}



