import argparse
import sys
from sl_fisheries_weather.catalogue.sites import load_registry

def cmd_doctor(args):
    import os
    import sys
    from zoneinfo import ZoneInfo
    from dotenv import load_dotenv
    print("Running doctor...")
    print(f"Python version: {sys.version.split()[0]} ({sys.platform})")
    assert sys.version_info >= (3, 11), "Python 3.11+ required"

    print("Checking dependencies...")
    import pandas
    import requests
    import pyarrow
    import duckdb
    import huggingface_hub
    from sl_fisheries_weather import config
    print("Dependencies OK (pandas, requests, pyarrow, duckdb, huggingface_hub).")

    # Timezone check
    tz = ZoneInfo("Asia/Colombo")
    print(f"Timezone check OK: {tz}")

    # Sites registry check
    sites = load_registry()
    print(f"Site registry check OK: {len(sites)} sites loaded.")

    # Configuration & Auth check
    load_dotenv()
    repo_id = os.environ.get("HF_REPO_ID", "tharinduperera/sl-fisheries-weather-daily")
    hf_token = os.environ.get("HF_TOKEN")
    print(f"Target Hugging Face repository: {repo_id}")
    if hf_token:
        print("HF_TOKEN found in environment (present, hidden).")
    else:
        print("Notice: HF_TOKEN not set in environment. Checking local cached HF login...")
    try:
        api = huggingface_hub.HfApi()
        who = api.whoami()
        print(f"Hugging Face authenticated as: {who.get('name', 'Unknown')}")
    except Exception as e:
        print(f"Hugging Face auth note: {e}")

    # Network / Open-Meteo check
    print("Testing Open-Meteo connectivity...")
    try:
        r = requests.get("https://archive-api.open-meteo.com/v1/archive?latitude=6.9&longitude=79.8&start_date=2010-01-01&end_date=2010-01-02&models=era5&daily=temperature_2m_mean&timezone=Asia/Colombo", timeout=15)
        if r.status_code == 200:
            print("Open-Meteo connectivity OK (HTTP 200).")
        else:
            print(f"Open-Meteo responded with status {r.status_code}")
    except Exception as e:
        print(f"Open-Meteo connectivity warning: {e}")

    print("Doctor checks passed.")

def cmd_verify_sites(args):
    print("Verifying sites...")
    sites = load_registry()
    print(f"Loaded {len(sites)} sites from registry.")
    assert len(sites) == 16, "Expected 16 sites."
    
    errors = []
    for s in sites:
        if not (5.9 <= s.lat_land <= 9.9 and 79.5 <= s.lon_land <= 81.9):
            errors.append(f"{s.site_id}: lat/lon land {s.lat_land},{s.lon_land} out of bounds")
        if not (5.9 <= s.lat_sea <= 9.9 and 79.5 <= s.lon_sea <= 81.9):
            errors.append(f"{s.site_id}: lat/lon sea {s.lat_sea},{s.lon_sea} out of bounds")
        if s.verification_status not in ["verified", "needs_review"]:
            errors.append(f"{s.site_id}: Invalid status {s.verification_status}")
            
        if s.verification_status == "verified" and "wikipedia.org/wiki/" in s.coordinate_source_url:
            if not any(word in s.coordinate_source_url.lower() for word in ["harbour", "fishery"]):
                errors.append(f"{s.site_id}: verified but generic Wikipedia URL {s.coordinate_source_url}")
                
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        import sys
        sys.exit(1)
        
    print("Sites verified successfully.")

def cmd_pilot(args):
    import json
    from pathlib import Path
    from datetime import datetime, timedelta
    from sl_fisheries_weather.config import (
        DATA_DIR, ATMOSPHERE_DAILY, MARINE_DAILY, TIMEZONE,
        OPENMETEO_ARCHIVE_URL, OPENMETEO_MARINE_ARCHIVE_URL,
        OPENMETEO_FORECAST_URL, OPENMETEO_MARINE_FORECAST_URL
    )
    from sl_fisheries_weather.budget.ledger import Ledger
    from sl_fisheries_weather.backfill.worker import Worker

    print(f"Running pilot from {args.start} to {args.end}...")
    pilot_dir = Path(DATA_DIR) / "pilot"
    pilot_dir.mkdir(parents=True, exist_ok=True)
    
    sites = load_registry()
    ledger = Ledger({
        "minute": 100, "hour": 1000, "day": 5000, "month": 150000
    })
    worker = Worker(ledger, str(pilot_dir))
    
    # Batch in 8s
    batches = [sites[i:i+8] for i in range(0, len(sites), 8)]
    
    expected_days = (datetime.strptime(args.end, "%Y-%m-%d") - datetime.strptime(args.start, "%Y-%m-%d")).days + 1

    for i, batch in enumerate(batches):
        print(f"Batch {i+1}/{len(batches)}")
        # Historical Atmosphere
        params_atmos = {
            "latitude": ",".join(str(s.lat_land) for s in batch),
            "longitude": ",".join(str(s.lon_land) for s in batch),
            "start_date": args.start,
            "end_date": args.end,
            "models": "era5",
            "daily": ",".join(ATMOSPHERE_DAILY),
            "timezone": TIMEZONE,
            "cell_selection": "land",
            "temperature_unit": "celsius",
            "wind_speed_unit": "ms",
            "precipitation_unit": "mm"
        }
        print("Fetching historical atmosphere...")
        res_atmos = worker.fetch_batch(f"pilot_atmos_{i}", OPENMETEO_ARCHIVE_URL, params_atmos, len(batch), expected_days, args.start, ATMOSPHERE_DAILY)
        with open(pilot_dir / f"pilot_atmos_{i}.json", "w") as f:
            json.dump(res_atmos, f)

        # Historical Marine
        params_marine = {
            "latitude": ",".join(str(s.lat_sea) for s in batch),
            "longitude": ",".join(str(s.lon_sea) for s in batch),
            "start_date": args.start,
            "end_date": args.end,
            "models": "era5_ocean",
            "daily": ",".join(MARINE_DAILY),
            "timezone": TIMEZONE,
            "cell_selection": "sea"
        }
        print("Fetching historical marine...")
        res_marine = worker.fetch_batch(f"pilot_marine_{i}", OPENMETEO_MARINE_ARCHIVE_URL, params_marine, len(batch), expected_days, args.start, MARINE_DAILY)
        with open(pilot_dir / f"pilot_marine_{i}.json", "w") as f:
            json.dump(res_marine, f)
            
        if args.include_recent:
            print("Fetching recent/forecast combinations...")
            # Recent/forecast use 7 days past to 7 days future. For pilot, let's just make one call.
            # wait, prompt says: "Use seven past days plus seven forecast days for the routine recent/forecast request. The forecast span includes today."
            # We can use past_days=7, forecast_days=7
            params_recent_atmos = {
                "latitude": ",".join(str(s.lat_land) for s in batch),
                "longitude": ",".join(str(s.lon_land) for s in batch),
                "models": "ecmwf_ifs025",
                "daily": ",".join(ATMOSPHERE_DAILY),
                "timezone": TIMEZONE,
                "past_days": 7,
                "forecast_days": 7,
                "temperature_unit": "celsius",
                "wind_speed_unit": "ms",
                "precipitation_unit": "mm"
            }
            past_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            res_rec_atmos = worker.fetch_batch(f"pilot_recent_atmos_{i}", OPENMETEO_FORECAST_URL, params_recent_atmos, len(batch), 14, past_date, ATMOSPHERE_DAILY)
            with open(pilot_dir / f"pilot_recent_atmos_{i}.json", "w") as f:
                json.dump(res_rec_atmos, f)
                
            params_recent_marine = {
                "latitude": ",".join(str(s.lat_sea) for s in batch),
                "longitude": ",".join(str(s.lon_sea) for s in batch),
                "models": "ecmwf_wam",
                "daily": ",".join(MARINE_DAILY),
                "timezone": TIMEZONE,
                "past_days": 7,
                "forecast_days": 7
            }
            res_rec_marine = worker.fetch_batch(f"pilot_recent_marine_{i}", OPENMETEO_MARINE_FORECAST_URL, params_recent_marine, len(batch), 14, past_date, MARINE_DAILY)
            with open(pilot_dir / f"pilot_recent_marine_{i}.json", "w") as f:
                json.dump(res_rec_marine, f)
            
    print("Pilot completed successfully.")

def cmd_init_hf(args):
    import os
    from dotenv import load_dotenv
    from sl_fisheries_weather.publish_hf.publisher import Publisher
    
    load_dotenv()
    repo_id = os.environ.get("HF_REPO_ID", "tharinduperera/sl-fisheries-weather-daily")
    print(f"Initializing HF repository: {repo_id}...")
    
    pub = Publisher(repo_id)
    pub.init_hf(create=args.create)

def _get_runner_setup():
    import os
    from dotenv import load_dotenv
    from sl_fisheries_weather.budget.ledger import Ledger
    from sl_fisheries_weather.backfill.worker import Worker
    from sl_fisheries_weather.backfill.runner import Runner
    from sl_fisheries_weather.manifest.state import CheckpointManager
    from sl_fisheries_weather.config import DATA_DIR, DEFAULT_LEDGER_LIMITS
    
    load_dotenv()
    repo_id = os.environ.get("HF_REPO_ID", "tharinduperera/sl-fisheries-weather-daily")
    sites = load_registry()
    ledger = Ledger(DEFAULT_LEDGER_LIMITS)
    worker = Worker(ledger, DATA_DIR)
    checkpoint = CheckpointManager()
    
    return Runner(worker, checkpoint, repo_id), sites

def cmd_backfill(args):
    from datetime import datetime
    print(f"Running backfill from {args.start} with limit {args.max_runtime_minutes} mins, {args.max_estimated_calls} calls...")
    runner, sites = _get_runner_setup()
    end_date = datetime.now().strftime("%Y-%m-%d")
    runner.backfill(sites, args.start, end_date, args.max_runtime_minutes, args.max_estimated_calls)
    print("Backfill completed or paused cleanly.")

def cmd_update(args):
    from datetime import datetime, timedelta
    print(f"Running update with limit {args.max_runtime_minutes} mins...")
    runner, sites = _get_runner_setup()
    end_date = datetime.now()
    start_date = (end_date - timedelta(days=14)).strftime("%Y-%m-%d")
    print(f"Refreshing historical reanalysis for past 14 days ({start_date} to {end_date.strftime('%Y-%m-%d')})...")
    runner.backfill(sites, start_date, end_date.strftime("%Y-%m-%d"), args.max_runtime_minutes, 1000)
    print("Fetching recent and forecast products from ECMWF...")
    runner.update_recent(sites, args.max_runtime_minutes, 1000)
    print("Update completed.")

def cmd_publish(args):
    print("Publishing to Hugging Face...")
    runner, _ = _get_runner_setup()
    from sl_fisheries_weather.config import DATA_DIR
    from pathlib import Path
    data_dir = Path(DATA_DIR)
    runner.files_to_upload.clear()
    for p in data_dir.rglob("*.parquet"):
        record_type = p.parent.parent.name
        year = p.parent.name.split("=")[1]
        runner.files_to_upload.add((record_type, str(p), year))
    
    if not runner.files_to_upload:
        print("No files to publish.")
        return
    runner._commit_staged()

def cmd_validate(args):
    print("Validating datasets...")
    from sl_fisheries_weather.config import DATA_DIR
    from pathlib import Path
    import pandas as pd
    from sl_fisheries_weather.parquet_store.schema import WEATHER_SCHEMA, MARINE_SCHEMA
    
    data_dir = Path(DATA_DIR)
    parquet_files = list(data_dir.rglob("*.parquet"))
    
    if not parquet_files:
        print("Empty dataset. Validation passed.")
        return
        
    for p in parquet_files:
        try:
            df = pd.read_parquet(p)
            print(f"{p}: {len(df)} rows OK")
            
            # Unrelated readable Parquet must fail
            if "site_id" not in df.columns or "date_local" not in df.columns:
                raise ValueError("Missing core columns site_id or date_local. Unrelated parquet.")
            
            # Check schema
            if "weather" in p.name or "weather" in p.parent.parent.name:
                expected_cols = set(WEATHER_SCHEMA.names)
            else:
                expected_cols = set(MARINE_SCHEMA.names)
                
            actual_cols = set(df.columns)
            if not expected_cols.issubset(actual_cols):
                raise ValueError(f"Schema mismatch: missing {expected_cols - actual_cols}")
            
            # per-site/model uniqueness
            if df.duplicated(subset=["site_id", "date_local", "model", "snapshot_id"]).any():
                raise ValueError("Duplicate rows found based on primary keys.")
                
            # Shard year check
            year = p.parent.name.split("=")[1]
            if not (df["date_local"].str[:4] == year).all():
                raise ValueError(f"Rows found outside of shard year {year}")
                
        except Exception as e:
            print(f"Error validating {p}: {e}")
            import sys
            sys.exit(1)
            
    print("Validation passed.")

def cmd_status(args):
    print("Checking dataset status...")
    from pathlib import Path
    from sl_fisheries_weather.config import DATA_DIR
    runner, sites = _get_runner_setup()
    
    print("\n--- Budget Ledger Status ---")
    print(f"Minute calls: {runner.worker.ledger._get_sum('minute_calls')} / {runner.worker.ledger.limits.get('minute')}")
    print(f"Hour calls:   {runner.worker.ledger._get_sum('hour_calls')} / {runner.worker.ledger.limits.get('hour')}")
    print(f"Day calls:    {runner.worker.ledger._get_sum('day_calls')} / {runner.worker.ledger.limits.get('day')}")
    print(f"Month calls:  {runner.worker.ledger._get_sum('month_calls')} / {runner.worker.ledger.limits.get('month')}")

    print("\n--- Checkpoint Status ---")
    all_checkpoints = runner.checkpoint.get_all()
    successes = [k for k, v in all_checkpoints.items() if v.get("status") == "success"]
    failures = [k for k, v in all_checkpoints.items() if v.get("status") == "failed"]
    print(f"Total recorded units: {len(all_checkpoints)}")
    print(f"Completed:            {len(successes)}")
    print(f"Failed / Pending:     {len(failures)}")

    print("\n--- Local Storage Status ---")
    data_dir = Path(DATA_DIR)
    parquet_files = list(data_dir.rglob("*.parquet"))
    print(f"Parquet files found:  {len(parquet_files)}")
    by_product = {}
    for p in parquet_files:
        product = p.parent.parent.name
        by_product[product] = by_product.get(product, 0) + 1
    for prod, count in sorted(by_product.items()):
        print(f"  {prod}: {count} shards")

def cmd_reconcile(args):
    from datetime import datetime, timedelta
    print(f"Reconciling past {args.lookback_days} days...")
    runner, sites = _get_runner_setup()
    end_date = datetime.now()
    start_date = (end_date - timedelta(days=args.lookback_days)).strftime("%Y-%m-%d")
    runner.backfill(sites, start_date, end_date.strftime("%Y-%m-%d"), args.max_runtime_minutes, 1000000)
    print("Reconcile completed.")

def main():
    parser = argparse.ArgumentParser(description="SL Fisheries Weather CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_doctor = subparsers.add_parser("doctor", help="Check system and dependencies")
    p_doctor.set_defaults(func=cmd_doctor)

    p_verify = subparsers.add_parser("verify-sites", help="Verify the site registry")
    p_verify.set_defaults(func=cmd_verify_sites)

    p_pilot = subparsers.add_parser("pilot", help="Run a small pilot collection")
    p_pilot.add_argument("--start", required=True)
    p_pilot.add_argument("--end", required=True)
    p_pilot.add_argument("--include-recent", action="store_true")
    p_pilot.set_defaults(func=cmd_pilot)

    p_init = subparsers.add_parser("init-hf", help="Initialize Hugging Face repository")
    p_init.add_argument("--create", action="store_true", help="Create the repository if it doesn't exist")
    p_init.set_defaults(func=cmd_init_hf)

    p_backfill = subparsers.add_parser("backfill", help="Run historical backfill")
    p_backfill.add_argument("--start", required=True)
    p_backfill.add_argument("--max-runtime-minutes", type=int, default=35)
    p_backfill.add_argument("--max-estimated-calls", type=int, default=750)
    p_backfill.set_defaults(func=cmd_backfill)

    p_update = subparsers.add_parser("update", help="Run daily update")
    p_update.add_argument("--max-runtime-minutes", type=int, default=35)
    p_update.set_defaults(func=cmd_update)

    p_publish = subparsers.add_parser("publish", help="Publish staged data")
    p_publish.set_defaults(func=cmd_publish)

    p_validate = subparsers.add_parser("validate", help="Validate data")
    p_validate.add_argument("--all", action="store_true")
    p_validate.set_defaults(func=cmd_validate)

    p_status = subparsers.add_parser("status", help="Check status")
    p_status.set_defaults(func=cmd_status)

    p_reconcile = subparsers.add_parser("reconcile", help="Reconcile data")
    p_reconcile.add_argument("--lookback-days", type=int, default=90)
    p_reconcile.add_argument("--max-runtime-minutes", type=int, default=35)
    p_reconcile.set_defaults(func=cmd_reconcile)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
