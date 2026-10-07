# sl-fisheries-weather

A daily Sri Lankan fishing-harbour weather and marine dataset from 2010-01-01 onward, with Hugging Face storage, resumable collection, GitHub Actions historical backfill and continuing daily updates.

## Project Structure
- `sl_fisheries_weather/`: Python package for fetching, validating, and publishing data.
- `catalogue/`: Contains the official registry of 16 verified sites.
- `data/`: Local storage for checkpoints, raw downloads, and parquet staged data.
- `tests/`: Offline tests.
- `.github/workflows/`: Automated GitHub Actions for CI, backfill, daily updates, and monthly reconciliation.

## Available Commands
Run using the virtual environment python:
`python -m sl_fisheries_weather <command>`

Commands:
- `doctor`: Checks dependencies and environment.
- `verify-sites`: Validates the site registry.
- `pilot`: Fetches a small batch into `data/pilot` for testing.
- `init-hf`: Initializes the Hugging Face repository metadata.
- `backfill`: Runs historical data collection.
- `update`: Refreshes recent data and repairs eligible gaps.
- `publish`: Uploads staged files to Hugging Face.
- `validate`: Checks the validity of published datasets.
- `status`: Reports coverage and pending jobs.
- `reconcile`: Revisits older recent reanalysis data.

## Automated Scheduling
GitHub schedules run daily and hourly depending on enabled flags. See `docs/SETUP.md` for more information on configuring scheduled runs and secrets.

## Reconciliation
The `reconcile` command looks back ~90 days and repairs older recent data. Scheduled to run monthly on the 1st day of the month via Actions.

## License
Code: MIT License
Dataset: CC BY 4.0 (Open-Meteo)
