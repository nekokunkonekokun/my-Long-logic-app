import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import timedelta

st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart")

# セッション状態にP50（最高値）を保持して固定する
if 'p50_fixed' not in st.session_state:
    st.session_state.p50_fixed = 0.0

@st.cache_data(ttl=3600)
def get_analysis_data():
    df = yf.download("NIY=F", period="1y", interval="1h").dropna()
    df.index = df.index.tz_convert('Asia/Tokyo')
    return df

df = get_analysis_data()
current_max = df['Close'].max().item()

# P50を更新（新高値が出たら更新し、そうでなければ維持）
if current_max > st.session_state.p50_fixed:
    st.session_state.p50_fixed = current_max

current = df['Close'].iloc[-1].item()
std = df['Close'].rolling(window=575).std().iloc[-1].item()

# 固定されたP50を基準にレベルを算出
p50 = st.session_state.p50_fixed
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

# 描画
tail_df = df.tail(168)
fig, ax = plt.subplots(figsize=(16, 7))
x = range(len(tail_df))
ax.plot(x, tail_df['Close'], color='black', lw=1.5)
ax.set_xlim(0, len(tail_df) - 1)

colors = {'P50': 'red', 'P48': 'green', 'P45': 'blue', 'P40': 'brown', 'P35': 'gray'}
for label, price in price_levels.items():
    ax.axhline(price, color=colors[label], linestyle='--', alpha=0.6)

panel_text = f"Current: {current:.0f}\nDev: {current_dev:.1f}\n" + \
             "\n".join([f"{k}: {p:.0f}" for k, p in price_levels.items()])
ax.text(0.01, 0.02, panel_text, transform=ax.transAxes, fontsize=10, 
        bbox=dict(facecolor='white', alpha=0.9), ha='left', va='bottom')

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
plt.subplots_adjust(left=0.06, right=0.98, top=0.95, bottom=0.18)

st.pyplot(fig, use_container_width=True)
