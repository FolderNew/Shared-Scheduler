from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Shared Scheduler", layout="wide")

DATA = Path(__file__).parent / "data"
log = DATA / "publish_log.csv"
weather = DATA / "weather.parquet"

st.title("Publish history")
st.caption("Who pushed data, and when.")

if log.exists():
    hist = pd.read_csv(log).sort_values("time", ascending=False)
    st.dataframe(hist, use_container_width=True, hide_index=True)
else:
    st.info("No publishes logged yet. Run publish.bat to push data.")

if weather.exists():
    st.divider()
    st.caption("Latest data (last 5 rows)")
    df = pd.read_parquet(weather).sort_values("date", ascending=False).head(5)
    st.dataframe(df, use_container_width=True, hide_index=True)
