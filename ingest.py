"""Placeholder ingest: merge every CSV in DATA_DIR into data/data.parquet (dedup on all columns).
Replace with the real ingest; keep it idempotent."""
import os
from pathlib import Path

import pandas as pd

src = Path(os.environ["DATA_DIR"])
files = sorted(src.glob("*.csv"))
if not files:
    raise SystemExit(f"No CSV files in {src}")

df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True).drop_duplicates()
out = Path(__file__).parent / "data" / "data.parquet"
df.to_parquet(out, index=False)
print(f"Wrote {len(df)} rows from {len(files)} file(s) -> {out}")
