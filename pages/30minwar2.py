import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(layout="wide")
st.title("Market War Map: Pro Scalping Terminal")

# サイドバー
with st.sidebar:
    st.header("Settings")
    ticker = st.text_input("Ticker Symbol", value="NIY=F")
    
    # 期間指定：デフォルトは直近3日
    today = datetime.now()
    default_start = today - timedelta(days=3)
    date_range = st.date_input("Date Range", value=(default_start, today))
    
    # 標準偏差ベースの感度（Zスコア）
    # 2.0σなら約2.3%の確率でしか起きない異常値
    spike_threshold = st.slider("Panic Spike Sensitivity (σ)", 1.0, 3.0, 2.0, 0.1)
    
    run_btn = st.button("Analyze Now")

if run_btn and len(date_range) == 2:
    start_date, end_date = date_range
    
    with st.spinner(f"Loading {ticker}..."):
        # 30分足でデータ取得
        df = yf.download(ticker, start=start_date, end=end_date, interval="30m")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # ロジック：価格幅の変動
        df['Range'] = df['High'] - df['Low']
        
        # 過去72本（30分足×72＝36時間分）で統計をとる
        window = 72
        mean_range = df['Range'].rolling(window).mean()
        std_range = df['Range'].rolling(window).std()
        
        # Zスコアの算出（これが今回の肝）
        # 過去の平均からどれだけ標準偏差分外れているか
        df['Vol_Factor'] = (df['Range'] - mean_range) / std_range
        
        # 可視化
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # パニック判定（しきい値以上の場所をプロット）
        is_panic = df['Vol_Factor'] > spike_threshold
        
        # 出来高と価格帯の可視化ロジックは以前のものをベースに調整
        # (簡単のためここでは散布図で表現します)
        ax.scatter(df.index[~is_panic], df['Close'][~is_panic], color='skyblue', alpha=0.3, label='Normal')
        ax.scatter(df.index[is_panic], df['Close'][is_panic], color='red', alpha=0.8, label='Panic Spike')
        
        ax.set_title(f"Market War Map: {ticker} (Threshold: {spike_threshold}σ)")
        ax.legend()
        st.pyplot(fig)
        
        st.write(f"Analyze finished. Data points: {len(df)}")
      
