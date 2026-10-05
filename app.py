from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Shared Scheduler", layout="wide")
st.title("Shared Scheduler")

path = Path(__file__).parent / "data" / "data.parquet"
if not path.exists():
    st.info("No data yet. Run publish.bat to ingest and push data/data.parquet.")
    st.stop()

df = pd.read_parquet(path)
st.caption(f"{len(df):,} rows, {len(df.columns)} columns")

num_cols = df.select_dtypes("number").columns.tolist()
c1, c2, c3 = st.columns(3)
c1.metric("Rows", f"{len(df):,}")
c2.metric("Columns", len(df.columns))
c3.metric("Numeric columns", len(num_cols))

if num_cols:
    col = st.selectbox("Chart column", num_cols)
    st.line_chart(df[col])

st.dataframe(df, use_container_width=True)
