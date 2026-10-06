# Shared-Scheduler

Any of the three of us can run ingest on our own machine and push the result to GitHub;
Streamlit deploys from this repo.

## One-time setup (each person)
1. Get added to the FolderNew org / this repo (needs write access) and sign in via Git Credential Manager.
2. Clone to a **local disk, NOT inside OneDrive** (OneDrive corrupts `.git`):
   `git clone https://github.com/FolderNew/Shared-Scheduler.git C:\Repos\Shared-Scheduler`
3. Nothing to configure per person: `config.json` is committed and uses `%USERPROFILE%`, so the OneDrive path
   resolves to whoever runs it (`C:\Users\<name>\ETG\SoftsDatabase - Documents\Database\Hardmine\A Shared Scheduler`).
   Just make sure that folder is synced on your PC. `publish.bat` prints who is running it and the resolved path.
   - `ingest_cmd` - command that runs ingest (repo root is the working dir; it receives `DATA_DIR` as an env var)
   - `publish_paths` - folders/files committed and pushed (e.g. the parquet output)

## Every run
Double-click `publish.bat` (or `python publish.py`). It does: pull --rebase -> ingest -> commit -> push.

## Rules
- Ingest must be **idempotent** (upsert on a key, never blind append), so any of us running it gives the same result.
- If two people push at once, the loser's run resets to the remote, re-runs ingest and pushes again (parquet can't be merged).
- Use this clone only for publishing: the retry does `git reset --hard origin/<branch>`, so don't keep uncommitted work here.
- Don't run it at the same time as someone else - say so in the group first.
