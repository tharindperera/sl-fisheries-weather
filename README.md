# sl-fisheries-weather

A daily Sri Lankan fishing-harbour weather and marine dataset from 2010-01-01 onward. The dataset is automatically fetched and updated via GitHub Actions and published directly to Hugging Face.

## Dataset Structure
The authoritative raw evidence and data products are pushed to Hugging Face:
- `metadata/sites.csv`: 16 checked logic site IDs with mapping links.
- `metadata/schema.json`, `manifest.json`, `coverage.json`.
- `data/weather_reanalysis/`, `data/marine_reanalysis/`: Historical atmosphere and marine features.

## Available Commands
Run using the virtual environment python:
`python -m sl_fisheries_weather <command>`

Commands:
- `doctor`: Checks dependencies and environment.
- `verify-sites`: Validates the site registry.
- `pilot`: Fetches a small batch into `data/pilot` for testing.
- `init-hf`: Initializes the Hugging Face repository metadata safely.
- `backfill`: Runs historical data collection for specified windows.
- `update`: Refreshes recent data and repairs eligible gaps.
- `publish`: Publishes staged files to HF.
- `validate`: Checks the validity of published datasets.
- `status`: Reports pending jobs and budgets.
- `reconcile`: Revisits older recent reanalysis data.

## Automated Scheduling
GitHub schedules run daily and hourly depending on enabled flags. See `docs/SETUP.md`.

## License
Code: MIT License
Dataset: CC BY 4.0 (Open-Meteo)
