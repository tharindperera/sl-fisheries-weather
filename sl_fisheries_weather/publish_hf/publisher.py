import os
import json
from pathlib import Path
from huggingface_hub import HfApi, DatasetCard
from sl_fisheries_weather.config import DATA_DIR
from sl_fisheries_weather.catalogue.sites import load_registry

class Publisher:
    def __init__(self, repo_id: str):
        self.repo_id = repo_id
        self.api = HfApi()

    def check_repo_exists(self) -> bool:
        try:
            self.api.dataset_info(self.repo_id)
            return True
        except Exception:
            return False

    def init_hf(self, create: bool = False):
        if not self.check_repo_exists():
            if create:
                print(f"Creating repository {self.repo_id}...")
                self.api.create_repo(repo_id=self.repo_id, repo_type="dataset", private=False)
            else:
                raise RuntimeError(
                    f"Dataset {self.repo_id} does not exist.\n"
                    "Please create it manually on Hugging Face, or run with --create if your token has permissions."
                )
                
        print(f"Initializing metadata in {self.repo_id}...")
        
        # We need to upload metadata/sites.csv
        sites_path = Path(__file__).parent.parent / "catalogue" / "registry.csv"
        
        # Initial empty coverage
        coverage = {"sites": {}}
        coverage_path = Path(DATA_DIR) / "coverage.json"
        coverage_path.parent.mkdir(parents=True, exist_ok=True)
        with coverage_path.open("w") as f:
            json.dump(coverage, f)
            
        # Initial empty manifest
        manifest = {"version": "1.0", "checkpoints": {}}
        manifest_path = Path(DATA_DIR) / "manifest.json"
        with manifest_path.open("w") as f:
            json.dump(manifest, f)
            
        # Dataset card
        card_content = """
---
license: cc-by-4.0
task_categories:
- time-series-forecasting
tags:
- climate
- weather
- oceanography
- sri-lanka
---
# Sri Lankan Fisheries Weather and Marine Dataset

A daily Sri Lankan fishing-harbour weather and marine dataset from 2010-01-01 onward.

## Attribution
Data sourced from Open-Meteo (ERA5 and ECMWF).
License: CC BY 4.0 for the data.
"""
        card_path = Path(DATA_DIR) / "README.md"
        with card_path.open("w") as f:
            f.write(card_content)

        print("Uploading initial files if missing...")
        existing_files = self.api.list_repo_files(repo_id=self.repo_id, repo_type="dataset")
        
        if "metadata/sites.csv" not in existing_files:
            self.api.upload_file(
                path_or_fileobj=str(sites_path),
                path_in_repo="metadata/sites.csv",
                repo_id=self.repo_id,
                repo_type="dataset"
            )
        if "metadata/coverage.json" not in existing_files:
            self.api.upload_file(
                path_or_fileobj=str(coverage_path),
                path_in_repo="metadata/coverage.json",
                repo_id=self.repo_id,
                repo_type="dataset"
            )
        if "metadata/manifest.json" not in existing_files:
            self.api.upload_file(
                path_or_fileobj=str(manifest_path),
                path_in_repo="metadata/manifest.json",
                repo_id=self.repo_id,
                repo_type="dataset"
            )
        if "README.md" not in existing_files:
            self.api.upload_file(
                path_or_fileobj=str(card_path),
                path_in_repo="README.md",
                repo_id=self.repo_id,
                repo_type="dataset"
            )
        print("Initialization complete.")

    def publish_data(self, commit_message: str, operations: list):
        # operations should be a list of huggingface_hub.CommitOperationAdd
        try:
            info = self.api.dataset_info(self.repo_id)
            parent_commit = info.sha
        except Exception as e:
            raise RuntimeError(f"Could not get parent commit for {self.repo_id}: {e}")
            
        print(f"Creating commit on {self.repo_id} with parent {parent_commit}...")
        self.api.create_commit(
            repo_id=self.repo_id,
            repo_type="dataset",
            operations=operations,
            commit_message=commit_message,
            parent_commit=parent_commit
        )
        print("Data published successfully.")

