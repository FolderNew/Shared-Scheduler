"""Run ingest locally, then commit + push the output so Streamlit picks it up.

Safe for several people: pull -> ingest -> commit -> push. If the push is
rejected (someone else pushed first), reset to the remote, re-run ingest
(it is idempotent) and push again.
"""
import getpass
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAX_TRIES = 3


def run(cmd, check=True, **kw):
    print("> " + " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=check, **kw)


def git_out(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def load_config():
    path = ROOT / "config.json"
    if not path.exists():
        sys.exit("config.json missing from the repo folder.")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    data_dir = os.path.expandvars(cfg.get("data_dir", ""))
    if not data_dir or not Path(data_dir).exists():
        sys.exit(f"data_dir not found: '{data_dir}' - check that the OneDrive folder is synced on this PC (see config.json).")
    cfg["data_dir"] = data_dir
    print(f"User: {getpass.getuser()}\nData dir: {data_dir}")
    return cfg


def ingest(cfg):
    env = {**os.environ, "DATA_DIR": cfg["data_dir"]}
    run(cfg["ingest_cmd"], env=env)


def commit(cfg):
    run(["git", "add", "--", *cfg["publish_paths"]])
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if staged.returncode == 0:
        return False
    msg = f"Data update {datetime.now():%Y-%m-%d %H:%M} by {getpass.getuser()}"
    run(["git", "commit", "-m", msg])
    return True


def main():
    cfg = load_config()
    branch = git_out("rev-parse", "--abbrev-ref", "HEAD")

    run(["git", "pull", "--rebase", "--autostash"])
    for attempt in range(1, MAX_TRIES + 1):
        ingest(cfg)
        if not commit(cfg):
            print("Nothing changed - nothing to push.")
            return
        if run(["git", "push", "origin", branch], check=False).returncode == 0:
            print("Pushed. Streamlit will pick it up.")
            return
        print(f"Push rejected (try {attempt}/{MAX_TRIES}) - resyncing and re-running ingest.")
        run(["git", "fetch", "origin"])
        run(["git", "reset", "--hard", f"origin/{branch}"])
    sys.exit("Push failed after retries. Check the output above.")


if __name__ == "__main__":
    main()
