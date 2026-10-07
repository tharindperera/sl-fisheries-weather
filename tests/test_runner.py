import pytest
import responses
import pandas as pd
from pathlib import Path
from sl_fisheries_weather.backfill.runner import Runner
from sl_fisheries_weather.backfill.worker import Worker
from sl_fisheries_weather.budget.ledger import Ledger
from sl_fisheries_weather.manifest.state import CheckpointManager
from sl_fisheries_weather.catalogue.sites import load_registry

@responses.activate
def test_runner_backfill(tmp_path, mocker):
    mocker.patch("sl_fisheries_weather.config.DATA_DIR", str(tmp_path))
    mocker.patch("sl_fisheries_weather.backfill.runner.DATA_DIR", str(tmp_path))
    mocker.patch("sl_fisheries_weather.manifest.state.DATA_DIR", str(tmp_path))
    mocker.patch("sl_fisheries_weather.budget.ledger.DATA_DIR", str(tmp_path))
    
    # Mock huggingface API to not actually upload or hit network
    mocker.patch("sl_fisheries_weather.backfill.runner.HfApi")
    
    ledger = Ledger({"minute": 100, "hour": 1000, "day": 5000, "month": 150000})
    worker = Worker(ledger, str(tmp_path))
    worker.client.min_delay = 0  # Speed up tests
    checkpoint = CheckpointManager(filename="test_checkpoint.json")
    
    runner = Runner(worker, checkpoint, "test/repo")
    sites = load_registry()[:2] # Just 2 sites for speed
    
    # Mock Open-Meteo responses
    # Atmosphere
    responses.add(
        responses.GET,
        "https://archive-api.open-meteo.com/v1/archive",
        json=[
            {
                "latitude": 7.0, "longitude": 79.8,
                "daily": {
                    "time": ["2010-01-01", "2010-01-02"],
                    "precipitation_sum": [0.0, 1.0],
                    "precipitation_hours": [0.0, 1.0],
                    "wind_speed_10m_max": [5.0, 6.0],
                    "wind_speed_10m_mean": [3.0, 4.0],
                    "wind_direction_10m_dominant": [180.0, 190.0],
                    "temperature_2m_mean": [27.0, 28.0],
                    "temperature_2m_max": [30.0, 31.0],
                    "temperature_2m_min": [24.0, 25.0],
                    "relative_humidity_2m_mean": [80.0, 85.0],
                    "pressure_msl_mean": [1010.0, 1012.0]
                }
            },
            {
                "latitude": 6.5, "longitude": 80.0,
                "daily": {
                    "time": ["2010-01-01", "2010-01-02"],
                    "precipitation_sum": [0.0, 1.0],
                    "precipitation_hours": [0.0, 1.0],
                    "wind_speed_10m_max": [5.0, 6.0],
                    "wind_speed_10m_mean": [3.0, 4.0],
                    "wind_direction_10m_dominant": [180.0, 190.0],
                    "temperature_2m_mean": [27.0, 28.0],
                    "temperature_2m_max": [30.0, 31.0],
                    "temperature_2m_min": [24.0, 25.0],
                    "relative_humidity_2m_mean": [80.0, 85.0],
                    "pressure_msl_mean": [1010.0, 1012.0]
                }
            }
        ],
        status=200
    )
    
    # Marine
    responses.add(
        responses.GET,
        "https://marine-api.open-meteo.com/v1/marine",
        json=[
            {
                "latitude": 6.9, "longitude": 79.8,
                "daily": {
                    "time": ["2010-01-01", "2010-01-02"],
                    "wave_height_max": [1.0, 1.5],
                    "wave_period_max": [5.0, 6.0],
                    "wave_direction_dominant": [180.0, 190.0]
                }
            },
            {
                "latitude": 6.4, "longitude": 79.9,
                "daily": {
                    "time": ["2010-01-01", "2010-01-02"],
                    "wave_height_max": [1.0, 1.5],
                    "wave_period_max": [5.0, 6.0],
                    "wave_direction_dominant": [180.0, 190.0]
                }
            }
        ],
        status=200
    )
    
    runner.backfill(sites, "2010-01-01", "2010-01-02", max_runtime_minutes=1, max_calls=100)
    
    # Check that parquet files were generated
    weather_path = tmp_path / "weather_reanalysis" / "year=2010" / "weather.parquet"
    marine_path = tmp_path / "marine_reanalysis" / "year=2010" / "marine.parquet"
    
    assert weather_path.exists()
    assert marine_path.exists()
    
    # Read and verify content
    df_weather = pd.read_parquet(weather_path)
    assert len(df_weather) == 4 # 2 sites * 2 days
    assert "precipitation_sum" in df_weather.columns
    
    df_marine = pd.read_parquet(marine_path)
    assert len(df_marine) == 4 # 2 sites * 2 days
    assert "wave_height_max" in df_marine.columns
    
    # Check durable state
    assert (tmp_path / "test_checkpoint.json").exists()
    assert checkpoint.is_completed("backfill_2010-01-01_2010-01-02_batch_0") is True
