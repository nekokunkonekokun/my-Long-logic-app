import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

st.title("NIY=F Strategic 3-Level Chart")

# データ取得
df = yf.download("NIY=F", period="1y", interval="1h")
df.index = df.index.tz_convert('Asia/Tokyo')

max_price = df['Close'].max()
current = df['Close'].iloc[-1]
std = df['Close'].rolling(window=25).std().iloc[-1]
current_time = df.index[-1].strftime('%Y-%m-%d %H:%M')

# レベル定義 (P50を最高値として計算)
levels = {"P50 (Red)": 0, "P48 (Green)": 2, "P45 (Blue)": 5, "P40 (Gray)": 10}

st.sidebar.write(f"**LATEST PRICE**: {current:.0f}")
st.sidebar.write("---")
st.sidebar.subheader("TARGET LEVELS")

# 空間的パネル表示
for label, diff in levels.items():
    price_level = max_price - (diff * std)
    st.sidebar.write(f"{label} : {price_level:.0f}")

st.sidebar.write("---")
st.sidebar.write(f"Sigma(25d) : {std:.0f}")
st.sidebar.write(f"Time : {current_time}")

# グラフ描画
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(df.index[-168:], df['Close'].tail(168), color='black', lw=1)
for label, diff in levels.items():
    ax.axhline(max_price - (diff * std), linestyle='--', alpha=0.5)
ax.grid(True, alpha=0.3)
st.pyplot(fig)
