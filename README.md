# Shared Scheduler

Three people share one OneDrive folder. **Any of them** double-clicks one file, ingest runs on
their own PC, the result is pushed to GitHub, and Streamlit shows it, including a history of
who ran what. This repo is the working example (a small weather pull) and the template for
building the same mechanism in another project.

```
 shared OneDrive folder                 each person's PC                      cloud
┌───────────────────────┐   click   ┌─────────────────────────┐  git push  ┌────────┐      ┌───────────┐
│ publish.bat           │ ───────>  │ local clone of the repo │ ─────────> │ GitHub │ ───> │ Streamlit │
│ ingest.py  (secrets)  │           │ (NOT inside OneDrive)   │            └────────┘      └───────────┘
│ raw inputs            │ <───────  │ publish.py runs ingest  │
│ logs/<user>.log       │  writes   └─────────────────────────┘
└───────────────────────┘  log
```

## Where each piece lives, and why

| Piece | Location | Why |
|---|---|---|
| `publish.bat` (the thing people click) | Shared OneDrive folder | One shared entry point; clones the repo on first run |
| `ingest.py` | Shared OneDrive folder | Holds API tokens/paths. The GitHub repo can be public, so it must never be committed |
| Raw input files | Shared OneDrive folder | Everyone already has them synced |
| `publish.py`, `app.py`, `config.json`, `data/` | GitHub repo, local clone per person | Git needs a normal local disk |
| `logs/<username>.log` | Shared OneDrive folder | One file per person, so OneDrive never has conflicts, and anyone can see who is stuck |
| `data/publish_log.csv` | In the repo | Feeds the dashboard's Publish history |

**Never put the git repo inside OneDrive.** Three people syncing one `.git` corrupts it.
`publish.bat` clones to `%USERPROFILE%\Shared-Scheduler` (local disk) instead.

## What one click does

1. `publish.bat` checks Git and Python are installed, clones the repo on first run, and runs `git pull` so everyone always runs the latest `publish.py`.
2. `publish.py` checks the libraries, opens the per-user log file, sets a fallback git name/email if missing, pulls, and does a dry-run push to prove GitHub login and write access (this also opens the GitHub sign-in window the first time).
3. It runs `ingest.py`, which writes the parquet into the local clone.
4. It stages the output, appends a row to `data/publish_log.csv`, commits and pushes.
5. If the push is rejected (someone pushed a second earlier) it resets to the remote, re-runs ingest and pushes again, up to 3 tries.

Every run is logged with a status:

| Status | Meaning |
|---|---|
| `Success - data updated` | New data was committed and pushed |
| `Success - no new data` | Ran fine, data identical; only the log row was pushed |
| `Failed` | Ingest crashed; the error is in the summary and the failure row is pushed |

Problems that happen before anything can be pushed (no Git, no Python, no GitHub access, missing libraries) are written to `logs\<username>.log` in the shared folder.

## Files in this repo

| File | Purpose |
|---|---|
| `publish.py` | The whole mechanism. Project-agnostic, driven by `config.json` |
| `config.json` | Paths and settings (see below) |
| `app.py` | Streamlit page: Publish history (main) + small preview of the data |
| `.streamlit/config.toml` | Forces the light theme |
| `requirements.txt` | Streamlit Cloud dependencies (`streamlit==1.56.0` is pinned on purpose) |
| `data/` | Output parquet + `publish_log.csv` |
| `templates/publish.bat` | Copy of the clickable file that sits in the shared OneDrive folder |
| `templates/ingest_template.py` | Skeleton for a new `ingest.py` |

## Build the same thing for another project

1. **GitHub.** Create a repo (org repos need the setup in the checklist below). Give all three people **Write** access.
2. **Shared folder.** Create a folder in the shared OneDrive, e.g. `...\Hardmine\<Project Name>`.
3. **Repo contents.** Copy `publish.py`, `config.json`, `app.py`, `.streamlit/`, `requirements.txt` and `.gitignore` into the new repo. Create an empty `data/` folder with a placeholder file.
4. **Edit `config.json`:**
   ```json
   {
     "data_dir": "%USERPROFILE%\\ETG\\SoftsDatabase - Documents\\Database\\Hardmine\\<Project Name>",
     "ingest_cmd": ["python", "{data_dir}\\ingest.py"],
     "publish_paths": ["data/"],
     "summary_file": "data/mydata.parquet",
     "date_column": "date"
   }
   ```
   - `%USERPROFILE%` resolves per person, so only the part after the user folder must be identical on all three PCs.
   - Backslashes must be doubled in JSON (`\\`). A single `\` breaks the file.
5. **Shared folder contents.** Copy `templates/publish.bat` there and change the clone URL and `REPO` folder name inside it. Copy `templates/ingest_template.py` there as `ingest.py` and fill in the TODOs.
6. **Edit `app.py`** to show whatever the new data is. Keep the Publish history section.
7. **Test** by double-clicking `publish.bat` once, then check the new commit and the new row in `data/publish_log.csv`.
8. **Deploy** on share.streamlit.io (repo, branch `main`, file `app.py`).
9. Tell the other two to run `publish.bat`.

### The ingest contract

`publish.py` runs `ingest_cmd` and sets two environment variables:

| Variable | Value |
|---|---|
| `DATA_DIR` | The shared OneDrive folder (raw inputs live here) |
| `REPO_DIR` | That person's local clone; write output to `REPO_DIR\data\` |

Ingest must be **idempotent and deterministic**: same inputs, same output, upsert on a key, never blind append, no timestamps inside the file. That is what makes "no new data" detection work and lets a rejected push be retried safely. Exit non-zero (raise) on any failure so it is logged as `Failed`.

## Checklist for each new teammate

- [ ] Python and Git for Windows installed (Python: tick "Add python.exe to PATH")
- [ ] `python -m pip install requests pandas pyarrow` (add whatever the new ingest imports)
- [ ] GitHub account with **Write** access to the repo
- [ ] The shared OneDrive folder is synced on their PC
- [ ] Double-click `publish.bat`; sign in to GitHub when the browser window opens

## Org repo gotchas (GitHub organisation + Streamlit Cloud)

| Error | Fix |
|---|---|
| Repo does not appear in Streamlit's repository list | Type `org/repo` manually; branch is `main`, not `master` |
| "organization has enabled OAuth App access restrictions" | Org settings, Third-party Access: approve Streamlit (or Remove restrictions). Needs an org owner |
| "Deploy keys are disabled for this repository or organization" | Org settings: allow deploy keys. Needs an org owner |
| Push rejected / "Cannot push to GitHub" | No write access, or signed in as the wrong account. Remove `git:https://github.com` in Windows Credential Manager and retry |

## Other things learned the hard way

- **Public repo means no secrets in it.** The API token sits in `ingest.py` inside OneDrive, not in git.
- **`.bat` files must stay CRLF/ASCII.** Editing with a tool that strips `\r` breaks them. Re-save with CRLF after editing.
- **CSV values containing commas must be quoted.** `publish.py` uses the `csv` module for this; do not hand-write the log.
- **`publish.bat` runs `git pull` before `publish.py`.** Otherwise the old script starts and only updates itself mid-run.
- **Only one person at a time** is safest; two at once is handled by the retry, but tell the others in chat first.
- **Streamlit is pinned to 1.56.0** in `requirements.txt` to avoid a known crash on newer versions.
- **Source systems that need a logged-in app** (LSEG Workspace, ICE Connect) only work on a PC where that app is open. For those projects, only people with it running can click publish.

## Troubleshooting

| Symptom | Look at |
|---|---|
| Nothing happens / window closes | Run it from a Command Prompt to see the message |
| "data_dir not found" | The OneDrive folder is not synced on that PC, or the path in `config.json` differs |
| "Missing Python libraries" | Run the `pip install` line it prints |
| Someone is stuck | Open `logs\<their username>.log` in the shared folder |
| Dashboard not updating | Check `data/publish_log.csv` on GitHub for their row, then reboot the Streamlit app |
