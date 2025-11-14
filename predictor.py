from __future__ import annotations

from typing import Dict, List, Tuple

from db import ExpenseDB


def _linear_regression(x_values: List[float], y_values: List[float]) -> Tuple[float, float]:
    """Simple least squares linear regression.

    Returns (slope, intercept) for y = slope * x + intercept.
    Falls back to a flat line (slope=0) when there is insufficient variance.
    """
    n = float(len(x_values))
    if n == 0:
        return 0.0, 0.0
    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n
    denom = sum((x - x_mean) ** 2 for x in x_values)
    if denom == 0:
        # All x are the same or only one point; return constant line at the mean
        return 0.0, y_mean
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values)) / denom
    intercept = y_mean - slope * x_mean
    return slope, intercept


class Predictor:
    def __init__(self, db: ExpenseDB) -> None:
        self.db = db

    def predict_next_month(self, months_back: int = 6) -> Dict:
        """Predict the next month's total and per-category spend.

        Improvements over the naive version:
        - Safely clamps the lookback window to available months
        - Sorts months chronologically using YYYY-MM
        - Falls back to recent average when regression is unstable
        - Builds per-category series with implicit zeros for missing months
        - Ensures non-negative outputs
        """
        monthly_totals = self.db.monthly_totals()
        if not monthly_totals:
            return {"total_next_month": 0.0, "per_category_next_month": {}}

        # Sort keys chronologically; keys are YYYY-MM strings so lexicographic works,
        # but we still keep this explicit to document the intent.
        keys_sorted = sorted(monthly_totals.keys())

        # Clamp lookback window
        lookback = max(2, min(months_back, len(keys_sorted)))
        keys_recent = keys_sorted[-lookback:]
        y_values = [max(0.0, float(monthly_totals[k])) for k in keys_recent]
        x_values = list(range(len(keys_recent)))

        slope, intercept = _linear_regression(x_values, y_values)
        next_x = len(x_values)
        regressed_total = slope * next_x + intercept

        # Fallback to recent average if regression yields a negative or NaN-like value
        recent_avg = sum(y_values) / float(len(y_values)) if y_values else 0.0
        total_next = regressed_total if regressed_total >= 0 else recent_avg
        total_next = max(0.0, float(total_next))

        # Per-category projection
        by_cat = self.db.monthly_totals_by_category()
        per_category_next: Dict[str, float] = {}

        if by_cat:
            # Build unified set of categories seen in the lookback window
            categories: set[str] = set()
            for k in keys_recent:
                month_map = by_cat.get(k, {})
                categories.update(month_map.keys())

            for category in sorted(categories):
                # Build dense series over the same keys (missing months -> 0)
                y_cat = [float(by_cat.get(k, {}).get(category, 0.0)) for k in keys_recent]
                x_cat = x_values
                if sum(y_cat) == 0:
                    # No signal for this category in the window
                    continue
                s, b = _linear_regression(x_cat, y_cat)
                cat_pred = s * len(x_cat) + b
                if cat_pred < 0:
                    # Fallback to recent average for this category
                    cat_pred = sum(y_cat) / float(len(y_cat))
                per_category_next[category] = max(0.0, float(cat_pred))

        # If we still do not have a breakdown, apportion using the latest month shares
        if not per_category_next:
            last_key = keys_recent[-1]
            last_cats = by_cat.get(last_key, {}) if by_cat else {}
            last_total = sum(last_cats.values()) or 1.0
            for category, cat_total in last_cats.items():
                per_category_next[category] = total_next * (float(cat_total) / float(last_total))

        return {"total_next_month": total_next, "per_category_next_month": per_category_next}



