import json
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from sl_fisheries_weather.config import DATA_DIR

class BudgetExceededError(Exception):
    pass

class Ledger:
    def __init__(self, limits: dict):
        self.limits = limits
        self.budget_file = Path(DATA_DIR) / "budget_state.json"
        self.budget_file.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self):
        if not self.budget_file.exists():
            return {
                "minute_calls": [],
                "hour_calls": [],
                "day_calls": [],
                "month_calls": []
            }
        with self.budget_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self):
        with self.budget_file.with_suffix(".tmp").open("w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)
        self.budget_file.with_suffix(".tmp").replace(self.budget_file)

    @staticmethod
    def _now() -> float:
        return datetime.now(timezone.utc).timestamp()

    def _cleanup_rolling(self):
        now = self._now()
        # Remove items outside the rolling window
        self.state["minute_calls"] = [t for t in self.state["minute_calls"] if now - t["time"] < 60]
        self.state["hour_calls"] = [t for t in self.state["hour_calls"] if now - t["time"] < 3600]
        self.state["day_calls"] = [t for t in self.state["day_calls"] if now - t["time"] < 86400]
        # For month, use 30 days = 2592000 seconds
        self.state["month_calls"] = [t for t in self.state["month_calls"] if now - t["time"] < 2592000]

    def _get_sum(self, window_key: str) -> int:
        return sum(item["cost"] for item in self.state[window_key])

    def can_consume(self, cost: int) -> bool:
        self._cleanup_rolling()
        return (
            self._get_sum("minute_calls") + cost <= self.limits["minute"] and
            self._get_sum("hour_calls") + cost <= self.limits["hour"] and
            self._get_sum("day_calls") + cost <= self.limits["day"] and
            self._get_sum("month_calls") + cost <= self.limits["month"]
        )

    def reserve(self, cost: int):
        if not self.can_consume(cost):
            raise BudgetExceededError("API budget exceeded.")
        
        now = self._now()
        entry = {"time": now, "cost": cost}
        self.state["minute_calls"].append(entry)
        self.state["hour_calls"].append(entry)
        self.state["day_calls"].append(entry)
        self.state["month_calls"].append(entry)
        self._save()

    def refund(self, cost: int):
        # We can refund by removing the last element if it matches, or adding a negative cost entry
        # Adding a negative cost entry is simpler and correctly expires.
        now = self._now()
        entry = {"time": now, "cost": -cost}
        self.state["minute_calls"].append(entry)
        self.state["hour_calls"].append(entry)
        self.state["day_calls"].append(entry)
        self.state["month_calls"].append(entry)
        self._save()
