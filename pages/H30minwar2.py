import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, time, timedelta

# 1. スマホ向けにレイアウトを「centered」に設定
st.set_page_config(layout="centered", page_title="War Map Mobile")
st.title("📱 Market War Map: Mobile")

# 2. サイドバーではなく、画面上部に折りたたみ式設定を配置（スマホで押しやすくするため）
with st.expander("⚙️ 分析設定 (タップして開閉)", expanded=True):
    ticker = st.text_input("銘柄コード", value="NIY=F")
    
    today = datetime.now().date()
    # スマホは2カラムにすると崩れやすいため1カラムで縦に並べる
    start_date = st.date_input("開始日", value=today - timedelta(days=5))
    a_start = st.slider("開始時間 (時)", 0, 24, 0)
    
    end_date = st.date_input("終了日", value=today)
    b_end = st.slider("終了時間 (時)", 0, 24, 24)
    
    spike_threshold = st.slider("感度 (σ)", 1.0, 3.0, 2.0, 0.1)
    
    # モバイルで押しやすいよう、ボタンを大きく
    run_btn = st.button("🔥 戦況を分析する", use_container_width=True)

if run_btn:
    start_dt = datetime.combine(start_date, time(hour=a_start))
    if b_end == 24:
        end_dt = datetime.combine(end_date + timedelta(days=1), time(0, 0))
    else:
        end_dt = datetime.combine(end_date, time(hour=b_end))
    
    with st.spinner("データを解析中..."):
        df = yf.download(ticker, start=start_dt, end=end_dt, interval="30m")
        
        if df.empty or len(df) < 2:
            st.warning("⚠️ 指定期間のデータが足りません。")
        else:
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            # データの安全な処理
            df['Volume'] = df['Volume'].fillna(0)
            df['Range'] = df['High'] - df['Low']
            
            window = 72
            mean_r = df['Range'].rolling(window, min_periods=1).mean()
            std_r = df['Range'].rolling(window, min_periods=1).std()
            
            df['Vol_Factor'] = ((df['Range'] - mean_r) / std_r).clip(lower=0)
            df['Direction'] = np.sign(df['Close'] - df['Open'])
            
            # War Map 計算
            bins = np.linspace(float(df['Low'].min()), float(df['High'].max()), 80) # スマホ用にビン数を少し間引く(100→80)
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
            
            # 3. スマホの縦長画面に合わせたプロットサイズ (横6 : 縦10)
            fig, ax = plt.subplots(figsize=(6, 10))
            plt.style.use('dark_background') # スマホで見やすいダークモード風（背景白なら削除してください）
            fig.patch.set_facecolor('#0e1117') # Streamlitのデフォルトダーク背景に合わせる
            ax.set_facecolor('#0e1117')
            
            bin_w = bins[1] - bins[0]
            ax.barh(labels, v_profile, height=bin_w*0.8, color='gray', alpha=0.3, label='Volume')
            ax.barh(labels, buy_spike, height=bin_w*0.8, color='#00FFFF', alpha=0.7, label='Buy Panic') # スマホで映えるネオンカラー
            ax.barh(labels, -sell_spike, height=bin_w*0.8, color='#FF3333', alpha=0.7, label='Sell Panic')
            
            curr = float(df['Close'].iloc[-1])
            ax.axhline(y=curr, color='#00FF00', linestyle='--', linewidth=2, label=f'Current: {curr:,.0f}')
            
            ax.set_title(f"War Map: {ticker}", fontsize=14, color='white')
            ax.legend(loc='upper right', fontsize=10)
            ax.tick_params(colors='white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            # 4. グラフを画面幅いっぱいに表示
            st.pyplot(fig, use_container_width=True)
            
            # モバイル用の簡易サマリー表示
            st.chat_message("assistant").write(f"現在の価格: **{curr:,.0f}** ⚠️赤（売り圧力）と青（買い圧力）の衝突ゾーンに注意してください。")
