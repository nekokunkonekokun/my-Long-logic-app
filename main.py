import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart")

# 1. 1時間足データを取得（dropnaで不完全な行を弾き、最新の確定/暫定値を末尾にする）
df = yf.download("NIY=F", period="1y", interval="1h").dropna()
df.index = df.index.tz_convert('Asia/Tokyo')

# 2. 取得できた最後の行を「現在のリアルタイム値」と仮定して各種計算を行う
max_price = df['Close'].max().item()
current = df['Close'].iloc[-1].item()  # 取得できた最新の価格
std = df['Close'].rolling(window=575).std().iloc[-1].item()

# 各レベルの価格を算出し、現在の位置を線形補間する
levels = {"P50": 0, "P48": 1, "P45": 2, "P40": 3, "P35": 4}
price_levels = {k: max_price - (v * std) for k, v in levels.items()}

# 現在価格がどのレベル間にあるか判定（P35以下もカバーする安全設計に修正）
if current >= price_levels["P48"]:
    current_dev = 48 + (50 - 48) * (current - price_levels["P48"]) / (max_price - price_levels["P48"])
elif current >= price_levels["P45"]:
    current_dev = 45 + (48 - 45) * (current - price_levels["P45"]) / (price_levels["P48"] - price_levels["P45"])
elif current >= price_levels["P40"]:
    current_dev = 40 + (45 - 40) * (current - price_levels["P40"]) / (price_levels["P45"] - price_levels["P40"])
else:
    current_dev = 35 + (40 - 35) * (current - price_levels["P35"]) / (price_levels["P40"] - price_levels["P35"])

# X軸の準備（直近168本＝シカゴの約1.4週間分）
tail_df = df.tail(168)
x = range(len(tail_df))
dates = tail_df.index.strftime('%m/%d %H:00').tolist() # 何時のデータか分かるようにフォーマット変更

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

# データの最終更新日時（このチャートが「いつの時点」のデータで作られているか）を明示
last_update = df.index[-1].strftime('%Y/%m/%d %H:%M:%S')
st.info(f"📊 チャート生成基準時刻 (日本時間): {last_update}")

st.pyplot(fig)
