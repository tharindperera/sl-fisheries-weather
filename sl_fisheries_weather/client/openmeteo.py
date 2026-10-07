import time
import requests
from typing import Any, Dict

class OpenMeteoClient:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self._last_request_time = None
        self.min_delay = 5.0 # 5 seconds minimum delay

    def _wait(self):
        if self._last_request_time is None: return
        elapsed = time.monotonic() - self._last_request_time
        remaining = self.min_delay - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def fetch(self, url: str, params: Dict[str, Any]) -> Any:
        for attempt in range(1, 6):
            self._wait()
            self._last_request_time = time.monotonic()
            try:
                response = self.session.get(url, params=params, timeout=(10, 120))
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_time = int(retry_after) if retry_after else 60 * (2 ** (attempt - 1))
                    time.sleep(min(wait_time, 600))
                    continue
                elif response.status_code in {500, 502, 503, 504}:
                    time.sleep(5 * (2 ** (attempt - 1)))
                    continue
                response.raise_for_status()
            except (requests.Timeout, requests.ConnectionError):
                if attempt < 5:
                    time.sleep(5 * (2 ** (attempt - 1)))
                    continue
                raise
        raise RuntimeError("Failed to fetch from Open-Meteo after 5 attempts.")

    def __enter__(self): return self
    def __exit__(self, *args): self.session.close()
