"""Run ingest locally, then commit + push the output so Streamlit picks it up.

Safe for several people: pull -> ingest -> log -> commit -> push. If the push is
rejected (someone else pushed first), reset to the remote, re-run ingest
(it is idempotent) and push again.

Every run is written to data/publish_log.csv with a status (updated / no new data /
failed) and pushed, so the dashboard shows who ran what.
"""
import csv
import getpass
import importlib.util
import json
import os
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAX_TRIES = 3
LOG = ROOT / "data" / "publish_log.csv"

OK_UPDATED = "Success - data updated"
OK_NO_CHANGE = "Success - no new data"
FAILED = "Failed"


class Tee:
    """Write everything printed to the console AND to the per-user log file."""

    def __init__(self, console, logfile):
        self.console, self.logfile = console, logfile

    def write(self, text):
        self.console.write(text)
        self.logfile.write(text)
        self.logfile.flush()

    def flush(self):
        self.console.flush()
        self.logfile.flush()


def start_logging(cfg):
    """Log this run to <data_dir>\\logs\\<username>.log (one file per person, so OneDrive never conflicts)."""
    logdir = Path(cfg["data_dir"]) / "logs"
    logdir.mkdir(exist_ok=True)
    logfile = open(logdir / f"{getpass.getuser()}.log", "a", encoding="utf-8", errors="replace")
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
    sys.stdout = Tee(sys.stdout, logfile)
    sys.stderr = Tee(sys.stderr, logfile)
    print(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S}  user={getpass.getuser()}  host={socket.gethostname()} =====")


def run(cmd, check=True, **kw):
    """Run a command, streaming its output through print() so it reaches the log file too."""
    print("> " + " ".join(cmd))
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", **kw)
    for line in p.stdout:
        print(line, end="")
    rc = p.wait()
    if check and rc:
        raise subprocess.CalledProcessError(rc, cmd)
    return subprocess.CompletedProcess(cmd, rc)


def ensure_git_identity():
    """Commits fail if git has no name/email; set a local fallback only when missing."""
    user = getpass.getuser()
    for key, fallback in (("user.name", user), ("user.email", f"{user}@users.noreply.github.com")):
        current = subprocess.run(["git", "config", "--get", key], cwd=ROOT,
                                 capture_output=True, text=True).stdout.strip()
        if not current:
            run(["git", "config", "--local", key, fallback])
            print(f"git {key} was not set - using '{fallback}' for this repo.")


def check_github_access(branch):
    """Dry-run push: triggers the GitHub sign-in window if needed and proves we have write access."""
    if run(["git", "push", "--dry-run", "origin", branch], check=False).returncode != 0:
        sys.exit(
            "\nCannot push to GitHub (FolderNew/Shared-Scheduler). Most likely:\n"
            "  1. You are not signed in. A GitHub login window should open - sign in with YOUR GitHub account\n"
            "     and run publish.bat again.\n"
            "  2. Your GitHub account has no write access. Send your GitHub username to the repo owner\n"
            "     so you can be added to the FolderNew organization / repo (Write).\n"
            "  3. You are signed in as a different account. Open Windows Credential Manager, remove\n"
            "     'git:https://github.com', and run again.\n"
            "Details are in your log file: <shared folder>\\logs\\" + getpass.getuser() + ".log\n")


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
    env = {**os.environ, "DATA_DIR": cfg["data_dir"], "REPO_DIR": str(ROOT)}
    cmd = [a.replace("{data_dir}", cfg["data_dir"]) for a in cfg["ingest_cmd"]]
    run(cmd, env=env)


def data_summary():
    data = ROOT / "data" / "weather.parquet"
    if not data.exists():
        return ""
    import pandas as pd
    df = pd.read_parquet(data)
    return f"{len(df)} rows, {df['date'].min():%Y-%m-%d} to {df['date'].max():%Y-%m-%d}"


def log_run(status, summary):
    """Append one row to data/publish_log.csv (shown in the dashboard)."""
    LOG.parent.mkdir(exist_ok=True)
    new = not LOG.exists()
    with LOG.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "user", "host", "status", "summary"])
        w.writerow([f"{datetime.now():%Y-%m-%d %H:%M}", getpass.getuser(),
                    socket.gethostname(), status, summary])


def commit_and_push(cfg, branch, status, summary, paths):
    """Log the run, commit `paths` plus the log, push. Returns True if pushed."""
    log_run(status, summary)
    run(["git", "add", "--", *paths, "data/publish_log.csv"])
    run(["git", "commit", "-m", f"{status} - {datetime.now():%Y-%m-%d %H:%M} by {getpass.getuser()}"])
    return run(["git", "push", "origin", branch], check=False).returncode == 0


REQUIRED_LIBS = ["requests", "pandas", "pyarrow"]


def check_libs():
    missing = [m for m in REQUIRED_LIBS if importlib.util.find_spec(m) is None]
    if missing:
        sys.exit("\nMissing Python libraries: " + ", ".join(missing)
                 + "\nInstall them once, then run publish.bat again:\n"
                 + "    pip install " + " ".join(REQUIRED_LIBS) + "\n")


def main():
    cfg = load_config()
    start_logging(cfg)
    check_libs()
    branch = git_out("rev-parse", "--abbrev-ref", "HEAD")

    ensure_git_identity()
    run(["git", "pull", "--rebase", "--autostash"])
    check_github_access(branch)
    for attempt in range(1, MAX_TRIES + 1):
        try:
            ingest(cfg)
        except Exception as e:
            err = str(e).replace("\n", " ")[:200]
            print(f"Ingest failed: {err}")
            run(["git", "checkout", "--", "data"], check=False)
            if commit_and_push(cfg, branch, FAILED, f"ingest error: {err}", []):
                print("Failure logged and pushed.")
            sys.exit(1)

        run(["git", "add", "--", *cfg["publish_paths"]])
        changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0
        status = OK_UPDATED if changed else OK_NO_CHANGE
        if commit_and_push(cfg, branch, status, data_summary(), cfg["publish_paths"]):
            print(f"{status}. Logged and pushed - Streamlit will pick it up.")
            return
        print(f"Push rejected (try {attempt}/{MAX_TRIES}) - resyncing and re-running ingest.")
        run(["git", "fetch", "origin"])
        run(["git", "reset", "--hard", f"origin/{branch}"])
    sys.exit("Push failed after retries. Check the output above.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (0, None):
            print(e.code if isinstance(e.code, str) else f"Exited with code {e.code}", file=sys.stderr)
            print("===== FAILED =====")
        raise SystemExit(0 if e.code in (0, None) else 1)
    except Exception:
        import traceback
        traceback.print_exc()
        print("===== FAILED =====")
        sys.exit(1)
    print("===== done =====")
