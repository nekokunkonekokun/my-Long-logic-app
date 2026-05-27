import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart")

if 'p50_fixed' not in st.session_state:
    st.session_state.p50_fixed = 0.0

@st.cache_data(ttl=300)
def get_data():
    df = yf.download("NIY=F", period="1y", interval="1h").dropna()
    df.index = df.index.tz_convert('Asia/Tokyo')
    return df

df = get_data()
current = df['Close'].iloc[-1].item()
current_max = df['Close'].max().item()

if current_max > st.session_state.p50_fixed:
    st.session_state.p50_fixed = current_max

p50 = st.session_state.p50_fixed
std = df['Close'].rolling(window=575).std().iloc[-1].item()

price_levels = {
    "P50": p50,
    "P48": p50 - std,
    "P45": p50 - 2*std,
    "P40": p50 - 3*std,
    "P35": p50 - 4*std
}

# Dev計算
if current >= price_levels["P48"]:
    current_dev = 48 + 2 * (current - price_levels["P48"]) / (p50 - price_levels["P48"])
elif current >= price_levels["P45"]:
    current_dev = 45 + 3 * (current - price_levels["P45"]) / (price_levels["P48"] - price_levels["P45"])
else:
    current_dev = 40 + 5 * (current - price_levels["P40"]) / (price_levels["P45"] - price_levels["P40"])

# グラフ描画
fig, ax = plt.subplots(figsize=(16, 7))
ax.plot(range(len(df.tail(168))), df['Close'].tail(168), color='black', lw=1.5)
for label, price in price_levels.items():
    ax.axhline(price, color={'P50':'red','P48':'green','P45':'blue','P40':'brown','P35':'gray'}[label], linestyle='--', alpha=0.6)

st.pyplot(fig, use_container_width=True)

# 凡例表示
cols = st.columns(7)
cols[0].metric("Current", f"{current:.0f}")
cols[1].metric("Dev", f"{current_dev:.1f}")
cols[2].metric("P50", f"{p50:.0f}")
cols[3].metric("P48", f"{price_levels['P48']:.0f}")
cols[4].metric("P45", f"{price_levels['P45']:.0f}")
cols[5].metric("P40", f"{price_levels['P40']:.0f}")
cols[6].metric("P35", f"{price_levels['P35']:.0f}")
