import os
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from huggingface_hub import HfApi

from sl_fisheries_weather.config import (
    DATA_DIR, ATMOSPHERE_DAILY, MARINE_DAILY, TIMEZONE,
    OPENMETEO_ARCHIVE_URL, OPENMETEO_MARINE_ARCHIVE_URL
)
from sl_fisheries_weather.backfill.worker import Worker
from sl_fisheries_weather.parquet_store.writer import write_parquet
from sl_fisheries_weather.parquet_store.schema import WEATHER_SCHEMA, MARINE_SCHEMA
from sl_fisheries_weather.manifest.state import CheckpointManager

def compute_hash(data: dict) -> str:
    return hashlib.md5(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()

class Runner:
    def __init__(self, worker: Worker, checkpoint: CheckpointManager, repo_id: str):
        self.worker = worker
        self.checkpoint = checkpoint
        self.repo_id = repo_id

    def backfill(self, sites: list, start_date_str: str, end_date_str: str, max_runtime_minutes: int, max_calls: int):
        start_time = datetime.now()
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        batches = [sites[i:i+8] for i in range(0, len(sites), 8)]
        
        calls_made = 0
        
        # Loop over windows
        current_start = start_date
        while current_start <= end_date:
            current_end = current_start + timedelta(days=13) # 14 day window
            if current_end > end_date:
                current_end = end_date
                
            expected_days = (current_end - current_start).days + 1
            s_date = current_start.strftime("%Y-%m-%d")
            e_date = current_end.strftime("%Y-%m-%d")
            
            for i, batch in enumerate(batches):
                work_id = f"backfill_{s_date}_{e_date}_batch_{i}"
                if self.checkpoint.is_completed(work_id):
                    continue
                    
                # Time limit check
                if (datetime.now() - start_time).total_seconds() / 60 > max_runtime_minutes:
                    print("Reached max runtime.")
                    return
                if calls_made >= max_calls:
                    print("Reached max calls.")
                    return

                # Fetch atmosphere
                params_atmos = {
                    "latitude": ",".join(str(s.lat_land) for s in batch),
                    "longitude": ",".join(str(s.lon_land) for s in batch),
                    "start_date": s_date,
                    "end_date": e_date,
                    "models": "era5",
                    "daily": ",".join(ATMOSPHERE_DAILY),
                    "timezone": TIMEZONE,
                    "cell_selection": "land",
                    "temperature_unit": "celsius",
                    "wind_speed_unit": "ms",
                    "precipitation_unit": "mm"
                }
                
                try:
                    res_atmos = self.worker.fetch_batch(f"atmos_{work_id}", OPENMETEO_ARCHIVE_URL, params_atmos, len(batch), expected_days, s_date, ATMOSPHERE_DAILY)
                    calls_made += self.worker._estimate_cost(len(batch), 1, len(ATMOSPHERE_DAILY), expected_days)
                    
                    df_atmos = self._parse_to_df(res_atmos, batch, "era5", "weather_reanalysis")
                    self._save_parquet(df_atmos, "weather_reanalysis", s_date[:4], WEATHER_SCHEMA)
                except Exception as e:
                    print(f"Failed atmos {work_id}: {e}")
                    self.checkpoint.mark_failure(work_id, str(e))
                    return

                # Fetch marine
                params_marine = {
                    "latitude": ",".join(str(s.lat_sea) for s in batch),
                    "longitude": ",".join(str(s.lon_sea) for s in batch),
                    "start_date": s_date,
                    "end_date": e_date,
                    "models": "era5_ocean",
                    "daily": ",".join(MARINE_DAILY),
                    "timezone": TIMEZONE,
                    "cell_selection": "sea"
                }
                
                try:
                    res_marine = self.worker.fetch_batch(f"marine_{work_id}", OPENMETEO_MARINE_ARCHIVE_URL, params_marine, len(batch), expected_days, s_date, MARINE_DAILY)
                    calls_made += self.worker._estimate_cost(len(batch), 1, len(MARINE_DAILY), expected_days)
                    
                    df_marine = self._parse_to_df(res_marine, batch, "era5_ocean", "marine_reanalysis")
                    self._save_parquet(df_marine, "marine_reanalysis", s_date[:4], MARINE_SCHEMA)
                except Exception as e:
                    print(f"Failed marine {work_id}: {e}")
                    self.checkpoint.mark_failure(work_id, str(e))
                    return

                self.checkpoint.mark_success(work_id)
                print(f"Completed {work_id}")

            current_start = current_end + timedelta(days=1)
            
    def _parse_to_df(self, results, batch, model_name, record_type) -> pd.DataFrame:
        rows = []
        for res, site in zip(results, batch):
            daily = res["daily"]
            time_arr = daily["time"]
            for i, t in enumerate(time_arr):
                row = {
                    "site_id": site.site_id,
                    "date_local": t,
                    "model": model_name,
                    "snapshot_id": "historical" if "reanalysis" in record_type else t, # simplification
                }
                for k, v in daily.items():
                    if k != "time":
                        row[k] = v[i]
                rows.append(row)
        return pd.DataFrame(rows)

    def _save_parquet(self, df: pd.DataFrame, record_type: str, year: str, schema):
        # We append/upsert. In this simple implementation, we'll read existing, concat, drop duplicates, and write back.
        path = Path(DATA_DIR) / record_type / f"year={year}" / f"{record_type.split('_')[0]}.parquet"
        if path.exists():
            existing = pd.read_parquet(path)
            df = pd.concat([existing, df]).drop_duplicates(subset=["site_id", "date_local", "model", "snapshot_id"], keep="last")
        write_parquet(df, str(path), schema=schema)
        self.publish_to_hf(record_type, str(path), year)

    def publish_to_hf(self, record_type: str, file_path: str, year: str):
        try:
            from huggingface_hub import CommitOperationAdd
            from sl_fisheries_weather.publish_hf.publisher import Publisher
            pub = Publisher(self.repo_id)
            operations = [
                CommitOperationAdd(path_in_repo=f"data/{record_type}/year={year}/{record_type.split('_')[0]}.parquet", path_or_fileobj=file_path)
            ]
            pub.publish_data(f"Automated backfill: {record_type} for {year}", operations)
        except Exception as e:
            print(f"Failed to publish to HF: {e}")
