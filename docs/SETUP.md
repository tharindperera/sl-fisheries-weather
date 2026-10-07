# Setup Guide

## 1. Local Environment Setup
Requires Python 3.11+.

### Windows PowerShell
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### Ubuntu / macOS
```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

## 2. Hugging Face Authentication
Log in via the huggingface_hub CLI to cache your token locally:
```bash
hf auth login
hf auth whoami
```

Alternatively, set the token in your environment or via GitHub Secrets.
Dataset ID defaults to `tharinduperera/sl-fisheries-weather-daily`. Customize this via `.env`:
```dotenv
HF_REPO_ID=your_hf_username/sl-fisheries-weather-daily
```

## 3. GitHub Actions Configuration
To enable the automated pipelines, configure the following in your GitHub repository:

**Secrets:**
- `HF_TOKEN`: Fine-grained token with read/write access to your HF dataset repository.

**Variables:**
- `HF_REPO_ID`: The target dataset ID.
- `AUTOMATION_ENABLED`: Set to `true` to enable daily updates and reconciliation.
- `BACKFILL_ENABLED`: Set to `true` to enable hourly backfill processing.

## 4. Initializing the Dataset
Once the pilot is tested, initialize the Hugging Face dataset (ensure your token has appropriate permissions, or create the repo manually first):
```bash
python -m sl_fisheries_weather init-hf --create
```

## 5. Execution Order
1. Offline tests: `pytest tests/`
2. Validate catalogue: `python -m sl_fisheries_weather verify-sites`
3. Dry run/pilot: `python -m sl_fisheries_weather pilot --start 2010-01-01 --end 2010-01-14 --include-recent`
4. Setup HF repository: `python -m sl_fisheries_weather init-hf`
5. Small backfill test: `python -m sl_fisheries_weather backfill --start 2010-01-01 --max-runtime-minutes 35`
6. Push to GitHub and enable workflows.
