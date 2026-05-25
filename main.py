import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart (Fully Automated)")

# 1. 過去のボラティリティ計算用に1時間足を取得
df_1h = yf.download("NIY=F", period="1y", interval="1h").dropna()
df_1h.index = df_1h.index.tz_convert('Asia/Tokyo')

# 2. 【完全自動】リアルタイム補完用に1分足を取得し、現在の「1時間足の枠」へ自動集計してドッキング
try:
    df_1m = yf.download("NIY=F", period="1d", interval="1m").dropna()
    if not df_1m.empty:
        # 1分足の最新時刻と最新価格を取得
        latest_1m_time = df_1m.index[-1].tz_convert('Asia/Tokyo')
        realtime_price = df_1m['Close'].iloc[-1].item()
        
        # 1分足の時間を「1時間単位（毎時0分）」に自動変換（例: 09:35 -> 09:00）
        current_hour_bin = latest_1m_time.floor('h')
        
        if current_hour_bin in df_1h.index:
            # すでに1時間足にその時間枠があれば、1分足の最新値で上書き（現在進行中の足のリアルタイム更新）
            df_1h.loc[current_hour_bin, 'Close'] = realtime_price
        elif current_hour_bin > df_1h.index[-1]:
            # まだ1時間足にデータが届いていない新しい時間帯なら、自動で新しい行を作って結合
            new_row = pd.DataFrame({'Close': [realtime_price]}, index=[current_hour_bin])
            df_1h = pd.concat([df_1h, new_row])
except Exception as e:
    st.sidebar.warning(f"リアルタイム自動補完スキップ（遅延データを使用します）: {e}")

# --- 以降の計算はすべて自動で最新値（1分足由来）ベースになります ---
df = df_1h # 名前を統一
max_price = df['Close'].max().item()
current = df['Close'].iloc[-1].item() # 1分足から自動抽合された「本当の現在値」
std = df['Close'].rolling(window=575).std().iloc[-1].item()

# 各レベルの価格を算出
levels = {"P50": 0, "P48": 1, "P45": 2, "P40": 3, "P35": 4}
price_levels = {k: max_price - (v * std) for k, v in levels.items()}

# 現在価格の階層判定（安全設計）
if current >= price_levels["P48"]:
    current_dev = 48 + (50 - 48) * (current - price_levels["P48"]) / (max_price - price_levels["P48"])
elif current >= price_levels["P45"]:
    current_dev = 45 + (48 - 45) * (current - price_levels["P45"]) / (price_levels["P48"] - price_levels["P45"])
elif current >= price_levels["P40"]:
    current_dev = 40 + (45 - 40) * (current - price_levels["P40"]) / (price_levels["P45"] - price_levels["P40"])
else:
    current_dev = 35 + (40 - 35) * (current - price_levels["P35"]) / (price_levels["P40"] - price_levels["P35"])

# X軸の準備
tail_df = df.tail(168)
x = range(len(tail_df))
dates = tail_df.index.strftime('%m/%d %H:00').tolist()

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(x, tail_df['Close'], color='black', lw=1.2)

colors = {'P50': 'red', 'P48': 'green', 'P45': 'blue', 'P40': 'brown', 'P35': 'gray'}
for label, price in price_levels.items():
    ax.axhline(price, color=colors[label], linestyle='--', alpha=0.5)

panel_text = f"Current: {current:.0f}\nDev: {current_dev:.1f}\n" + \
             "\n".join([f"{k}: {p:.0f}" for k, p in price_levels.items()])
ax.text(0.02, 0.02, panel_text, transform=ax.transAxes, fontsize=9, 
        bbox=dict(facecolor='white', alpha=0.8), ha='left', va='bottom')

ax.xaxis.set_major_locator(ticker.MaxNLocator(8))
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda i, pos: dates[int(i)] if 0 <= int(i) < len(dates) else ""))
ax.grid(True, alpha=0.3)

# 最終データ時刻の自動表示
last_update = df.index[-1].strftime('%Y/%m/%d %H:%M:%S')
st.info(f"📊 システム自動連動時刻 (日本時間): {last_update}")

st.pyplot(fig)

