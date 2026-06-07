import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd

st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart (Daily Enhanced)")

@st.cache_data(ttl=60)
def get_daily_data():
    ticker = yf.Ticker("NIY=F")
    
    # 過去1年以上の最高値を捕捉するため、2年分のデータを取得
    df = ticker.history(period="2y", interval="1d")
    
    # 【リアルタイム仮終値反映】
    # 場中は最新価格を取得し、データフレームの「一番最後の行（今日）」の終値に即座に上書きする
    try:
        latest_price = ticker.fast_info['last_price']
        if not df.empty and latest_price is not None:
            df.iloc[-1, df.columns.get_loc('Close')] = float(latest_price)
    except Exception:
        pass  # 取得失敗時はそのままの確定終値を使用
        
    if df.index.tz is not None:
        df.index = df.index.tz_convert('Asia/Tokyo')
    return df

# データ取得
df = get_daily_data()

if df.empty:
    st.error("データの取得に失敗しました。")
else:
    last_updated = df.index[-1]
    current = df['Close'].iloc[-1].item()

    # 【味噌・完全改修】
    # 最新価格が上書きされたデータフレームの「直近252営業日（約1年）」の中から最大値を探す。
    # これにより、現在値（current）が過去の最高値を1円でも超えた瞬間、
    # この p50 自体が自動的に「今の現在値」に書き換わります（天井のリアルタイム自己更新）。
    window_1year = min(252, len(df))
    p50 = df['Close'].iloc[-window_1year:].max().item()

    # 標準偏差: 直近25日間のデータから取得
    std = df['Close'].rolling(window=25, min_periods=5).std().iloc[-1].item()

    # 各Pレベルの定義 (-1σ 〜 -4σ)
    price_levels = {
        "P50": p50,
        "P48": p50 - 1 * std,
        "P45": p50 - 2 * std,
        "P40": p50 - 3 * std,
        "P35": p50 - 4 * std
    }

    # Dev（現在偏差）の計算ロジック
    # 現在値がP50をぶち抜いて「current == p50」の状態になると、
    # 以下の数式により current_dev は自動的に「正確に 50.0 」にロックされます。
    # P50以上は絶対に存在しないため、これ以上の条件分岐は不要になります。
    if current >= price_levels["P48"]:
        div = p50 - price_levels["P48"]
        current_dev = 48 + 2 * (current - price_levels["P48"]) / div if div != 0 else 50.0
    elif current >= price_levels["P45"]:
        div = price_levels["P48"] - price_levels["P45"]
        current_dev = 45 + 3 * (current - price_levels["P45"]) / div if div != 0 else 45.0
    elif current >= price_levels["P40"]:
        div = price_levels["P45"] - price_levels["P40"]
        current_dev = 40 + 5 * (current - price_levels["P40"]) / div if div != 0 else 40.0
    else:
        div = price_levels["P40"] - price_levels["P35"]
        current_dev = 35 + 5 * (current - price_levels["P35"]) / div if div != 0 else 35.0

    # グラフ描画（画面に出すのは直近5日分）
    fig, ax = plt.subplots(figsize=(16, 6))
    tail_df = df.tail(5)
    x_labels = [idx.strftime('%m/%d') for idx in tail_df.index]
    
    # 5日間の終値プロット
    ax.plot(range(len(tail_df)), tail_df['Close'], color='black', lw=2.5, marker='o')

    # 各Pレベルの水平破線
    colors = {'P50': 'red', 'P48': 'green', 'P45': 'blue', 'P40': 'brown', 'P35': 'gray'}
    for label, price in price_levels.items():
        ax.axhline(price, color=colors[label], linestyle='--', alpha=0.7, lw=1.5)
        # グラフ右端に各ラインのラベルと価格を表示
        ax.text(len(tail_df) - 0.4, price, f" {label} ({price:.0f})", color=colors[label], va='center', weight='bold')

    # 最新日の縦破線（右端の今日を表す位置）
    ax.axvline(x=len(tail_df)-1, color='orange', linestyle=':', lw=2)

    # グラフのレイアウト調整
    ax.set_xticks(range(len(tail_df)))
    ax.set_xticklabels(x_labels, fontsize=11)
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.set_title("NIY=F 5-Day Trend & P-Levels", fontsize=14)
    
    st.pyplot(fig, use_container_width=True)

    # タイムスタンプ
    st.write(f"**Data Last Updated (リアルタイム仮終値反映):** {last_updated.strftime('%Y-%m-%d %H:%M')} JST")
    
    st.write("---")
    
    # 【パネル部分】7列のメトリック表示
    st.markdown("### 📊 戦略ステータス・パネル")
    cols = st.columns(7)
    cols[0].metric("Current", f"{current:.0f}")
    cols[1].metric("Dev", f"{current_dev:.1f}")
    cols[2].metric("P50", f"{p50:.0f}")
    cols[3].metric("P48", f"{price_levels['P48']:.0f}")
    cols[4].metric("P45", f"{price_levels['P45']:.0f}")
    cols[5].metric("P40", f"{price_levels['P40']:.0f}")
    cols[6].metric("P35", f"{price_levels['P35']:.0f}")
