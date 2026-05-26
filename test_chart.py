import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from datetime import datetime, timedelta

# 1. テスト用データの生成 (UTC)
# 現在時刻から過去24時間分のダミーデータを生成
periods = 24
end_time = datetime.utcnow()
times = [end_time - timedelta(hours=i) for i in range(periods)]
data = {
    'Time': times,
    'Close': np.random.randn(periods).cumsum() + 100
}
df = pd.DataFrame(data).set_index('Time').sort_index()

# 2. JST/UTC 2段表示フォーマッター
def dual_time_formatter(x, pos):
    # matplotlibの数値(float)をdatetimeに戻す
    dt_utc = mdates.num2date(x)
    # JSTへの変換 (+9時間)
    dt_jst = dt_utc + timedelta(hours=9)
    # 改行して2段にする
    return f"{dt_jst.strftime('%m/%d %H:%M')}\n({dt_utc.strftime('%H:%M')} UTC)"

# 3. グラフ描画
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(df.index, df['Close'], marker='o', color='black', lw=1.2)

# X軸の設定
ax.xaxis.set_major_formatter(ticker.FuncFormatter(dual_time_formatter))
# 適宜、表示間隔を調整 (3時間ごと)
ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))

plt.xticks(rotation=0, fontsize=8)
plt.grid(True, alpha=0.3)
plt.title("Time-Axis Test: JST & UTC Dual Display")
plt.tight_layout()

# 4. Streamlit表示
st.title("時間軸表示テスト")
st.pyplot(fig)

st.write("X軸が『JST』と『(UTC)』の2段で表示されているか確認してください。")

