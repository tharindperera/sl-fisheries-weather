# Sri Lankan fishing-harbour weather: setup and first run

Prepared: 7 October 2026.

Use this guide with **Antigravity_SL_Fisheries_Weather_Prompt.txt**. The text file is the complete instruction to paste into Antigravity. It asks the IDE to create and test the actual Python project. The commands below are interfaces that the IDE must implement; they are not an already installed application.

The project stores code in GitHub and data in a Hugging Face **dataset repository**. It collects daily weather and wave data from 2010-01-01 onward for 16 fishing areas, including all ten areas you requested. It keeps historical reanalysis, recent model estimates and forecast snapshots separate.

## 1. Create the GitHub repository

Open [GitHub's new repository page](https://github.com/new) while signed in.

| Setting | Value |
| --- | --- |
| Owner | `tharindperera`, if this is your account |
| Repository name | `sl-fisheries-weather` |
| Description | Daily weather and marine data for Sri Lankan fishing areas |
| Visibility | Public, recommended for this public-data project |
| Initialize | Add a README so the new repository can be cloned |
| Code license | MIT is a reasonable choice; keep the dataset license separate |

Click **Create repository**.

Expected URL: [tharindperera/sl-fisheries-weather](https://github.com/tharindperera/sl-fisheries-weather).

Standard GitHub-hosted Actions runners are free for public repositories under the current billing rules. The prompt uses standard Ubuntu runners. Private repositories have account-dependent included usage and possible charges; do not select a larger paid runner.

Create this new repository instead of editing the existing weather-clustering project. If your actual owner is different, change the expected GitHub remote in the prompt before pasting it.

## 2. Create the Hugging Face dataset

Sign in to Hugging Face and open [New dataset](https://huggingface.co/new-dataset).

| Setting | Value |
| --- | --- |
| Owner | Your actual Hugging Face account |
| Dataset name | `sl-fisheries-weather-daily` |
| Visibility | Public, recommended for the public weather dataset |

Click **Create dataset**. Create a dataset, not a model or a Space.

The existing project's Hugging Face namespace was `tharinduperera`. This differs from the GitHub username `tharindperera`. Confirm your actual Hugging Face account before copying the ID.

Expected dataset ID:

```text
tharinduperera/sl-fisheries-weather-daily
```

Expected URL: [tharinduperera/sl-fisheries-weather-daily](https://huggingface.co/datasets/tharinduperera/sl-fisheries-weather-daily).

If your HF owner differs, use `YOUR_HF_OWNER/sl-fisheries-weather-daily` everywhere instead. Do not accidentally select the old weather-clustering dataset.

You do not need to upload empty CSV files. The implementation's `init-hf` command will write the metadata and dataset card. Antigravity must verify the data license and attribution requirements. The expected data license is CC BY 4.0 for the selected Open-Meteo products; MIT applies to the project code.

## 3. Create a restricted Hugging Face token

Open [Hugging Face access tokens](https://huggingface.co/settings/tokens) and create a new token:

1. Select **Fine-grained**.
2. Name it `sl-fisheries-weather-publisher`.
3. Grant read/write access to the specific dataset created in step 2.
4. Avoid unrelated repository, administration and inference permissions.
5. Copy it into your password manager or directly into the GitHub secret field.

Never paste the token into Antigravity chat, this prompt, a Git commit or an issue. A token restricted to an existing dataset does not need permission to create more repositories, which is why you created the dataset first.

## 4. Configure GitHub Actions

In the new GitHub repository, open:

**Settings > Secrets and variables > Actions**

On the **Secrets** tab, add this repository secret:

| Name | Value |
| --- | --- |
| `HF_TOKEN` | The Hugging Face token from step 3 |

On the **Variables** tab, add these repository variables:

| Name | Initial value | Purpose |
| --- | --- | --- |
| `HF_REPO_ID` | `tharinduperera/sl-fisheries-weather-daily` | Destination dataset; substitute your real owner |
| `AUTOMATION_ENABLED` | `false` | Keeps scheduled daily updates and reconciliation off during setup |
| `BACKFILL_ENABLED` | `false` | Keeps scheduled historical collection off during setup |

Use the lowercase strings `true` and `false`.

The ordinary weather workflows upload to HF using `HF_TOKEN`. They do not need a GitHub personal access token. The built-in `GITHUB_TOKEN` only needs the workflow's stated repository permissions, normally `contents: read` for checkout.

## 5. Open the new project in Antigravity

Install Git and Python 3.11 or later if they are missing. In your terminal, run:

```powershell
git clone https://github.com/tharindperera/sl-fisheries-weather.git
cd sl-fisheries-weather
```

Open this cloned folder in Antigravity. Open **Antigravity_SL_Fisheries_Weather_Prompt.txt**, copy its entire contents, and paste them into the IDE's agent chat.

Before sending it, replace the expected GitHub remote and HF dataset ID if your accounts differ. Keep credentials out of the prompt.

The instruction asks Antigravity to inspect the original project, verify the 16 locations, implement the package, test failures and recovery, run a real pilot, and finish deployment steps when authentication is available. Let it execute and fix the work. Do not accept a response consisting only of a design or unimplemented files.

## 6. Authenticate locally and run the first checks

Antigravity should create the environment and install its project dependencies. If you need to do this manually, run the following **after it has created `pyproject.toml` and the package**.

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\hf.exe auth login
.\.venv\Scripts\hf.exe auth whoami
```

If you use another supported Python version, adjust `py -3.11`. Calling the virtual environment executables directly avoids a PowerShell activation-policy change.

The current HF CLI may offer browser login or **Paste an access token**. Use the interactive token option to enter your restricted token without putting it in a command argument. Check that `auth whoami` shows the expected owner. If the CLI reports an existing wrong account, use `hf auth login --force` interactively.

For Ubuntu/macOS, use these equivalents:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/hf auth login
.venv/bin/hf auth whoami
```

For local configuration, make an ignored `.env` file containing your dataset ID:

```dotenv
HF_REPO_ID=tharinduperera/sl-fisheries-weather-daily
```

The implementation must use the locally cached HF login. CI uses its `HF_TOKEN` environment variable. You do not need to store the token in `.env`.

Then run, in this order, or have Antigravity execute these commands:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m sl_fisheries_weather doctor
.\.venv\Scripts\python.exe -m sl_fisheries_weather verify-sites
.\.venv\Scripts\python.exe -m sl_fisheries_weather pilot --start 2010-01-01 --end 2010-01-14 --include-recent
.\.venv\Scripts\python.exe -m sl_fisheries_weather init-hf
.\.venv\Scripts\python.exe -m sl_fisheries_weather backfill --start 2010-01-01 --max-runtime-minutes 35 --max-estimated-calls 750
.\.venv\Scripts\python.exe -m sl_fisheries_weather update --max-runtime-minutes 35
.\.venv\Scripts\python.exe -m sl_fisheries_weather validate --all
.\.venv\Scripts\python.exe -m sl_fisheries_weather status
```

On Ubuntu/macOS, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.

The pilot must check all sixteen sites and the historical, recent and forecast model combinations. It must not pass with missing required fields or unverified site coordinates.

The first bounded backfill run is deliberately a partial collection. It must publish valid progress and record unfinished windows. A quota deferral is expected behavior, not proof that the full 2010-to-present dataset exists.

Check the Hugging Face **Files and versions** tab. It should contain real Parquet data, metadata, coverage, checkpoints and a dataset card. The HF viewer may take time to process a new configuration; direct file validation is the first acceptance check.

## 7. Push the implementation and test Actions

The prompt tells Antigravity to commit and push the finished code if your Git login is available. Confirm the remote and working tree:

```powershell
git remote -v
git status
```

The remote must be the new repository. Commit code, documentation, tests, workflows and the small verified site catalogue. Keep `data/`, `.env`, caches and credentials ignored.

If a ready local commit has not been pushed:

```powershell
git push origin main
```

Use your actual default branch if different. Complete any normal Git credential-manager sign-in in the terminal/browser. Do not force-push.

In the repository's **Actions** tab:

1. Confirm the offline CI workflow passes.
2. Open the **Backfill** workflow and choose **Run workflow** on the default branch.
3. Check its log and summary for publication, coverage and quota state.
4. Open the **Update Weather** workflow and run it manually.
5. Confirm both runs use the expected HF dataset and that the downloaded published data validates.

Manual dispatch must work with both automation flags still set to `false`. If the workflow names differ, use the corresponding `backfill.yml` and `update_weather.yml` entries.

## 8. Enable collection and scheduling

After the pilot, initialization and manual Actions runs succeed, change the repository variables:

```text
AUTOMATION_ENABLED=true
BACKFILL_ENABLED=true
```

The required schedules are:

| Work | UTC cron | Sri Lanka time | Behavior |
| --- | --- | --- | --- |
| Historical backfill | `31 * * * *` | Every hour at minute 01 | Resumes remaining history, bounded to 35 minutes and 750 estimated calls |
| Daily refresh | `13 1 * * *` | 06:43 daily | Refreshes published history, recent estimates and forecasts |
| Recovery refresh | `13 8 * * *` | 13:43 daily | Repairs eligible gaps and captures a newer forecast snapshot |
| Reconciliation | Monthly slot documented by the implementation | See generated README | Revisits approximately 90 days for revisions |

Backfill and updates share quota accounting and one writer lease. Runs may defer because another writer is active, the provider rate-limits a runner, or the shared budget is exhausted. The next eligible run resumes from durable state.

The proposed project ceiling is 5,000 estimated calls per rolling 24 hours. The full historical acquisition can take several days; runtime, availability and retries affect completion. Do not keep a local collector running independently of the shared writer controls.

Once `status` confirms contiguous historical coverage from 2010 for **every site and both source families** up to their actual published cutoffs, set:

```text
BACKFILL_ENABLED=false
AUTOMATION_ENABLED=true
```

Daily operation continues. The reanalysis cutoff will lag today's date; recent completed-day estimates bridge that gap. Today's and future full-day values remain forecasts. Unreleased trailing reanalysis dates must stay pending rather than becoming zero rainfall or zero waves.

GitHub schedules can be delayed or missed. In public repositories they can be disabled after 60 days without repository activity. Check Actions and HF publication freshness periodically and re-enable workflows when needed. Two schedules in the same repository do not remove this limitation.

## 9. Expected output and recovery

The core published products are:

- Atmospheric ERA5 history: rainfall total/hours, wind maximum/mean/direction, temperature mean/minimum/maximum, humidity and sea-level pressure.
- ERA5-Ocean wave history: maximum wave height, maximum period and dominant direction.
- Separate recent estimates and archived forecast snapshots.
- A joined daily table and past-only features for later price analysis.
- Per-site/source coverage, source attribution, units, QA and resumable collection state.

Look in `metadata/coverage.json` and run `status` to distinguish the latest date from complete coverage. Seeing a recent row alone does not establish that all older dates were collected.

| Symptom | Action |
| --- | --- |
| HF 401 or 403 | Check local login, GitHub secret, token expiry and dataset-specific read/write permissions |
| Repository not found | Verify the complete HF owner/name and GitHub owner/name |
| Unknown `sl_fisheries_weather` command | Confirm Antigravity implemented the package and installed it into the interpreter you are running |
| Provider 429 or budget deferral | Keep the persisted state; honor the reported retry/reset time |
| Historical collection unfinished | Leave backfill enabled; inspect pending/failed windows and let later runs resume |
| Missing newly released history | Inspect actual source availability; keep pending dates missing |
| Failed upload after valid collection | Run `python -m sl_fisheries_weather publish` using the configured environment |
| Concurrent writer/head conflict | Let the implementation reload remote state and retry safely; never overwrite manually |
| Stale daily publication | Check workflow enablement, flags, last run, token and failure summary |

Keep API response data factual. Weather and waves are candidate predictors of fishing supply and prices; this collector does not prove price effects. Species, market, landings, fuel and price observations require a separate price-data project.

## Official references

Checked for this guide on 7 October 2026:

- [GitHub repository creation](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)
- [GitHub Actions secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [GitHub Actions variables](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables)
- [GitHub schedule behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Hugging Face dataset creation](https://huggingface.co/docs/hub/datasets-adding)
- [Hugging Face token permissions](https://huggingface.co/docs/hub/security-tokens)
- [Hugging Face CLI authentication](https://huggingface.co/docs/huggingface_hub/guides/cli)
- [Open-Meteo API terms and limits](https://open-meteo.com/en/pricing)

The implementation must recheck current model/API support and document any change before collecting data.
