# sl-fisheries-weather

A daily Sri Lankan fishing-harbour weather and marine dataset from 2010-01-01 onward. The dataset is automatically fetched and updated via GitHub Actions and published directly to Hugging Face.

## Dataset Structure
The authoritative raw evidence and data products are pushed to Hugging Face:
- `metadata/sites.csv`: 16 checked logic site IDs with mapping links.
- `metadata/schema.json`, `manifest.json`, `coverage.json`.
- `data/weather_reanalysis/`, `data/marine_reanalysis/`: Historical atmosphere and marine features.
- `data/weather_recent/`, `data/marine_recent/`: Recent data models.
- `data/weather_forecasts/`, `data/marine_forecasts/`: Immutable forecast snapshots.

## Features
- **Idempotent Data Collection**: Retrieves 14-day windows with atomic local storage.
- **Hugging Face Integration**: Synchronizes local state by downloading remote shards before appending to prevent data loss. Uploads automatically.
- **Strict Validation**: Validates continuity, prefixes, and physical bounds. Trims unavailable trailing tails as pending.
- **Budget Control**: Adheres to strict per-minute/hour/day/month Open-Meteo limits.
- **Strict Site Verification**: Harbour coordinates validated deeply against Wikipedia URLs and valid spatial ranges.

## Repository Structure
```text
sl-fisheries-weather/
├── .github/
│   └── workflows/              # GitHub Actions CI and automation workflows
│       ├── backfill.yml        # Hourly historical backfill workflow
│       ├── update_weather.yml  # Daily recent & forecast update workflow
│       ├── reconcile.yml       # Monthly reconciliation workflow
│       └── ci.yml              # Offline test suite on push/PR
├── docs/                       # Project documentation and specifications
│   ├── SETUP.md                # Quickstart setup instructions
│   ├── SETUP_GUIDE.md          # Comprehensive account and pipeline runbook
│   └── PROMPT.txt              # Specification prompt and data contract
├── scripts/                    # Maintenance and operational utility scripts
│   └── fix_2026_shards.py      # Utility patch for historical shard repair
├── sl_fisheries_weather/       # Core Python package
│   ├── backfill/               # Batch orchestration and worker routines
│   ├── budget/                 # Open-Meteo rolling rate limiter and ledger
│   ├── catalogue/              # 16-site fishery harbour registry & CSV
│   ├── client/                 # Paced HTTP client with exponential retry
│   ├── manifest/               # Durable checkpoint state manager
│   ├── parquet_store/          # Strict Arrow schemas and atomic writers
│   ├── publish_hf/             # Hugging Face dataset publishing utilities
│   ├── validation/             # Strict prefix, continuity, and bounds checks
│   ├── cli.py                  # CLI command implementations
│   └── config.py               # Shared constants, URLs, and budget limits
├── tests/                      # Offline unit and integration test suite
├── .env.example                # Environment variable configuration template
├── .gitignore                  # Git ignore rules
├── pyproject.toml              # Build and package metadata
├── IMPLEMENTATION_REPORT.md    # Verification and acceptance audit report
└── README.md                   # Project overview
```

## Available Commands
Run using the virtual environment:
```powershell
python -m sl_fisheries_weather <command>
```

Commands:
- `doctor`: Checks Python version, dependencies, Colombo timezone, and connectivity.
- `verify-sites`: Validates the 16-site catalogue against spatial bounds and registry standards.
- `pilot`: Fetches a small batch into `data/pilot` for isolated validation.
- `init-hf`: Initializes repository cards and metadata on Hugging Face safely.
- `backfill`: Runs historical reanalysis data collection for specified windows.
- `update`: Refreshes recent model data and ECMWF forecast vintages.
- `publish`: Publishes staged Parquet files and metadata to Hugging Face.
- `validate`: Deeply checks dataset shards for schema compliance, continuity, and uniqueness.
- `status`: Reports current budget ledger sums, checkpoint progress, and local shard counts.
- `reconcile`: Revisits older recent reanalysis data for revisions.

## Documentation
- [Quickstart Guide](docs/SETUP.md): Step-by-step developer setup and execution commands.
- [Comprehensive Runbook](docs/SETUP_GUIDE.md): Detailed accounts, token scope, and operational runbook.
- [Implementation Report](IMPLEMENTATION_REPORT.md): Audit report of tests, fixes, and dataset coverage.

## License
- **Code**: MIT License
- **Dataset**: CC BY 4.0 (Open-Meteo attribution required)
