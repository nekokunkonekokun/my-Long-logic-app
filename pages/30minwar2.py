import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(layout="wide", page_title="Market War Map")
st.title("Market War Map: Pro Scalping Terminal")

with st.sidebar:
    st.header("Settings")
    ticker = st.text_input("Ticker Symbol", value="NIY=F")
    target_date = st.date_input("Target Date", value=datetime.now().date())
    
    # 0.5時間刻みで24時間まで調整可能
    offset_options = [i * 0.5 for i in range(49)]
    time_offset = st.select_slider("Time Offset (Hours)", options=offset_options, value=9.0)
    
    spike_threshold = st.slider("Panic Spike Sensitivity (σ)", 1.0, 3.0, 2.0, 0.1)
    run_btn = st.button("Analyze Now")

if run_btn:
    # 日本時間ベースでの取得期間計算
    start_dt = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=time_offset)
    end_dt = start_dt + timedelta(hours=24.1) # 24時間＋余裕分
    
    with st.spinner("Loading & Processing..."):
        df = yf.download(ticker, start=start_dt, end=end_dt, interval="30m")
        
        # データチェック
        if df.empty or len(df) < 2:
            st.warning("⚠️ 指定した期間に取引データがありません。")
        else:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            # 各種計算
            df['Range'] = df['High'] - df['Low']
            window = 72
            mean_r = df['Range'].rolling(window, min_periods=1).mean()
            std_r = df['Range'].rolling(window, min_periods=1).std()
            
            # Vol_Factor (Zスコア)
            df['Vol_Factor'] = (df['Range'] - mean_r) / std_r
            df['Vol_Factor'] = df['Vol_Factor'].clip(lower=0)
            
            # 方向性の判定 (Close - Open)
            df['Direction'] = np.sign(df['Close'] - df['Open'])
            
            # ビンの作成
            bins = np.linspace(float(df['Low'].min()), float(df['High'].max()), 100)
            labels = bins[:-1] + (bins[1] - bins[0]) / 2
            
            v_profile = np.zeros(len(labels))
            buy_spike = np.zeros(len(labels))
            sell_spike = np.zeros(len(labels))
            
            for _, row in df.iterrows():
                vol = float(row['Volume'])
                factor = float(row['Vol_Factor'])
                mask = (labels >= float(row['Low'])) & (labels <= float(row['High']))
                count = np.sum(mask)
                if count == 0: continue
                
                v_profile[mask] += (vol / count)
                if factor > spike_threshold:
                    val = (vol * factor / count)
                    if row['Direction'] >= 0: # 買いパニック
                        buy_spike[mask] += val
                    else: # 売りパニック
                        sell_spike[mask] += val
            
            # プロット
            fig, ax = plt.subplots(figsize=(10, 7))
            bin_w = bins[1] - bins[0]
            ax.barh(labels, v_profile, height=bin_w*0.8, color='gray', alpha=0.2, label='Volume')
            ax.barh(labels, buy_spike, height=bin_w*0.8, color='blue', alpha=0.6, label='Buy Panic')
            ax.barh(labels, -sell_spike, height=bin_w*0.8, color='red', alpha=0.6, label='Sell Panic')
            
            current_price = float(df['Close'].iloc[-1])
            ax.axvline(x=0, color='black', linewidth=1)
            ax.axhline(y=current_price, color='green', linestyle='--', label=f'Current: {current_price:,.0f}')
            
            ax.set_title(f"War Map: {ticker} (Threshold: {spike_threshold}σ)")
            ax.legend()
            st.pyplot(fig)
