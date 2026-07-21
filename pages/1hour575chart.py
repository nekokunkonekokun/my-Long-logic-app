import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import timedelta

st.set_page_config(layout="wide")
st.title("NIY=F 1hour×575 Chart (Mean Reversion)")

@st.cache_data(ttl=3600)
def get_data():
    df = yf.download("NIY=F", period="1y", interval="1h").dropna()
    df.index = df.index.tz_convert('Asia/Tokyo')
    return df

df = get_data()

# 575本の移動平均（SMA）と標準偏差（STD）の計算
WINDOW = 575
df['SMA'] = df['Close'].rolling(window=WINDOW).mean()
df['STD'] = df['Close'].rolling(window=WINDOW).std()

current = df['Close'].iloc[-1].item()
sma = df['SMA'].iloc[-1].item()
std = df['STD'].iloc[-1].item()

# 平均（SMA）を基準に上下へラインを展開（P50 = SMA）
price_levels = {
    "P65 (+3σ)": sma + (3 * std),
    "P60 (+2σ)": sma + (2 * std),
    "P55 (+1σ)": sma + (1 * std),
    "P50 (SMA)": sma,
    "P45 (-1σ)": sma - (1 * std),
    "P40 (-2σ)": sma - (2 * std),
    "P35 (-3σ)": sma - (3 * std)
}

# 平均回帰型 Dev (偏差値) 計算： 1σ離れるごとに Dev が 5 変動する設定
current_dev = 50 + ((current - sma) / std) * 5

# グラフ描画
tail_df = df.tail(168)
fig, ax = plt.subplots(figsize=(16, 7))
ax.plot(range(len(tail_df)), tail_df['Close'], color='black', lw=1.5)
ax.set_xlim(0, len(tail_df) - 1)

# 破線と凡例の描画（中心のP50を強調）
colors = {
    "P65 (+3σ)": 'brown',
    "P60 (+2σ)": 'blue',
    "P55 (+1σ)": 'green',
    "P50 (SMA)": 'red',
    "P45 (-1σ)": 'green',
    "P40 (-2σ)": 'blue',
    "P35 (-3σ)": 'brown'
}

for label, price in price_levels.items():
    style = '-' if "SMA" in label else '--'
    alpha = 0.8 if "SMA" in label else 0.5
    ax.axhline(price, color=colors[label], linestyle=style, alpha=alpha)

# 凡例ボックス（左下）
panel_text = f"Current: {current:.0f}\nDev: {current_dev:.1f}\n" + \
             "\n".join([f"{k}: {p:.0f}" for k, p in price_levels.items()])
ax.text(0.01, 0.02, panel_text, transform=ax.transAxes, fontsize=10, 
        bbox=dict(facecolor='white', alpha=0.9), ha='left', va='bottom')

# JST/UTC軸フォーマット
def jst_utc_formatter(i, pos):
    idx = int(i)
    if 0 <= idx < len(tail_df):
        dt_jst = tail_df.index[idx]
        dt_utc = dt_jst - timedelta(hours=9)
        return f"{dt_jst.strftime('%m/%d %H:%M')}\n({dt_utc.strftime('%H:%M')} UTC)"
    return ""

ax.xaxis.set_major_formatter(ticker.FuncFormatter(jst_utc_formatter))
ax.xaxis.set_major_locator(ticker.MaxNLocator(7))
plt.xticks(rotation=30, fontsize=10, ha='right')
ax.grid(True, alpha=0.4)
plt.subplots_adjust(left=0.06, right=0.98, top=0.95, bottom=0.18)

# チャートを出力
st.pyplot(fig, use_container_width=True)

# ---------------------------------------------------------
# 追加部分: チャートの外に独立して分かりやすく並ぶ文字（インジケーター）
# ---------------------------------------------------------
st.write("---")
st.subheader("📊 Strategic Metrics Panel (Mean Reversion)")

# 9列に分割して配置（全レベル表示）
cols = st.columns(9)

cols[0].metric(label="Current Price", value=f"{current:.0f}")
cols[1].metric(label="Current Dev", value=f"{current_dev:.1f}")
cols[2].metric(label="P65 (+3σ)", value=f"{price_levels['P65 (+3σ)']:.0f}")
cols[3].metric(label="P60 (+2σ)", value=f"{price_levels['P60 (+2σ)']:.0f}")
cols[4].metric(label="P55 (+1σ)", value=f"{price_levels['P55 (+1σ)']:.0f}")
cols[5].metric(label="P50 (SMA)", value=f"{price_levels['P50 (SMA)']:.0f}")
cols[6].metric(label="P45 (-1σ)", value=f"{price_levels['P45 (-1σ)']:.0f}")
cols[7].metric(label="P40 (-2σ)", value=f"{price_levels['P40 (-2σ)']:.0f}")
cols[8].metric(label="P35 (-3σ)", value=f"{price_levels['P35 (-3σ)']:.0f}")
