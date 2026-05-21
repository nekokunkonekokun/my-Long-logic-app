import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart")

df = yf.download("NIY=F", period="1y", interval="1h").dropna()
df.index = df.index.tz_convert('Asia/Tokyo')

max_price = df['Close'].max().item()
current = df['Close'].iloc[-1].item()
std = df['Close'].rolling(window=375).std().iloc[-1].item()
current_dev = 50 - ((max_price - current) / std)

# X軸の準備：直近168個のデータを使用
tail_df = df.tail(168)

x = range(len(tail_df))
dates = tail_df.index.strftime('%m/%d').tolist()

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(x, tail_df['Close'], color='black', lw=1.2)

levels = {"P50": 0, "P48": 1, "P45": 2, "P40": 3, "P35": 4}
colors = {'P50': 'red', 'P48': 'green', 'P45': 'blue', 'P40': 'yellow', 'P35': 'gray'}
for label, diff in levels.items():
    ax.axhline(max_price - (diff * std), color=colors[label], linestyle='--', alpha=0.5)

# 左下に情報パネル
panel_text = f"Current: {current:.0f}\nDev: {current_dev:.1f}\n" + \
             "\n".join([f"{k}: {max_price - (v*std):.0f}" for k, v in levels.items()])
ax.text(0.02, 0.02, panel_text, transform=ax.transAxes, fontsize=9, 
        bbox=dict(facecolor='white', alpha=0.8), ha='left', va='bottom')

# X軸設定：日付ラベルを確実に表示
ax.xaxis.set_major_locator(ticker.MaxNLocator(8))
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda i, pos: dates[int(i)] if 0 <= int(i) < len(dates) else ""))

ax.grid(True, alpha=0.3)
st.pyplot(fig)
