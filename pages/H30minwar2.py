import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, time, timedelta

# ページ設定
st.set_page_config(layout="wide", page_title="Market War Map")
st.title("Market War Map: Precision")

with st.sidebar:
    st.header("Settings")
    ticker = st.text_input("Ticker Symbol", value="NIY=F")
    
    today = datetime.now().date()
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=today - timedelta(days=5))
        a_start = st.slider("Start Hour", 0, 24, 0)
    with col2:
        end_date = st.date_input("End Date", value=today)
        b_end = st.slider("End Hour", 0, 24, 24)
    
    spike_threshold = st.slider("Sensitivity (σ)", 1.0, 3.0, 2.0, 0.1)
    run_btn = st.button("Analyze Now")

if run_btn:
    # 24時問題を回避し、正確な期間を設定
    start_dt = datetime.combine(start_date, time(hour=a_start))
    if b_end == 24:
        end_dt = datetime.combine(end_date + timedelta(days=1), time(0, 0))
    else:
        end_dt = datetime.combine(end_date, time(hour=b_end))
    
    with st.spinner("Processing..."):
        df = yf.download(ticker, start=start_dt, end=end_dt, interval="30m")
        
        if df.empty or len(df) < 2:
            st.warning("⚠️ 指定した期間に十分なデータがありません。")
        else:
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            # 統計計算 (σ)
            df['Range'] = df['High'] - df['Low']
            window = 72
            mean_r = df['Range'].rolling(window, min_periods=1).mean()
            std_r = df['Range'].rolling(window, min_periods=1).std()
            
            df['Vol_Factor'] = ((df['Range'] - mean_r) / std_r).clip(lower=0)
            df['Direction'] = np.sign(df['Close'] - df['Open'])
            
            # War Map計算
            bins = np.linspace(float(df['Low'].min()), float(df['High'].max()), 100)
            labels = bins[:-1] + (bins[1] - bins[0]) / 2
            v_profile, buy_spike, sell_spike = np.zeros(len(labels)), np.zeros(len(labels)), np.zeros(len(labels))
            
            for _, row in df.iterrows():
                vol, factor = float(row['Volume']), float(row['Vol_Factor'])
                mask = (labels >= float(row['Low'])) & (labels <= float(row['High']))
                count = np.sum(mask)
                if count == 0: continue
                
                v_profile[mask] += (vol / count)
                if factor > spike_threshold:
                    val = (vol * factor / count)
                    if row['Direction'] >= 0: buy_spike[mask] += val
                    else: sell_spike[mask] += val
            
            # 可視化
            fig, ax = plt.subplots(figsize=(10, 8))
            bin_w = bins[1] - bins[0]
            ax.barh(labels, v_profile, height=bin_w*0.8, color='gray', alpha=0.2, label='Volume')
            ax.barh(labels, buy_spike, height=bin_w*0.8, color='blue', alpha=0.6, label='Buy Panic')
            ax.barh(labels, -sell_spike, height=bin_w*0.8, color='red', alpha=0.6, label='Sell Panic')
            
            curr = float(df['Close'].iloc[-1])
            ax.axhline(y=curr, color='green', linestyle='--', label=f'Current: {curr:,.0f}')
            
            ax.set_title(f"War Map: {ticker}")
            ax.legend()
            st.pyplot(fig)
