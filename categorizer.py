import json
import os
from typing import Dict, List


DEFAULT_RULES: Dict[str, List[str]] = {
    "Food": ["food", "meal", "restaurant", "cafe", "grocer", "pizza", "burger"],
    "Travel": ["uber", "ola", "taxi", "bus", "train", "flight", "fuel", "petrol"],
    "Shopping": ["amazon", "flipkart", "mall", "shop", "clothes", "electronics"],
    "Bills": ["electric", "water", "wifi", "internet", "mobile", "recharge", "rent"],
    "Entertainment": ["movie", "netflix", "spotify", "game"],
    "Health": ["doctor", "pharmacy", "medicine", "hospital", "gym"],
    "Other": [],
}


class CategoryRules:
    def __init__(self, path: str = "categories.json") -> None:
        self.path = path
        self._rules = self._load_or_default()

    def _load_or_default(self) -> Dict[str, List[str]]:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    rules: Dict[str, List[str]] = {}
                    for category, keywords in data.items():
                        rules[str(category)] = [str(k).lower() for k in keywords]
                    return rules
            except Exception:
                pass
        return {k: [kw.lower() for kw in v] for k, v in DEFAULT_RULES.items()}

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._rules, f, indent=2, ensure_ascii=False)

    def get_rules(self) -> Dict[str, List[str]]:
        return self._rules

    def categorize(self, description: str) -> str:
        text = description.lower()
        best_category = "Other"
        best_match_count = 0
        for category, keywords in self._rules.items():
            match_count = sum(1 for kw in keywords if kw and kw in text)
            if match_count > best_match_count:
                best_match_count = match_count
                best_category = category
        return best_category

    def add_keyword(self, category: str, keyword: str) -> None:
        if category not in self._rules:
            self._rules[category] = []
        kw_lower = keyword.lower()
        if kw_lower not in self._rules[category]:
            self._rules[category].append(kw_lower)

    def remove_keyword(self, category: str, keyword: str) -> None:
        if category in self._rules:
            kw_lower = keyword.lower()
            self._rules[category] = [k for k in self._rules[category] if k != kw_lower]



