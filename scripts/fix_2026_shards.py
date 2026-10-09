import os
import pandas as pd
from pathlib import Path
from huggingface_hub import HfApi, CommitOperationAdd
from dotenv import load_dotenv

load_dotenv()
repo_id = os.environ.get("HF_REPO_ID", "tharinduperera/sl-fisheries-weather-daily")
api = HfApi()

def fix_shards():
    info = api.dataset_info(repo_id)
    parent_commit = info.sha
    print(f"Parent commit: {parent_commit}")
    
    operations = []
    
    # Download and fix weather_reanalysis 2026
    weather_file = "data/weather_reanalysis/year=2026/weather.parquet"
    try:
        w_path = api.hf_hub_download(repo_id=repo_id, repo_type="dataset", filename=weather_file)
        df_w = pd.read_parquet(w_path)
        # remove rows with missing core values
        valid_w = df_w.dropna(subset=["precipitation_sum", "temperature_2m_mean"])
        if len(valid_w) < len(df_w):
            print(f"Weather: Dropping {len(df_w) - len(valid_w)} invalid rows.")
            fixed_w_path = "fixed_weather.parquet"
            valid_w.to_parquet(fixed_w_path)
            operations.append(CommitOperationAdd(path_in_repo=weather_file, path_or_fileobj=fixed_w_path))
    except Exception as e:
        print(f"No weather file found or error: {e}")

    # Download and fix marine_reanalysis 2026
    marine_file = "data/marine_reanalysis/year=2026/marine.parquet"
    try:
        m_path = api.hf_hub_download(repo_id=repo_id, repo_type="dataset", filename=marine_file)
        df_m = pd.read_parquet(m_path)
        valid_m = df_m.dropna(subset=["wave_height_max", "wave_period_max", "wave_direction_dominant"])
        if len(valid_m) < len(df_m):
            print(f"Marine: Dropping {len(df_m) - len(valid_m)} invalid rows.")
            fixed_m_path = "fixed_marine.parquet"
            valid_m.to_parquet(fixed_m_path)
            operations.append(CommitOperationAdd(path_in_repo=marine_file, path_or_fileobj=fixed_m_path))
    except Exception as e:
        print(f"No marine file found or error: {e}")
        
    if operations:
        api.create_commit(
            repo_id=repo_id,
            repo_type="dataset",
            operations=operations,
            commit_message="Fix 2026 shards by removing unavailable placeholders",
            parent_commit=parent_commit
        )
        print("Fixed shards pushed to HF.")
    else:
        print("No operations needed.")

if __name__ == "__main__":
    fix_shards()
