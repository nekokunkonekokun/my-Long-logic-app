import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import timedelta

# ページ設定
st.set_page_config(layout="wide")
st.title("NIY=F Strategic 3-Level Chart")

# セッション管理（高値更新ロジック用）
if 'p50_fixed' not in st.session_state:
    st.session_state.p50_fixed = 0.0

@st.cache_data(ttl=3600)
def get_data():
    df = yf.download("NIY=F", period="1y", interval="1h").dropna()
    df.index = df.index.tz_convert('Asia/Tokyo')
    return df

df = get_data()
current_max = df['Close'].max().item()

# 新高値が出たら更新（追従して固定）
if current_max > st.session_state.p50_fixed:
    st.session_state.p50_fixed = current_max

p50 = st.session_state.p50_fixed
std = df['Close'].rolling(window=575).std().iloc[-1].item()
current = df['Close'].iloc[-1].item()

# Pレベルの計算
price_levels = {
    "P50": p50, "P48": p50 - (1 * std), "P45": p50 - (2 * std),
    "P40": p50 - (3 * std), "P35": p50 - (4 * std)
}

# Dev計算
if current >= price_levels["P48"]:
    current_dev = 48 + (50 - 48) * (current - price_levels["P48"]) / (p50 - price_levels["P48"])
elif current >= price_levels["P45"]:
    current_dev = 45 + (48 - 45) * (current - price_levels["P45"]) / (price_levels["P48"] - price_levels["P45"])
else:
    current_dev = 40 + (45 - 40) * (current - price_levels["P40"]) / (price_levels["P45"] - price_levels["P40"])

# グラフ描画
tail_df = df.tail(168)
fig, ax = plt.subplots(figsize=(10, 9))

# 背景設定：全体は黒、グラフ内は白
fig.patch.set_facecolor('#0E1117')
ax.set_facecolor('white')

# メインプロット
ax.plot(range(len(tail_df)), tail_df['Close'], color='black', lw=1.5)
ax.set_xlim(0, len(tail_df) - 1)
ax.grid(True, alpha=0.3)

# 軸のメモリ・線の色を白に設定
ax.tick_params(axis='both', colors='white', labelsize=10)
for spine in ax.spines.values():
    spine.set_color('white')

# 破線の描画
colors = {'P50': 'red', 'P48': 'green', 'P45': 'blue', 'P40': 'brown', 'P35': 'gray'}
for label, price in price_levels.items():
    ax.axhline(price, color=colors[label], linestyle='--', alpha=0.6)

# 1. グラフ内凡例（白いボックス）
panel_text = f"Current: {current:.0f}\nDev: {current_dev:.1f}\n" + \
             "\n".join([f"{k}: {p:.0f}" for k, p in price_levels.items()])
ax.text(0.02, 0.02, panel_text, transform=ax.transAxes, fontsize=10, 
        bbox=dict(facecolor='white', alpha=0.9), ha='left', va='bottom')

# 2. グラフ下部の黒余白用凡例（白文字で大きく）
footer_text = f"Current: {current:.0f} | Dev: {current_dev:.1f}\n" + \
              "  ".join([f"{k}: {p:.0f}" for k, p in price_levels.items()])
fig.text(0.05, 0.05, footer_text, color='white', fontsize=14, 
         fontweight='bold', ha='left', va='bottom')

# X軸設定（日時の表示）
def jst_utc_formatter(i, pos):
    idx = int(i)
    if 0 <= idx < len(tail_df):
        return tail_df.index[idx].strftime('%m/%d\n%H:%M')
    return ""

ax.xaxis.set_major_formatter(ticker.FuncFormatter(jst_utc_formatter))
ax.xaxis.set_major_locator(ticker.MaxNLocator(6))
plt.xticks(rotation=30, ha='right', color='white')

# 余白設定 (bottomを広げて下部にスペースを確保)
plt.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.3)

st.pyplot(fig, use_container_width=True)
