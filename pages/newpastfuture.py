import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import streamlit as st

# ページの設定
st.set_page_config(page_title="日経225 ボリンジャーバンド未来予測", layout="wide")
st.title("🔍 日経225 ボリンジャーバンド予測シミュレーター")

# ==========================================
# 1. データのダウンロードと【最新1日の独立追加ロジック】
# ==========================================
@st.cache_data(ttl=3600)  # 1時間キャッシュして高速化
def load_data():
    ticker = yf.Ticker("^N225")
    df_global = ticker.history(period="2y", interval="1d")
    
    if df_global.index.tz is not None:
        df_global.index = df_global.index.tz_convert('Asia/Tokyo')
        
    try:
        latest_price = ticker.fast_info['last_price']
        if not df_global.empty and latest_price is not None:
            last_date = df_global.index[-1]
            today_date = pd.Timestamp.now(tz='Asia/Tokyo').normalize()
            if today_date.date() <= last_date.date():
                today_date = last_date + pd.Timedelta(days=1)
            
            new_row = pd.DataFrame(
                [[float(latest_price)] * len(df_global.columns)], 
                columns=df_global.columns, 
                index=[today_date]
            )
            df_global = pd.concat([df_global, new_row])
    except Exception:
        pass
        
    close_series = df_global['Close'].dropna()
    return close_series.index, close_series.values

try:
    global_dates, global_data = load_data()
except Exception as e:
    st.error(f"データの取得に失敗しました: {e}")
    st.stop()

# ==========================================
# 2. サイドバー機能（基準日を決める）
# ==========================================
st.sidebar.header("設定項目")
過去へのタイムワープ_日数 = st.sidebar.slider(
    "過去へのタイムワープ（日数）", 
    min_value=1, 
    max_value=200, 
    value=1, 
    step=1
)

target_idx = len(global_data) - 過去へのタイムワープ_日数

if target_idx < 25:
    st.sidebar.warning("⚠️ 過去に遡りすぎです。スライダーの数値を小さくしてください。")
else:
    base_date_str = global_dates[target_idx].strftime('%Y-%m-%d')
    sub_data = global_data[:target_idx + 1]
    
    # 計算処理
    df_calc = pd.Series(sub_data)
    ma25_series = df_calc.rolling(window=25).mean().values
    std25_series = df_calc.rolling(window=25).std().values
    
    current_ma = ma25_series[-1]
    current_std = std25_series[-1]
    prev_ma = ma25_series[-2] if len(ma25_series) > 1 else current_ma
    drift = current_ma - prev_ma

    # 画面を2カラム（左右半分）に分割してグラフを並べる
    col1, col2 = st.columns(2)

    # ==========================================
    # 📸 左画面：1枚目のグラフ（確定データ固定）
    # ==========================================
    with col1:
        st.subheader(f"1. 基準日チャート [ 基準日: {base_date_str} ]")
        fig1, ax1 = plt.subplots(figsize=(10, 4.5))
        
        plot_start = max(0, target_idx - 40)
        display_data = global_data[plot_start:target_idx + 1]
        display_dates = global_dates[plot_start:target_idx + 1]
        display_ma = ma25_series[plot_start:target_idx + 1]
        display_std = std25_series[plot_start:target_idx + 1]
        
        for i in range(1, 4):
            ax1.fill_between(display_dates, display_ma - i*display_std, display_ma + i*display_std, 
                             color='blue', alpha=0.12 - (i * 0.03))
            
        ax1.plot(display_dates, display_data, color='black', marker='o', label='Actual Price({latest_val:,.2f}円)')
        ax1.plot(display_dates, display_ma, color='blue', linewidth=2, label='25MA')
        ax1.grid(True)
        ax1.legend(loc='upper left')
        plt.xticks(rotation=15)
        st.pyplot(fig1)

    # ==========================================
    # 🔮 右画面：2枚目のグラフ（未来予測）
    # ==========================================
    ma_1d = current_ma + drift * 1
    ma_5d = current_ma + drift * 5
    
    with col2:
        st.subheader("2. 未来予測バンド")
        fig2, ax2 = plt.subplots(figsize=(10, 4.5))
        
        future_days = np.array([0, 1, 5])
        future_ma_points = np.array([current_ma, ma_1d, ma_5d])
        
        for i in range(1, 4):
            ax2.fill_between(future_days, future_ma_points - i*current_std, future_ma_points + i*current_std, 
                             color='red', alpha=0.12 - (i * 0.03))
            
        ax2.plot(future_days, future_ma_points, color='blue', linestyle='--', marker='s', label='Predicted 25MA')
        ax2.plot(0, global_data[target_idx], color='black', marker='o', markersize=10, label='Current Price')
        
        ax2.set_xticks([0, 1, 5])
        ax2.set_xticklabels(['Today (0)', '1 Day After', '5 Days After'])
        ax2.grid(True)
        ax2.legend(loc='upper left')
        st.pyplot(fig2)

    # ==========================================
    # 📋 最下部：予測価格帯ボード（シンプル表）
    # ==========================================
    st.markdown("---")
    st.subheader(f"📊 【最新予測価格帯ボード】 基準日: {base_date_str}")
    
    prediction_data = {
        "項目": ["+3σ", "+2σ", "+1σ", "予測25MA", "-1σ", "-2σ", "-3σ"],
        "1日後の価格 (円)": [
            ma_1d + 3*current_std, ma_1d + 2*current_std, ma_1d + 1*current_std,
            ma_1d,
            ma_1d - 1*current_std, ma_1d - 2*current_std, ma_1d - 3*current_std
        ],
        "5日後の価格 (円)": [
            ma_5d + 3*current_std, ma_5d + 2*current_std, ma_5d + 1*current_std,
            ma_5d,
            ma_5d - 1*current_std, ma_5d - 2*current_std, ma_5d - 3*current_std
        ]
    }
    df_prediction = pd.DataFrame(prediction_data).set_index("項目")
    
    # Streamlitの機能で、あの変な検索箱を出さずにスッキリと綺麗な表を全画面幅で表示
    st.dataframe(df_prediction.style.format("{:,.2f}"), use_container_width=True)
    
