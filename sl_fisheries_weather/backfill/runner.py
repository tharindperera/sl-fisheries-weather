import os
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from huggingface_hub import HfApi, CommitOperationAdd
from zoneinfo import ZoneInfo
import shutil

from sl_fisheries_weather.config import (
    DATA_DIR, ATMOSPHERE_DAILY, MARINE_DAILY, TIMEZONE,
    OPENMETEO_ARCHIVE_URL, OPENMETEO_MARINE_ARCHIVE_URL,
    OPENMETEO_FORECAST_URL, OPENMETEO_MARINE_FORECAST_URL
)
from sl_fisheries_weather.backfill.worker import Worker
from sl_fisheries_weather.parquet_store.writer import write_parquet
from sl_fisheries_weather.parquet_store.schema import WEATHER_SCHEMA, MARINE_SCHEMA
from sl_fisheries_weather.manifest.state import CheckpointManager

def get_colombo_now():
    return datetime.now(ZoneInfo("Asia/Colombo"))

class Runner:
    def __init__(self, worker: Worker, checkpoint: CheckpointManager, repo_id: str):
        self.worker = worker
        self.checkpoint = checkpoint
        self.repo_id = repo_id
        self.api = HfApi()
        self.parent_commit = None
        self.files_to_upload = set()

    def restore(self):
        try:
            info = self.api.dataset_info(self.repo_id)
            self.parent_commit = info.sha
        except Exception as e:
            print(f"Could not fetch dataset info: {e}")
            return
            
        files = self.api.list_repo_files(repo_id=self.repo_id, repo_type="dataset")
        for f in files:
            if f.endswith(".parquet") or f in ["metadata/manifest.json", "metadata/coverage.json"]:
                try:
                    local_path = self.api.hf_hub_download(repo_id=self.repo_id, repo_type="dataset", filename=f)
                    dest = Path(DATA_DIR) / f
                    if f.startswith("data/"):
                        dest = Path(DATA_DIR) / f.replace("data/", "")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(local_path, dest)
                except Exception as e:
                    print(f"Failed to restore {f}: {e}")

    def backfill(self, sites: list, start_date_str: str, end_date_str: str, max_runtime_minutes: int, max_calls: int):
        self.restore()
        
        start_time = datetime.now()
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        batches = [sites[i:i+8] for i in range(0, len(sites), 8)]
        calls_made = 0
        
        for i, batch in enumerate(batches):
            current_start = start_date
            while current_start <= end_date:
                current_end = current_start + timedelta(days=13)
                if current_end > end_date:
                    current_end = end_date
                    
                s_date = current_start.strftime("%Y-%m-%d")
                e_date = current_end.strftime("%Y-%m-%d")
                expected_days = (current_end - current_start).days + 1
                
                # Assume batch runs together, simplified work id
                work_id = f"backfill_{s_date}_{e_date}_batch_{i}"
                if self.checkpoint.is_completed(work_id):
                    current_start = current_end + timedelta(days=1)
                    continue

                if (datetime.now() - start_time).total_seconds() / 60 > max_runtime_minutes:
                    print("Reached max runtime.")
                    self._commit_staged()
                    return

                cost_atmos = self.worker._estimate_cost(len(batch), 1, len(ATMOSPHERE_DAILY), expected_days)
                if calls_made + cost_atmos > max_calls:
                    print("Reached max calls (atmos).")
                    self._commit_staged()
                    return

                # Atmosphere
                params_atmos = {
                    "latitude": ",".join(str(s.lat_land) for s in batch),
                    "longitude": ",".join(str(s.lon_land) for s in batch),
                    "start_date": s_date, "end_date": e_date,
                    "models": "era5", "daily": ",".join(ATMOSPHERE_DAILY),
                    "timezone": TIMEZONE, "cell_selection": "land",
                    "temperature_unit": "celsius", "wind_speed_unit": "ms", "precipitation_unit": "mm"
                }
                
                try:
                    res_atmos = self.worker.fetch_batch(f"atmos_{work_id}", OPENMETEO_ARCHIVE_URL, params_atmos, len(batch), expected_days, s_date, ATMOSPHERE_DAILY)
                    calls_made += cost_atmos
                    df_atmos = self._parse_to_df(res_atmos, batch, "era5", "weather_reanalysis")
                    self._save_parquet(df_atmos, "weather_reanalysis", WEATHER_SCHEMA)
                except Exception as e:
                    print(f"Failed atmos {work_id}: {e}")
                    self.checkpoint.mark_failure(work_id, str(e))
                    self._commit_staged()
                    return

                cost_marine = self.worker._estimate_cost(len(batch), 1, len(MARINE_DAILY), expected_days)
                if calls_made + cost_marine > max_calls:
                    print("Reached max calls (marine).")
                    self._commit_staged()
                    return

                # Marine
                params_marine = {
                    "latitude": ",".join(str(s.lat_sea) for s in batch),
                    "longitude": ",".join(str(s.lon_sea) for s in batch),
                    "start_date": s_date, "end_date": e_date,
                    "models": "era5_ocean", "daily": ",".join(MARINE_DAILY),
                    "timezone": TIMEZONE, "cell_selection": "sea"
                }
                
                try:
                    res_marine = self.worker.fetch_batch(f"marine_{work_id}", OPENMETEO_MARINE_ARCHIVE_URL, params_marine, len(batch), expected_days, s_date, MARINE_DAILY)
                    calls_made += cost_marine
                    df_marine = self._parse_to_df(res_marine, batch, "era5_ocean", "marine_reanalysis")
                    self._save_parquet(df_marine, "marine_reanalysis", MARINE_SCHEMA)
                except Exception as e:
                    print(f"Failed marine {work_id}: {e}")
                    self.checkpoint.mark_failure(work_id, str(e))
                    self._commit_staged()
                    return

                # Check if we got full expected days. If not, it's a pending tail, do not mark completed.
                # Find min length across results
                min_days = expected_days
                for res in res_atmos + res_marine:
                    if "daily" in res and "time" in res["daily"]:
                        min_days = min(min_days, len(res["daily"]["time"]))

                if min_days == expected_days:
                    self.checkpoint.mark_success(work_id)
                else:
                    self.checkpoint.mark_failure(work_id, "Pending tail")
                print(f"Completed {work_id} up to {min_days} days")
                current_start = current_end + timedelta(days=1)
                
        self._commit_staged()

    def update_recent(self, sites: list, max_runtime_minutes: int, max_calls: int):
        self.restore()
        start_time = datetime.now()
        calls_made = 0
        batches = [sites[i:i+8] for i in range(0, len(sites), 8)]
        
        today_str = get_colombo_now().strftime("%Y-%m-%d")
        past_date = (get_colombo_now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        for i, batch in enumerate(batches):
            work_id = f"update_{today_str}_batch_{i}"
            if self.checkpoint.is_completed(work_id):
                continue
                
            if (datetime.now() - start_time).total_seconds() / 60 > max_runtime_minutes:
                self._commit_staged()
                return

            cost_atmos = self.worker._estimate_cost(len(batch), 1, len(ATMOSPHERE_DAILY), 14)
            if calls_made + cost_atmos > max_calls:
                self._commit_staged()
                return

            params_atmos = {
                "latitude": ",".join(str(s.lat_land) for s in batch),
                "longitude": ",".join(str(s.lon_land) for s in batch),
                "models": "ecmwf_ifs025", "daily": ",".join(ATMOSPHERE_DAILY),
                "timezone": TIMEZONE, "past_days": 7, "forecast_days": 7,
                "temperature_unit": "celsius", "wind_speed_unit": "ms", "precipitation_unit": "mm"
            }
            try:
                res_atmos = self.worker.fetch_batch(f"atmos_{work_id}", OPENMETEO_FORECAST_URL, params_atmos, len(batch), 14, past_date, ATMOSPHERE_DAILY)
                calls_made += cost_atmos
                df_atmos = self._parse_to_df(res_atmos, batch, "ecmwf_ifs025", "weather_recent")
                
                df_recent = df_atmos[df_atmos["date_local"] < today_str].copy()
                df_forecast = df_atmos[df_atmos["date_local"] >= today_str].copy()
                if not df_recent.empty:
                    self._save_parquet(df_recent, "weather_recent", WEATHER_SCHEMA)
                if not df_forecast.empty:
                    # snapshot_id is already the date_local. Wait, forecast snapshot id should be today's date.
                    df_forecast["snapshot_id"] = today_str
                    self._save_parquet(df_forecast, "weather_forecasts", WEATHER_SCHEMA)
            except Exception as e:
                self.checkpoint.mark_failure(work_id, str(e))
                self._commit_staged()
                return
                
            cost_marine = self.worker._estimate_cost(len(batch), 1, len(MARINE_DAILY), 14)
            if calls_made + cost_marine > max_calls:
                self._commit_staged()
                return

            params_marine = {
                "latitude": ",".join(str(s.lat_sea) for s in batch),
                "longitude": ",".join(str(s.lon_sea) for s in batch),
                "models": "ecmwf_wam", "daily": ",".join(MARINE_DAILY),
                "timezone": TIMEZONE, "past_days": 7, "forecast_days": 7
            }
            try:
                res_marine = self.worker.fetch_batch(f"marine_{work_id}", OPENMETEO_MARINE_FORECAST_URL, params_marine, len(batch), 14, past_date, MARINE_DAILY)
                calls_made += cost_marine
                df_marine = self._parse_to_df(res_marine, batch, "ecmwf_wam", "marine_recent")
                
                df_recent = df_marine[df_marine["date_local"] < today_str].copy()
                df_forecast = df_marine[df_marine["date_local"] >= today_str].copy()
                if not df_recent.empty:
                    self._save_parquet(df_recent, "marine_recent", MARINE_SCHEMA)
                if not df_forecast.empty:
                    df_forecast["snapshot_id"] = today_str
                    self._save_parquet(df_forecast, "marine_forecasts", MARINE_SCHEMA)
            except Exception as e:
                self.checkpoint.mark_failure(work_id, str(e))
                self._commit_staged()
                return
                
            self.checkpoint.mark_success(work_id)
            
        self._commit_staged()

    def _parse_to_df(self, results, batch, model_name, record_type) -> pd.DataFrame:
        rows = []
        for res, site in zip(results, batch):
            if "daily" not in res: continue
            daily = res["daily"]
            time_arr = daily["time"]
            for i, t in enumerate(time_arr):
                row = {
                    "site_id": site.site_id,
                    "date_local": t,
                    "model": model_name,
                    "snapshot_id": "historical" if "reanalysis" in record_type or "recent" in record_type else t,
                }
                for k, v in daily.items():
                    if k != "time":
                        row[k] = v[i]
                rows.append(row)
        return pd.DataFrame(rows)

    def _save_parquet(self, df: pd.DataFrame, record_type: str, schema):
        if df.empty: return
        df["year"] = df["date_local"].str[:4]
        for year, group in df.groupby("year"):
            path = Path(DATA_DIR) / record_type / f"year={year}" / f"{record_type.split('_')[0]}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            
            save_df = group.drop(columns=["year"])
            if path.exists():
                existing = pd.read_parquet(path)
                save_df = pd.concat([existing, save_df]).drop_duplicates(subset=["site_id", "date_local", "model", "snapshot_id"], keep="last")
            
            save_df = save_df.sort_values(["site_id", "date_local", "model", "snapshot_id"])
            write_parquet(save_df, str(path), schema=schema)
            self.files_to_upload.add((record_type, str(path), year))

    def _commit_staged(self):
        if not self.files_to_upload:
            return
        try:
            operations = []
            for record_type, file_path, year in self.files_to_upload:
                operations.append(CommitOperationAdd(
                    path_in_repo=f"data/{record_type}/year={year}/{record_type.split('_')[0]}.parquet",
                    path_or_fileobj=file_path
                ))
            
            print(f"Creating commit on {self.repo_id} with parent {self.parent_commit}...")
            self.api.create_commit(
                repo_id=self.repo_id,
                repo_type="dataset",
                operations=operations,
                commit_message="Automated data update",
                parent_commit=self.parent_commit
            )
            print("Data published successfully.")
            self.files_to_upload.clear()
        except Exception as e:
            print(f"Failed to publish to HF: {e}")
            raise e
