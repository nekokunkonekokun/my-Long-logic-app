import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import timedelta

st.title("Strategic Analysis Detail")

# データロードとロジック（そのまま）
@st.cache_data(ttl=3600)
def get_analysis_data():
    df = yf.download("NIY=F", period="1y", interval="1h").dropna()
    df.index = df.index.tz_convert('Asia/Tokyo')
    max_price = df['Close'].max().item()
    current = df['Close'].iloc[-1].item()
    std = df['Close'].rolling(window=575).std().iloc[-1].item()
    levels = {"P50": 0, "P48": 1, "P45": 2, "P40": 3, "P35": 4}
    price_levels = {k: max_price - (v * std) for k, v in levels.items()}
    if current >= price_levels["P48"]:
        current_dev = 48 + (50 - 48) * (current - price_levels["P48"]) / (max_price - price_levels["P48"])
    elif current >= price_levels["P45"]:
        current_dev = 45 + (48 - 45) * (current - price_levels["P45"]) / (price_levels["P48"] - price_levels["P45"])
    else:
        current_dev = 40 + (45 - 40) * (current - price_levels["P40"]) / (price_levels["P45"] - price_levels["P40"])
    return df, price_levels, current, current_dev

df, price_levels, current, current_dev = get_analysis_data()
tail_df = df.tail(168)

# 1. グラフの表示幅を最大化する（use_container_width=True）
fig, ax = plt.subplots(figsize=(15, 6))
x = range(len(tail_df))
ax.plot(x, tail_df['Close'], color='black', lw=1.2)

# 水平線と凡例
colors = {'P50': 'red', 'P48': 'green', 'P45': 'blue', 'P40': 'brown', 'P35': 'gray'}
for label, price in price_levels.items():
    ax.axhline(price, color=colors[label], linestyle='--', alpha=0.5)

panel_text = f"Current: {current:.0f}\nDev: {current_dev:.1f}\n" + \
             "\n".join([f"{k}: {p:.0f}" for k, p in price_levels.items()])
ax.text(0.02, 0.02, panel_text, transform=ax.transAxes, fontsize=10, 
        bbox=dict(facecolor='white', alpha=0.8), ha='left', va='bottom')

# 2. X軸：JST基準のフォーマッター
def jst_utc_formatter(i, pos):
    idx = int(i)
    if 0 <= idx < len(tail_df):
        dt_jst = tail_df.index[idx]
        # JSTからUTCを引くのではなく、JSTをそのままメインに表示する
        dt_utc = dt_jst - timedelta(hours=9)
        return f"{dt_jst.strftime('%m/%d %H:%M')}\n({dt_utc.strftime('%H:%M')} UTC)"
    return ""

ax.xaxis.set_major_formatter(ticker.FuncFormatter(jst_utc_formatter))
ax.xaxis.set_major_locator(ticker.MaxNLocator(10))

plt.xticks(rotation=45, fontsize=9, ha='right')
plt.tight_layout()
ax.grid(True, alpha=0.3)

# 3. Streamlit側でコンテナ幅いっぱいに引き伸ばす
st.pyplot(fig, use_container_width=True)
