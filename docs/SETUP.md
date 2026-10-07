# Setup Guide

## 1. Local Environment Setup
Requires Python 3.11+.

### Windows PowerShell
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## 2. Hugging Face Authentication
Log in via the huggingface_hub CLI to cache your token locally:
```bash
python -c "from huggingface_hub import HfApi; print(HfApi().whoami())"
```

## 3. GitHub Actions Configuration
To enable the automated pipelines, configure the following in your GitHub repository:

**Secrets:**
- `HF_TOKEN`: Fine-grained token with read/write access to your HF dataset repository.

**Variables:**
- `HF_REPO_ID`: The target dataset ID.
- `AUTOMATION_ENABLED`: Set to `true` to enable daily updates and reconciliation.
- `BACKFILL_ENABLED`: Set to `true` to enable hourly backfill processing.

*Note: Code and workflows go to GitHub. The Parquet data goes directly to Hugging Face.*

## 4. Execution Commands
1. Offline tests: `python -m pytest tests/`
2. Validate catalogue: `python -m sl_fisheries_weather verify-sites`
3. Dry run/pilot: `python -m sl_fisheries_weather pilot --start 2010-01-01 --end 2010-01-14 --include-recent`
4. Setup HF repository: `python -m sl_fisheries_weather init-hf`
5. Small backfill test: `python -m sl_fisheries_weather backfill --start 2010-01-01 --max-runtime-minutes 35 --max-estimated-calls 200`
6. Push code to GitHub and enable repository variable flags.
