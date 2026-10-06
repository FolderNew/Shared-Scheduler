from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Shared Scheduler", layout="wide")
st.title("Shared Scheduler")

DATA = Path(__file__).parent / "data"
weather = DATA / "weather.parquet"
log = DATA / "publish_log.csv"

if not weather.exists():
    st.info("No data yet. Run publish.bat to ingest and push data/weather.parquet.")
    st.stop()

df = pd.read_parquet(weather)
st.caption(f"Station {df['station'].iloc[0]} ({df['country'].iloc[0]}), last 365 days")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", f"{len(df):,}")
c2.metric("From", f"{df['date'].min():%Y-%m-%d}")
c3.metric("To", f"{df['date'].max():%Y-%m-%d}")
c4.metric("Rain, total (mm)", f"{df['prcp'].sum():,.0f}")

st.subheader("Temperature")
st.line_chart(df.set_index("date")[["tmax", "tavg", "tmin"]])

st.subheader("Daily rain (mm)")
st.bar_chart(df.set_index("date")["prcp"])

st.subheader("Publish history")
if log.exists():
    hist = pd.read_csv(log).sort_values("time", ascending=False)
    st.dataframe(hist, use_container_width=True, hide_index=True)
else:
    st.caption("No publishes logged yet.")
