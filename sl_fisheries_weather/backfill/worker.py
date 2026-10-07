import json
from datetime import date, timedelta
from sl_fisheries_weather.config import (
    OPENMETEO_ARCHIVE_URL, OPENMETEO_MARINE_ARCHIVE_URL,
    OPENMETEO_FORECAST_URL, OPENMETEO_MARINE_FORECAST_URL,
    ATMOSPHERE_DAILY, MARINE_DAILY, TIMEZONE
)
from sl_fisheries_weather.client.openmeteo import OpenMeteoClient
from sl_fisheries_weather.budget.ledger import Ledger
from sl_fisheries_weather.validation.checks import validate_response

class Worker:
    def __init__(self, ledger: Ledger, out_dir: str):
        self.ledger = ledger
        self.out_dir = out_dir
        self.client = OpenMeteoClient()

    def _estimate_cost(self, num_locations: int, num_models: int, num_vars: int, num_days: int) -> int:
        var_factor = max(1, num_vars / 10)
        day_factor = max(1, num_days / 14)
        return int(num_locations * num_models * var_factor * day_factor)

    def fetch_batch(self, work_id: str, url: str, params: dict, expected_locs: int, expected_days: int):
        # cost
        models_count = len(params.get("models", "").split(","))
        vars_count = len(params.get("daily", "").split(","))
        cost = self._estimate_cost(expected_locs, models_count, vars_count, expected_days)
        
        self.ledger.reserve(cost)
        try:
            data = self.client.fetch(url, params)
            results = validate_response(data, expected_locs, expected_days)
            return results
        except Exception as e:
            # We don't refund if failure was actual network call, but budget is safety budget
            raise e
