import json
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
        self._reset_expired()

    def _load(self):
        if not self.budget_file.exists():
            return {
                "minute_calls": 0, "minute_start": self._now(),
                "hour_calls": 0, "hour_start": self._now(),
                "day_calls": 0, "day_start": self._now(),
                "month_calls": 0, "month_start": self._now()
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

    def _reset_expired(self):
        now = self._now()
        if now - self.state["minute_start"] >= 60:
            self.state["minute_calls"] = 0
            self.state["minute_start"] = now
        if now - self.state["hour_start"] >= 3600:
            self.state["hour_calls"] = 0
            self.state["hour_start"] = now
        if now - self.state["day_start"] >= 86400:
            self.state["day_calls"] = 0
            self.state["day_start"] = now
        # simple 30-day month approximation for budget reset
        if now - self.state["month_start"] >= 2592000:
            self.state["month_calls"] = 0
            self.state["month_start"] = now
        self._save()

    def can_consume(self, cost: int) -> bool:
        self._reset_expired()
        return (
            self.state["minute_calls"] + cost <= self.limits["minute"] and
            self.state["hour_calls"] + cost <= self.limits["hour"] and
            self.state["day_calls"] + cost <= self.limits["day"] and
            self.state["month_calls"] + cost <= self.limits["month"]
        )

    def reserve(self, cost: int):
        if not self.can_consume(cost):
            raise BudgetExceededError("API budget exceeded.")
        self.state["minute_calls"] += cost
        self.state["hour_calls"] += cost
        self.state["day_calls"] += cost
        self.state["month_calls"] += cost
        self._save()

    def refund(self, cost: int):
        self.state["minute_calls"] = max(0, self.state["minute_calls"] - cost)
        self.state["hour_calls"] = max(0, self.state["hour_calls"] - cost)
        self.state["day_calls"] = max(0, self.state["day_calls"] - cost)
        self.state["month_calls"] = max(0, self.state["month_calls"] - cost)
        self._save()
