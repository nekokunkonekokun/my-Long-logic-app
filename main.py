import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import timedelta

st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart")

if 'p50_fixed' not in st.session_state:
    st.session_state.p50_fixed = 0.0

@st.cache_data(ttl=3600)
def get_data():
    df = yf.download("NIY=F", period="1y", interval="1h").dropna()
    df.index = df.index.tz_convert('Asia/Tokyo')
    return df

df = get_data()
current_max = df['Close'].max().item()

if current_max > st.session_state.p50_fixed:
    st.session_state.p50_fixed = current_max

p50 = st.session_state.p50_fixed
std = df['Close'].rolling(window=575).std().iloc[-1].item()
current = df['Close'].iloc[-1].item()

price_levels = {
    "P50": p50,
    "P48": p50 - (1 * std),
    "P45": p50 - (2 * std),
    "P40": p50 - (3 * std),
    "P35": p50 - (4 * std)
}

if current >= price_levels["P48"]:
    current_dev = 48 + (50 - 48) * (current - price_levels["P48"]) / (p50 - price_levels["P48"])
elif current >= price_levels["P45"]:
    current_dev = 45 + (48 - 45) * (current - price_levels["P45"]) / (price_levels["P48"] - price_levels["P45"])
else:
    current_dev = 40 + (45 - 40) * (current - price_levels["P40"]) / (price_levels["P45"] - price_levels["P40"])

# グラフ描画
tail_df = df.tail(168)
fig, ax = plt.subplots(figsize=(10, 9)) # 縦長に設定
fig.patch.set_facecolor('#0E1117') # 背景をStreamlitの黒に
ax.set_facecolor('#0E1117') # グラフ内も黒に合わせるならここも調整可

ax.plot(range(len(tail_df)), tail_df['Close'], color='white', lw=1.5)
ax.set_xlim(0, len(tail_df) - 1)

# 破線の描画
colors = {'P50': 'red', 'P48': 'green', 'P45': 'blue', 'P40': 'brown', 'P35': 'gray'}
for label, price in price_levels.items():
    ax.axhline(price, color=colors[label], linestyle='--', alpha=0.6)

# 1. 【グラフ内】凡例
panel_text = f"Current: {current:.0f}\nDev: {current_dev:.1f}\n" + \
             "\n".join([f"{k}: {p:.0f}" for k, p in price_levels.items()])
ax.text(0.02, 0.02, panel_text, transform=ax.transAxes, fontsize=10, 
        color='white', bbox=dict(facecolor='black', alpha=0.5, edgecolor='white'), ha='left', va='bottom')

# 2. 【黒い余白部分】大きい文字の凡例
footer_text = f"Current: {current:.0f} | Dev: {current_dev:.1f}\n" + \
              "  ".join([f"{k}: {p:.0f}" for k, p in price_levels.items()])
fig.text(0.05, 0.05, footer_text, color='white', fontsize=14, 
         fontweight='bold', ha='left', va='bottom')

# 軸設定
ax.tick_params(axis='x', colors='white')
ax.tick_params(axis='y', colors='white')
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda i, pos: tail_df.index[int(i)].strftime('%m/%d %H:%M') if 0 <= int(i) < len(tail_df) else ""))
plt.xticks(rotation=30, fontsize=10, ha='right')

# 余白設定 (bottomを大きく取って黒背景部分を確保)
plt.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.3)

st.pyplot(fig, use_container_width=True)
