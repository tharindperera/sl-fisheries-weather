import time
import random
import requests
from email.utils import parsedate_to_datetime
from typing import Any, Dict
from sl_fisheries_weather.budget.ledger import BudgetExceededError

class OpenMeteoClient:
    def __init__(self, ledger=None, session=None):
        self.ledger = ledger
        self.session = session or requests.Session()
        self._last_request_time = None
        self.min_delay = 5.0

    def _wait(self):
        if self._last_request_time is None: return
        elapsed = time.monotonic() - self._last_request_time
        remaining = self.min_delay - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def fetch(self, url: str, params: Dict[str, Any], cost_per_attempt: int = 1) -> Any:
        last_error = None
        for attempt in range(1, 6):
            if self.ledger:
                if hasattr(self.ledger, "wait_for_minute_capacity"):
                    self.ledger.wait_for_minute_capacity(cost_per_attempt)
                self.ledger.reserve(cost_per_attempt)
            
            self._wait()
            self._last_request_time = time.monotonic()
            
            try:
                response = self.session.get(url, params=params, timeout=(10, 120))
                if response.status_code == 200:
                    try:
                        return response.json()
                    except Exception as json_err:
                        # Open-Meteo occasionally returns 200 with an empty or truncated body
                        last_error = f"JSON decode error: {json_err}"
                        if attempt < 5:
                            jitter = random.uniform(0.8, 1.2)
                            time.sleep(5 * (2 ** (attempt - 1)) * jitter)
                            continue
                        raise RuntimeError(f"Failed to parse JSON response after {attempt} attempts: {json_err}")
                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_time = 60 * (2 ** (attempt - 1))
                    if retry_after:
                        try:
                            wait_time = int(retry_after)
                        except ValueError:
                            # Parse HTTP date
                            try:
                                dt = parsedate_to_datetime(retry_after)
                                wait_time = max(0, int((dt - dt.now(dt.tzinfo)).total_seconds()))
                            except Exception:
                                pass
                    # If server requests wait longer than 2 minutes, defer remaining work rather than stalling CI
                    if wait_time > 120:
                        raise BudgetExceededError(f"HTTP 429 rate limit exceeded. Retry-After {wait_time}s.")
                    time.sleep(wait_time)
                    continue
                elif response.status_code in {500, 502, 503, 504}:
                    last_error = f"HTTP {response.status_code}"
                    jitter = random.uniform(0.8, 1.2)
                    time.sleep(5 * (2 ** (attempt - 1)) * jitter)
                    continue
                elif 400 <= response.status_code < 500:
                    # Client errors (400 Bad Request, 401, 403, 404) must fail immediately without blind retries
                    response.raise_for_status()
                response.raise_for_status()
            except (requests.Timeout, requests.ConnectionError) as e:
                last_error = e
                if attempt < 5:
                    jitter = random.uniform(0.8, 1.2)
                    time.sleep(5 * (2 ** (attempt - 1)) * jitter)
                    continue
                raise RuntimeError(f"Connection/timeout after 5 attempts: {e}")
            except requests.HTTPError as e:
                raise RuntimeError(f"HTTP error: {e}")
            except BudgetExceededError:
                raise
            except requests.RequestException as e:
                raise RuntimeError(f"Request failed: {e}")
        
        raise RuntimeError(f"Failed to fetch from Open-Meteo after 5 attempts. Last error: {last_error}")

    def __enter__(self): return self
    def __exit__(self, *args): self.session.close()
