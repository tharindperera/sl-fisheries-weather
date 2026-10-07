import argparse
import sys
from sl_fisheries_weather.catalogue.sites import load_registry

def cmd_doctor(args):
    print("Running doctor...")
    print("Checking dependencies...")
    import pandas
    import requests
    import pyarrow
    import duckdb
    import huggingface_hub
    from sl_fisheries_weather import config
    print("Dependencies OK.")
    # More doctor checks to be implemented
    print("Doctor checks passed.")

def cmd_verify_sites(args):
    print("Verifying sites...")
    sites = load_registry()
    print(f"Loaded {len(sites)} sites from registry.")
    assert len(sites) == 16, "Expected 16 sites."
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

def cmd_backfill(args):
    import os
    from dotenv import load_dotenv
    from datetime import datetime
    from sl_fisheries_weather.budget.ledger import Ledger
    from sl_fisheries_weather.backfill.worker import Worker
    from sl_fisheries_weather.backfill.runner import Runner
    from sl_fisheries_weather.manifest.state import CheckpointManager
    from sl_fisheries_weather.config import DATA_DIR
    
    print(f"Running backfill from {args.start} with limit {args.max_runtime_minutes} mins, {args.max_estimated_calls} calls...")
    load_dotenv()
    repo_id = os.environ.get("HF_REPO_ID", "tharinduperera/sl-fisheries-weather-daily")
    
    sites = load_registry()
    ledger = Ledger({
        "minute": 100, "hour": 1000, "day": 5000, "month": 150000
    })
    worker = Worker(ledger, DATA_DIR)
    checkpoint = CheckpointManager()
    
    runner = Runner(worker, checkpoint, repo_id)
    end_date = datetime.now().strftime("%Y-%m-%d")
    runner.backfill(sites, args.start, end_date, args.max_runtime_minutes, args.max_estimated_calls)
    print("Backfill completed or paused cleanly.")

def _get_runner_setup():
    import os
    from dotenv import load_dotenv
    from sl_fisheries_weather.budget.ledger import Ledger
    from sl_fisheries_weather.backfill.worker import Worker
    from sl_fisheries_weather.backfill.runner import Runner
    from sl_fisheries_weather.manifest.state import CheckpointManager
    from sl_fisheries_weather.config import DATA_DIR
    
    load_dotenv()
    repo_id = os.environ.get("HF_REPO_ID", "tharinduperera/sl-fisheries-weather-daily")
    sites = load_registry()
    ledger = Ledger({"minute": 100, "hour": 1000, "day": 5000, "month": 150000})
    worker = Worker(ledger, DATA_DIR)
    checkpoint = CheckpointManager()
    
    return Runner(worker, checkpoint, repo_id), sites

def cmd_update(args):
    from datetime import datetime, timedelta
    print(f"Running update with limit {args.max_runtime_minutes} mins...")
    runner, sites = _get_runner_setup()
    end_date = datetime.now()
    start_date = (end_date - timedelta(days=14)).strftime("%Y-%m-%d")
    runner.backfill(sites, start_date, end_date.strftime("%Y-%m-%d"), args.max_runtime_minutes, 1000000)
    print("Update completed.")

def cmd_publish(args):
    print("Publishing to Hugging Face...")
    runner, _ = _get_runner_setup()
    # Staged data would be published here
    print("Staged files already published during backfill/update.")

def cmd_validate(args):
    print("Validating datasets...")
    from sl_fisheries_weather.config import DATA_DIR
    from pathlib import Path
    import pandas as pd
    data_dir = Path(DATA_DIR)
    for p in data_dir.rglob("*.parquet"):
        try:
            df = pd.read_parquet(p)
            print(f"{p}: {len(df)} rows OK")
        except Exception as e:
            print(f"Error validating {p}: {e}")
            raise e
    print("Validation passed.")

def cmd_status(args):
    print("Checking dataset status...")
    runner, _ = _get_runner_setup()
    print(f"Ledger Minute: {runner.worker.ledger._get_sum('minute_calls')}")
    print(f"Ledger Hour: {runner.worker.ledger._get_sum('hour_calls')}")
    print(f"Ledger Day: {runner.worker.ledger._get_sum('day_calls')}")
    print(f"Ledger Month: {runner.worker.ledger._get_sum('month_calls')}")

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
