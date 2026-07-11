import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, time

# ページ設定
st.set_page_config(layout="wide", page_title="Market War Map")
st.title("Market War Map: Pro Scalping Terminal")

with st.sidebar:
    st.header("Settings")
    ticker = st.text_input("Ticker Symbol", value="NIY=F")
    
    # 複数日の期間指定
    default_start = datetime.now().date() - timedelta(days=5)
    date_range = st.date_input("Date Range", value=(default_start, datetime.now().date()))
    
    # オフセット調整 (期間全体をスライド)
    offset_options = [i * 0.5 for i in range(49)]
    time_offset = st.select_slider("Time Offset (Hours)", options=offset_options, value=9.0)
    
    spike_threshold = st.slider("Panic Spike Sensitivity (σ)", 1.0, 3.0, 2.0, 0.1)
    run_btn = st.button("Analyze Now")

if run_btn and len(date_range) == 2:
    # オフセットを適用して開始・終了時間を決定
    start_dt = datetime.combine(date_range[0], time.min) + timedelta(hours=time_offset)
    end_dt = datetime.combine(date_range[1], time.max) + timedelta(hours=time_offset)
    
    with st.spinner("Processing War Map..."):
        df = yf.download(ticker, start=start_dt, end=end_dt, interval="30m")
        
        if df.empty or len(df) < 2:
            st.warning("⚠️ 指定した期間・時間帯には取引データがありません。スライダーや日付を見直してください。")
        else:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            # 統計計算 (期間全体を通した移動平均/標準偏差)
            df['Range'] = df['High'] - df['Low']
            window = 72 # 36時間分
            mean_r = df['Range'].rolling(window, min_periods=1).mean()
            std_r = df['Range'].rolling(window, min_periods=1).std()
            
            # Zスコアと方向性
            df['Vol_Factor'] = ((df['Range'] - mean_r) / std_r).clip(lower=0)
            df['Direction'] = np.sign(df['Close'] - df['Open'])
            
            # ビンの作成 (期間内の全価格をカバー)
            bins = np.linspace(float(df['Low'].min()), float(df['High'].max()), 100)
            labels = bins[:-1] + (bins[1] - bins[0]) / 2
            
            v_profile = np.zeros(len(labels))
            buy_spike = np.zeros(len(labels))
            sell_spike = np.zeros(len(labels))
            
            # プロファイル作成
            for _, row in df.iterrows():
                vol = float(row['Volume'])
                factor = float(row['Vol_Factor'])
                mask = (labels >= float(row['Low'])) & (labels <= float(row['High']))
                count = np.sum(mask)
                if count == 0: continue
                
                v_profile[mask] += (vol / count)
                if factor > spike_threshold:
                    val = (vol * factor / count)
                    if row['Direction'] >= 0:
                        buy_spike[mask] += val
                    else:
                        sell_spike[mask] += val
            
            # 可視化
            fig, ax = plt.subplots(figsize=(10, 8))
            bin_w = bins[1] - bins[0]
            ax.barh(labels, v_profile, height=bin_w*0.8, color='gray', alpha=0.2, label='Volume')
            ax.barh(labels, buy_spike, height=bin_w*0.8, color='blue', alpha=0.6, label='Buy Panic')
            ax.barh(labels, -sell_spike, height=bin_w*0.8, color='red', alpha=0.6, label='Sell Panic')
            
            curr = float(df['Close'].iloc[-1])
            ax.axhline(y=curr, color='black', linewidth=2, label=f'Last: {curr:,.0f}')
            
            ax.set_title(f"War Map: {ticker} ({date_range[0]} to {date_range[1]})")
            ax.legend()
            st.pyplot(fig)
