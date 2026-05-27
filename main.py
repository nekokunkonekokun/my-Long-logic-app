import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import pandas as pd
from datetime import timedelta

st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart (30m)")

if 'p50_fixed' not in st.session_state:
    st.session_state.p50_fixed = 0.0

@st.cache_data(ttl=60)
def get_data():
    df = yf.download("NIY=F", period="7d", interval="30m")
    df.index = df.index.tz_convert('Asia/Tokyo')
    
    # 欠損日時の処理：30分ごとのインデックスを生成して補完
    full_idx = pd.date_range(start=df.index.min(), end=df.index.max(), freq='30T')
    df = df.reindex(full_idx)
    # 前の値で埋める（取引がない時間は直近の価格を維持）
    df['Close'] = df['Close'].ffill()
    return df

df = get_data()
last_updated = df.index[-1]
current_max = df['Close'].max().item()

if current_max > st.session_state.p50_fixed:
    st.session_state.p50_fixed = current_max

p50 = st.session_state.p50_fixed
# 30分足に合わせた標準偏差期間 (575 * 2 = 1150)
std = df['Close'].rolling(window=1150, min_periods=100).std().iloc[-1].item()
current = df['Close'].iloc[-1].item()

price_levels = {
    "P50": p50,
    "P48": p50 - (1 * std),
    "P45": p50 - (2 * std),
    "P40": p50 - (3 * std),
    "P35": p50 - (4 * std)
}

# Dev計算
if current >= price_levels["P48"]:
    current_dev = 48 + (50 - 48) * (current - price_levels["P48"]) / (p50 - price_levels["P48"])
elif current >= price_levels["P45"]:
    current_dev = 45 + (48 - 45) * (current - price_levels["P45"]) / (price_levels["P48"] - price_levels["P45"])
else:
    current_dev = 40 + (45 - 40) * (current - price_levels["P40"]) / (price_levels["P45"] - price_levels["P40"])

# グラフ描画
fig, ax = plt.subplots(figsize=(16, 7))
ax.plot(df.index, df['Close'], color='black', lw=1.5)

colors = {'P50': 'red', 'P48': 'green', 'P45': 'blue', 'P40': 'brown', 'P35': 'gray'}
for label, price in price_levels.items():
    ax.axhline(price, color=colors[label], linestyle='--', alpha=0.6)

ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d\n%H:%M'))
plt.xticks(rotation=0, fontsize=10)
ax.grid(True, alpha=0.4)
plt.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.2)

st.pyplot(fig, use_container_width=True)

st.caption(f"Data Last Updated: {last_updated.strftime('%Y-%m-%d %H:%M')} JST")
st.markdown("---")
cols = st.columns(7)
cols[0].metric("Current", f"{current:.0f}")
cols[1].metric("Dev", f"{current_dev:.1f}")
cols[2].metric("P50", f"{price_levels['P50']:.0f}")
cols[3].metric("P48", f"{price_levels['P48']:.0f}")
cols[4].metric("P45", f"{price_levels['P45']:.0f}")
cols[5].metric("P40", f"{price_levels['P40']:.0f}")
cols[6].metric("P35", f"{price_levels['P35']:.0f}")
