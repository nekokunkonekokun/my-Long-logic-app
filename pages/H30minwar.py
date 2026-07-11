import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ページ設定
st.set_page_config(layout="wide")
st.title("Market War Map: 30m Scalping Terminal")

# サイドバーによる入力
with st.sidebar:
    st.header("Settings")
    ticker = st.text_input("Ticker Symbol", value="NIY=F")
    days = st.slider("Data Range (Days)", 1, 10, 3)
    spike_threshold = st.slider("Panic Spike Sensitivity", 1.0, 3.0, 2.0, 0.1)
    
    run_btn = st.button("Analyze Now")

if run_btn:
    # データ取得
    with st.spinner(f"Loading {ticker}..."):
        df = yf.download(ticker, period=f"{days}d", interval="30m")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df['Range'] = df['High'] - df['Low']
        df['Vol_Factor'] = df['Range'] / df['Range'].rolling(5).mean()
        
        # 可視化ロジック
        bins = np.linspace(float(df['Low'].min()), float(df['High'].max()), 100)
        labels = bins[:-1] + (bins[1] - bins[0]) / 2
        
        v_profile = np.zeros(len(labels))
        p_profile = np.zeros(len(labels))
        
        for _, row in df.iterrows():
            vol = float(row['Volume'])
            factor = float(row['Vol_Factor'])
            mask = (labels >= float(row['Low'])) & (labels <= float(row['High']))
            count = np.sum(mask)
            if count == 0: continue
            
            v_profile[mask] += (vol / count)
            if factor > spike_threshold:
                p_profile[mask] += (vol * factor / count)
        
        # プロット
        fig, ax = plt.subplots(figsize=(10, 6))
        bin_w = bins[1] - bins[0]
        ax.barh(labels, v_profile, height=bin_w*0.8, color='skyblue', alpha=0.4, label='Volume')
        ax.barh(labels, p_profile, height=bin_w*0.8, color='red', alpha=0.6, label='Panic Spike')
        
        current_price = float(df['Close'].iloc[-1])
        ax.axhline(y=current_price, color='black', linewidth=2, label=f'Current: {current_price:,.0f}')
        
        ax.set_title(f"War Map: {ticker}")
        ax.legend()
        st.pyplot(fig)

