"""TEMPLATE ingest. Copy to the shared OneDrive folder as ingest.py and fill in the TODOs.

Lives in OneDrive, NOT in the git repo: it holds API tokens / paths and the repo may be public.
publish.py runs it and sets two environment variables:
    DATA_DIR  the shared OneDrive folder (raw inputs live here)
    REPO_DIR  the person's local git clone (write the output into REPO_DIR/data/)

Rules: idempotent (same inputs -> same output, upsert on a key, never blind append),
deterministic (no timestamps inside the parquet), and raise/exit non-zero on failure.
"""
import os
from pathlib import Path

import pandas as pd

DATA_DIR = Path(os.environ["DATA_DIR"])
REPO_DIR = Path(os.environ["REPO_DIR"])

# TODO 1: fetch / read the raw data (API call, files in DATA_DIR, ...)
df = pd.DataFrame()

# TODO 2: clean it and make it deterministic (sort, dedupe on the key)
# df = df.drop_duplicates(subset=["key"]).sort_values("key")

if df.empty:
    raise SystemExit("ingest produced no rows")

out = REPO_DIR / "data" / "mydata.parquet"     # TODO 3: output name
out.parent.mkdir(exist_ok=True)
df.to_parquet(out, index=False)
print(f"Wrote {len(df)} rows -> {out}")
