import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(layout="wide")
st.title("Market War Map: Pro Scalping Terminal (σ-Logic)")

# サイドバーによる入力
with st.sidebar:
    st.header("Settings")
    ticker = st.text_input("Ticker Symbol", value="NIY=F")
    
    # 期間指定（デフォルトは過去3日間）
    today = datetime.now()
    default_start = today - timedelta(days=3)
    date_range = st.date_input("Date Range", value=(default_start, today))
    
    # スパイク感度をσ（標準偏差）単位で指定
    spike_threshold = st.slider("Panic Spike Sensitivity (σ)", 1.0, 3.0, 2.0, 0.1)
    
    run_btn = st.button("Analyze Now")

if run_btn and len(date_range) == 2:
    start_date, end_date = date_range
    
    with st.spinner(f"Loading {ticker}..."):
        # 30分足でデータ取得
        df = yf.download(ticker, start=start_date, end=end_date, interval="30m")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 価格幅の計算
        df['Range'] = df['High'] - df['Low']
        
        # 統計的ロジック: 過去72本（36時間分）の平均と標準偏差を使用
        window = 72
        mean_r = df['Range'].rolling(window).mean()
        std_r = df['Range'].rolling(window).std()
        
        # Zスコアの算出 (標準偏差の何倍動いたか)
        # 負の値は0に丸め、異常値のみを抽出
        df['Vol_Factor'] = (df['Range'] - mean_r) / std_r
        df['Vol_Factor'] = df['Vol_Factor'].clip(lower=0)
        
        # 可視化ロジック (ビンの作成)
        bins = np.linspace(float(df['Low'].min()), float(df['High'].max()), 100)
        labels = bins[:-1] + (bins[1] - bins[0]) / 2
        
        v_profile = np.zeros(len(labels))
        p_profile = np.zeros(len(labels))
        
        # 各足の出来高を価格帯に振り分ける
        for _, row in df.iterrows():
            vol = float(row['Volume'])
            factor = float(row['Vol_Factor'])
            mask = (labels >= float(row['Low'])) & (labels <= float(row['High']))
            count = np.sum(mask)
            if count == 0: continue
            
            v_profile[mask] += (vol / count)
            # 標準偏差ベースの感度を超えたらパニックスパイクとして加算
            if factor > spike_threshold:
                p_profile[mask] += (vol * factor / count)
        
        # プロット
        fig, ax = plt.subplots(figsize=(10, 6))
        bin_w = bins[1] - bins[0]
        ax.barh(labels, v_profile, height=bin_w*0.8, color='skyblue', alpha=0.4, label='Volume')
        ax.barh(labels, p_profile, height=bin_w*0.8, color='red', alpha=0.6, label='Panic Spike')
        
        current_price = float(df['Close'].iloc[-1])
        ax.axhline(y=current_price, color='black', linewidth=2, label=f'Current: {current_price:,.0f}')
        
        ax.set_title(f"War Map: {ticker} (Threshold: {spike_threshold}σ)")
        ax.legend()
        st.pyplot(fig)
