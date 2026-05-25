import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart (JP Yahoo! Hybrid)")

# --- 【手間ゼロ自動化】日本のYahoo!ファイナンスから最新値を引っこ抜く関数 ---
def get_jp_yahoo_future_price():
    try:
        # ユーザー様にご提示いただいた日本のYahoo!ファイナンスのURL
        url = "https://finance.yahoo.co.jp/quote/5040469.O?term=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 日本のYahoo!ファイナンスの「現在値」が表示されるクラス(長年不動の構造です)
        # ページ上部の大きな数字のエリアを特定
        price_element = soup.find("span", class_="_3rXWJKFI")
        if not price_element:
            # 万が一クラス名が変わった場合の予備ルート
            price_element = soup.find(attrs={"data-testid": "stock-price"})
            
        if price_element:
            price_text = price_element.text.replace(",", "").replace("円", "").strip()
            return float(price_text)
    except Exception as e:
        st.sidebar.warning(f"日本のYahoo!からの自動取得に失敗: {e}")
    return None

# 1. ベースとなる1時間足データをyfinanceから取得
df = yf.download("NIY=F", period="1y", interval="1h").dropna()
df.index = df.index.tz_convert('Asia/Tokyo')

# 2. 日本のYahoo!ファイナンスから動いている最新値を自動取得して上書き
realtime_price = get_jp_yahoo_future_price()
current_time_floored = pd.Timestamp.now(tz='Asia/Tokyo').floor('h')

if realtime_price:
    # 最後の行のCloseを、日本のYahoo!ファイナンスのリアルタイム価格に差し替える
    if current_time_floored in df.index:
        df.loc[current_time_floored, 'Close'] = realtime_price
    else:
        # 新しい時間枠（10:00台など）であれば新しい行として滑り込ませる
        new_row = pd.DataFrame({'Close': [realtime_price]}, index=[current_time_floored])
        df = pd.concat([df, new_row])
    is_realtime = True
else:
    is_realtime = False

# --- 以降の計算は共通 ---
max_price = df['Close'].max().item()
current = df['Close'].iloc[-1].item()  # 日本のYahoo!から取得した最新価格
std = df['Close'].rolling(window=575).std().iloc[-1].item()

# 各レベルの価格を算出し、現在の位置を線形補間する
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

# ステータス表示
if is_realtime:
    st.success(f"🚀 日本のYahoo!ファイナンス（大証先物）からリアルタイム自動補正中: {current:.0f}")
else:
    st.warning(f"⚠️ 自動取得に失敗したため、yfinanceの遅延データ（{current:.0f}）を表示中")

st.pyplot(fig)

