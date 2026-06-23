import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# 画面をワイドモードに設定
st.set_page_config(layout="wide")
st.title("NIY=F Strategic 8-Hour 75-Window Chart")

@st.cache_data(ttl=60)
def get_processed_data():
    ticker = yf.Ticker("NIY=F")
    
    # 1. 8時間足を綺麗に作るため、yfinanceの最大期間である1時間足を2年分取得
    df_1h = ticker.history(period="2y", interval="1h")
    
    if df_1h.empty:
        return pd.DataFrame()
        
    # 日本時間（JST）に変換
    if df_1h.index.tz is not None:
        df_1h.index = df_1h.index.tz_convert('Asia/Tokyo')
        
    # 2. 8時間足の終値ベースに集約
    df_8h = df_1h['Close'].resample('8h').last()
    
    # 【欠損日の除外】土日や祝日などのデータが入っていない空行を完全に排除
    df_8h = df_8h.dropna().to_frame()
    
    # 3. 【リアルタイム仮終値反映】
    # 場中の最新価格を反映させるため、現在のリアルタイム価格を最後の行に強制上書き
    try:
        latest_price = ticker.fast_info['last_price']
        if latest_price is not None:
            df_8h.iloc[-1, df_8h.columns.get_loc('Close')] = float(latest_price)
    except Exception:
        pass
        
    return df_8h

# データ取得の実行
df = get_processed_data()

if df.empty:
    st.error("データの取得に失敗しました。")
else:
    # タイムスタンプ（凡例用）と現在の最新価格
    last_updated = df.index[-1]
    current = df['Close'].iloc[-1].item()

    # 4. パラメータの定義（1日3本計算ベース）
    window_1year = 1095  # 過去約1年分の8時間足（3本 × 365日）
    window_std = 75      # 過去25日分の8時間足（3本 × 25日）

    # 5. 基準となる過去1年最高値(P50)の算出
    actual_window_1y = min(window_1year, len(df))
    p50 = df['Close'].iloc[-actual_window_1y:].max().item()

    # 6. 標準偏差(std)の算出
    std = df['Close'].rolling(window=window_std, min_periods=5).std().iloc[-1].item()

    # 7. 新・Pレベルの定義（等間隔4刻み・価格はすべて整数）
    # 小数点以下を切り捨てて整数型(int)にキャスト
    price_levels = {
        "P50": int(round(p50)),
        "P46": int(round(p50 - 0.5 * std)),
        "P42": int(round(p50 - 1.0 * std)),
        "P38": int(round(p50 - 1.5 * std)),
        "P34": int(round(p50 - 2.0 * std)),
        "P30": int(round(p50 - 2.5 * std))
    }

    # 8. 新・偏差値（Dev）計算ロジック（等間隔の美しい1行数式）
    # Devのみこだわり通り「小数点以下あり（1桁）」で計算
    if std > 0:
        current_dev = 50.0 + 4.0 * ((current - p50) / (0.5 * std))
    else:
        current_dev = 50.0

    # P50（最高値）以上にはならない仕様のため、上限を50.0にロック
    if current_dev > 50.0:
        current_dev = 50.0

    # 9. グラフ描画（時刻は気にせず、直近15本分のうねりを表示）
    fig, ax = plt.subplots(figsize=(16, 6))
    tail_df = df.tail(15) # 直近15本（5日分相当）
    
    # 終値ラインプロット（時刻ノイズを消し、インデックス番号でシンプルに結ぶ）
    ax.plot(range(len(tail_df)), tail_df['Close'], color='black', lw=2.5, marker='o', label='8H Close')

    # 各Pレベルの水平破線をチャートに配置
    colors = {'P50': 'red', 'P46': 'orange', 'P42': 'green', 'P38': 'blue', 'P34': 'purple', 'P30': 'gray'}
    for label, price in price_levels.items():
        ax.axhline(price, color=colors[label], linestyle='--', alpha=0.6, lw=1.5)
        # 右端にラベルと整数化された価格を表示
        ax.text(len(tail_df) - 0.4, price, f" {label} ({price})", color=colors[label], va='center', weight='bold', fontsize=10)

    # 現在の最新の足（一番右端）に縦線を引く
    ax.axvline(x=len(tail_df)-1, color='gold', linestyle=':', lw=2)

    # グラフの装飾とレイアウト（X軸は日付表示のみでスッキリ）
    x_labels = [idx.strftime('%m/%d') for idx in tail_df.index]
    ax.set_xticks(range(len(tail_df)))
    ax.set_xticklabels(x_labels, fontsize=10, rotation=15)
    ax.grid(True, linestyle=':', alpha=0.5)
    
    # 凡例にデータ最終取得時刻を明記してマウント
    ax.set_title(f"NIY=F 15-Window Trend & Strategic P-Levels", fontsize=14, weight='bold')
    ax.legend([f"Data Fetched: {last_updated.strftime('%Y-%m-%d %H:%M')} JST"], loc='upper left')
    
    st.pyplot(fig, use_container_width=True)
    
    st.write("---")
    
    # 10. 【パネル部分】新仕様に合わせた8列のメトリック表示
    st.markdown("### 📊 戦略ステータス・パネル（8-Hour Version）")
    cols = st.columns(8)
    cols[0].metric("Current", f"{int(round(current))}") # 現在値も整数
    cols[1].metric("Dev", f"{current_dev:.1f}")         # Devは小数点1桁キープ！
    cols[2].metric("P50", f"{price_levels['P50']}")
    cols[3].metric("P46", f"{price_levels['P46']}")
    cols[4].metric("P42", f"{price_levels['P42']}")
    cols[5].metric("P38", f"{price_levels['P38']}")
    cols[6].metric("P34", f"{price_levels['P34']}")
    cols[7].metric("P30", f"{price_levels['P30']}")
  
