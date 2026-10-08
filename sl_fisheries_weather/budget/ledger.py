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
        try:
            with self.budget_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "minute_calls": [],
                "hour_calls": [],
                "day_calls": [],
                "month_calls": []
            }

    def reload(self):
        self.state = self._load()

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
        self.state["minute_calls"] = [t for t in self.state.get("minute_calls", []) if now - t["time"] < 60]
        self.state["hour_calls"] = [t for t in self.state.get("hour_calls", []) if now - t["time"] < 3600]
        self.state["day_calls"] = [t for t in self.state.get("day_calls", []) if now - t["time"] < 86400]
        # For month, use 30 days = 2592000 seconds
        self.state["month_calls"] = [t for t in self.state.get("month_calls", []) if now - t["time"] < 2592000]

    def _get_sum(self, window_key: str) -> int:
        return max(0, sum(item["cost"] for item in self.state.get(window_key, [])))

    def can_consume(self, cost: int) -> bool:
        self._cleanup_rolling()
        return (
            self._get_sum("minute_calls") + cost <= self.limits["minute"] and
            self._get_sum("hour_calls") + cost <= self.limits["hour"] and
            self._get_sum("day_calls") + cost <= self.limits["day"] and
            self._get_sum("month_calls") + cost <= self.limits["month"]
        )

    def wait_for_minute_capacity(self, cost: int, max_wait: float = 65.0) -> bool:
        """Wait if rolling minute quota is nearly full, preventing premature job aborts."""
        start_wait = self._now()
        while True:
            self._cleanup_rolling()
            if self._get_sum("minute_calls") + cost <= self.limits["minute"]:
                return True
            now = self._now()
            minute_calls = self.state.get("minute_calls", [])
            if not minute_calls:
                return True
            oldest_time = min(t["time"] for t in minute_calls)
            wait_needed = max(1.0, (oldest_time + 60.1) - now)
            if (self._now() - start_wait) + wait_needed > max_wait:
                return False
            time.sleep(wait_needed)

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
        now = self._now()
        entry = {"time": now, "cost": -cost}
        self.state["minute_calls"].append(entry)
        self.state["hour_calls"].append(entry)
        self.state["day_calls"].append(entry)
        self.state["month_calls"].append(entry)
        self._save()
