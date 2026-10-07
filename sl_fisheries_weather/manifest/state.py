import json
from pathlib import Path
from sl_fisheries_weather.config import DATA_DIR

class CheckpointManager:
    def __init__(self, filename="checkpoint.json"):
        self.path = Path(DATA_DIR) / filename
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self):
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self):
        with self.path.with_suffix(".tmp").open("w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)
        self.path.with_suffix(".tmp").replace(self.path)

    def is_completed(self, work_id: str) -> bool:
        return self.state.get(work_id, {}).get("status") == "success"

    def mark_success(self, work_id: str, metadata: dict = None):
        self.state[work_id] = {"status": "success", "metadata": metadata or {}}
        self._save()

    def mark_failure(self, work_id: str, error: str, metadata: dict = None):
        self.state[work_id] = {"status": "failed", "error": error, "metadata": metadata or {}}
        self._save()

    def get_all(self):
        return self.state
