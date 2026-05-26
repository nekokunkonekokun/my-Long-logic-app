import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from datetime import timedelta

# (前略：データのダウンロードと価格レベルの計算ロジックはそのまま)

# X軸の準備 (修正部分)
tail_df = df.tail(168)

# 2段表示フォーマッター
def dual_time_formatter(x, pos):
    # x は matplotlib の内部数値なので、mdates で datetime に戻す
    # df.index はすでに tz_aware(Asia/Tokyo) なのでそのまま変換可能
    dt_jst = mdates.num2date(x)
    dt_utc = dt_jst - timedelta(hours=9)
    return f"{dt_jst.strftime('%m/%d %H:%M')}\n({dt_utc.strftime('%H:%M')} UTC)"

fig, ax = plt.subplots(figsize=(10, 5))

# X軸を数値ではなく、datetime型の日時データとしてプロットする
ax.plot(tail_df.index, tail_df['Close'], color='black', lw=1.2)

# (中略：水平線の描画やテキストボックスの処理はそのまま)

# X軸の設定 (ここを dual_time_formatter に差し替え)
ax.xaxis.set_major_formatter(ticker.FuncFormatter(dual_time_formatter))
ax.xaxis.set_major_locator(mdates.HourLocator(interval=24)) # 1日ごと等の間隔に調整
plt.xticks(rotation=0, fontsize=8)

ax.grid(True, alpha=0.3)
st.pyplot(fig)
