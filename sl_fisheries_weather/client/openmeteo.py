import time
import requests
from email.utils import parsedate_to_datetime
from typing import Any, Dict

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
                self.ledger.reserve(cost_per_attempt)
            
            self._wait()
            self._last_request_time = time.monotonic()
            
            try:
                response = self.session.get(url, params=params, timeout=(10, 120))
                if response.status_code == 200:
                    return response.json()
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
                    # Wait the full time, don't cap it to 600 if server says otherwise
                    # But if it's too long, maybe we should raise deferral
                    time.sleep(wait_time)
                    continue
                elif response.status_code in {500, 502, 503, 504}:
                    time.sleep(5 * (2 ** (attempt - 1)))
                    continue
                response.raise_for_status()
            except (requests.Timeout, requests.ConnectionError) as e:
                last_error = e
                if attempt < 5:
                    time.sleep(5 * (2 ** (attempt - 1)))
                    continue
                raise RuntimeError(f"Connection/timeout after 5 attempts: {e}")
            except requests.RequestException as e:
                raise RuntimeError(f"Request failed: {e}")
        
        raise RuntimeError(f"Failed to fetch from Open-Meteo after 5 attempts. Last error: {last_error}")

    def __enter__(self): return self
    def __exit__(self, *args): self.session.close()
