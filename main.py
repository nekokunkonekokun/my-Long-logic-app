import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import timedelta

st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart")

# P50の最高値を記憶するセッションステート
if 'p50_fixed' not in st.session_state:
    st.session_state.p50_fixed = 0.0

@st.cache_data(ttl=3600)
def get_data():
    df = yf.download("NIY=F", period="1y", interval="1h").dropna()
    df.index = df.index.tz_convert('Asia/Tokyo')
    return df

df = get_data()
current_max = df['Close'].max().item()

# 新高値が出たら更新
if current_max > st.session_state.p50_fixed:
    st.session_state.p50_fixed = current_max

p50 = st.session_state.p50_fixed
std = df['Close'].rolling(window=575).std().iloc[-1].item()
current = df['Close'].iloc[-1].item()

# 各レベルの計算
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
tail_df = df.tail(168)
fig, ax = plt.subplots(figsize=(16, 7))
ax.plot(range(len(tail_df)), tail_df['Close'], color='black', lw=1.5)
ax.set_xlim(0, len(tail_df) - 1)

# 各ラインの描画
colors = {'P50': 'red', 'P48': 'green', 'P45': 'blue', 'P40': 'brown', 'P35': 'gray'}
for label, price in price_levels.items():
    ax.axhline(price, color=colors[label], linestyle='--', alpha=0.6)

# 軸フォーマット
def jst_utc_formatter(i, pos):
    idx = int(i)
    if 0 <= idx < len(tail_df):
        dt_jst = tail_df.index[idx]
        dt_utc = dt_jst - timedelta(hours=9)
        return f"{dt_jst.strftime('%m/%d %H:%M')}\n({dt_utc.strftime('%H:%M')} UTC)"
    return ""

ax.xaxis.set_major_formatter(ticker.FuncFormatter(jst_utc_formatter))
ax.xaxis.set_major_locator(ticker.MaxNLocator(7))
plt.xticks(rotation=30, fontsize=10, ha='right')
ax.grid(True, alpha=0.4)
plt.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.2)

# グラフ出力
st.pyplot(fig, use_container_width=True)

# 凡例セクション（枠線なし、各ラベルを独立）
st.markdown("---")
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

col1.metric("Current", f"{current:.0f}")
col2.metric("Dev", f"{current_dev:.1f}")
col3.metric("P50", f"{price_levels['P50']:.0f}")
col4.metric("P48", f"{price_levels['P48']:.0f}")
col5.metric("P45", f"{price_levels['P45']:.0f}")
col6.metric("P40", f"{price_levels['P40']:.0f}")
col7.metric("P35", f"{price_levels['P35']:.0f}")
