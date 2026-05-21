import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart")

# データ取得・クリーンアップ
df = yf.download("NIY=F", period="1y", interval="1h").dropna()
df.index = df.index.tz_convert('Asia/Tokyo')

# 指標計算
max_price = df['Close'].max().item()
current = df['Close'].iloc[-1].item()
std = df['Close'].rolling(window=25).std().iloc[-1].item()
current_dev = 50 - ((max_price - current) / std)

# レベル設定
levels = {"P50 (Red)": 0, "P48 (Green)": 2, "P45 (Blue)": 5, "P40 (Gray)": 10}

# グラフ描画
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(df.index[-168:], df['Close'].tail(168), color='black', lw=1.2)

# 水平線の描画
colors = ['red', 'green', 'blue', 'gray']
for i, (label, diff) in enumerate(levels.items()):
    ax.axhline(max_price - (diff * std), color=colors[i], linestyle='--', alpha=0.5)

# 情報パネルをグラフ右下に配置
panel_text = f"Current: {current:.0f}\nDev: {current_dev:.1f}\n" + \
             "\n".join([f"{k}: {max_price - (v*std):.0f}" for k, v in levels.items()])
ax.text(0.98, 0.02, panel_text, transform=ax.transAxes, fontsize=9, 
        bbox=dict(facecolor='white', alpha=0.8), ha='right', va='bottom')

ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
ax.grid(True, alpha=0.3)
st.pyplot(fig)
