import datetime
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# ==============================================================================
# 1. ページ設定
# ==============================================================================
st.set_page_config(layout="wide")
st.title("NIY=F 1h-Base × 575bars Dual-Vision Chart")
st.markdown("上段に**現在のリアルタイム監視画面**、下段に**過去の任意の瞬間にタイムワープする検証画面**を表示します。")

# リアルタイム用のP50を保存する初期化
if 'p50_fixed' not in st.session_state:
    st.session_state.p50_fixed = 0.0

# ==============================================================================
# 2. データ取得（過去検証のために3ヶ月分の1時間足を確保）
# ==============================================================================
@st.cache_data(ttl=60)
def get_extended_data():
    ticker = yf.Ticker("NIY=F")
    # スライダーで過去に遡れるよう、7dから3mo（3ヶ月分）へ拡張
    df = ticker.history(period="3mo", interval="1h")
    
    if df.empty:
        return df

    # リアルタイム価格を取得して最新行を上書き
    try:
        latest_price = ticker.fast_info['last_price']
        if latest_price is not None:
            df.iloc[-1, df.columns.get_loc('Close')] = latest_price
    except:
        pass
        
    df.index = df.index.tz_convert('Asia/Tokyo')
    return df

# データ取得
df_all = get_extended_data()

if df_all.empty:
    st.error("データの取得に失敗しました。時間をおいて再度お試しください。")
    st.stop()

# ==============================================================================
# 3. 【上段】リアルタイム・エリア（今までのロジックを100%維持）
# ==============================================================================
st.markdown("---")
st.header("⚡ 1. リアルタイム・ライブモニター")

last_updated = df_all.index[-1]
current = df_all['Close'].iloc[-1].item()
current_max = df_all['Close'].max().item()

# 新高値更新ロジック
if current_max > st.session_state.p50_fixed:
    st.session_state.p50_fixed = current_max

p50_rt = st.session_state.p50_fixed
std_rt = df_all['Close'].rolling(window=575, min_periods=10).std().iloc[-1].item()

price_levels_rt = {
    "P50": p50_rt,
    "P48": p50_rt - std_rt,
    "P45": p50_rt - 2 * std_rt,
    "P40": p50_rt - 3 * std_rt,
    "P35": p50_rt - 4 * std_rt
}

# リアルタイムDev計算
if current >= price_levels_rt["P48"]:
    current_dev = 48 + 2 * (current - price_levels_rt["P48"]) / (p50_rt - price_levels_rt["P48"])
elif current >= price_levels_rt["P45"]:
    current_dev = 45 + 3 * (current - price_levels_rt["P45"]) / (price_levels_rt["P48"] - price_levels_rt["P45"])
else:
    current_dev = 40 + 5 * (current - price_levels_rt["P40"]) / (price_levels_rt["P45"] - price_levels_rt["P40"])

# リアルタイムグラフ描画（直近168本＝約1週間分）
fig_rt, ax_rt = plt.subplots(figsize=(16, 5))
tail_df_rt = df_all.tail(168)
ax_rt.plot(range(len(tail_df_rt)), tail_df_rt['Close'], color='black', lw=1.5, label="Actual Price")

# 横の破線（リアルタイム）
colors_map = {'P50':'red','P48':'green','P45':'blue','P40':'brown','P35':'gray'}
for label, price in price_levels_rt.items():
    ax_rt.axhline(price, color=colors_map[label], linestyle='--', alpha=0.6, label=label)

ax_rt.axvline(x=len(tail_df_rt)-1, color='orange', linestyle=':', lw=2, label="Latest Spot")
ax_rt.grid(True, linestyle=':', alpha=0.5)
ax_rt.set_title("Current Real-Time Window (Last 168 Bars)", fontsize=12, fontweight='bold')
st.pyplot(fig_rt, use_container_width=True)

# リアルタイム指標表示
st.write(f"Data Last Updated: {last_updated.strftime('%Y-%m-%d %H:%M')} JST")
cols_rt = st.columns(7)
cols_rt[0].metric("Current", f"{current:.0f}")
cols_rt[1].metric("Dev (Now)", f"{current_dev:.1f}")
cols_rt[2].metric("P50", f"{p50_rt:.0f}")
cols_rt[3].metric("P48", f"{price_levels_rt['P48']:.0f}")
cols_rt[4].metric("P45", f"{price_levels_rt['P45']:.0f}")
cols_rt[5].metric("P40", f"{price_levels_rt['P40']:.0f}")
cols_rt[6].metric("P35", f"{price_levels_rt['P35']:.0f}")


# ==============================================================================
# 4. 【下段】過去検証・エリア（新設：パターンA完全連動スライダー）
# ==============================================================================
st.markdown("---")
st.header("🔍 2. バックテスト・タイムワープシミュレーター")

# 最大で何本前まで遡るか（データ全件数から168本を残した残量を上限に安全マージンを設定）
max_backtrack = len(df_all) - 169

if max_backtrack < 10:
    st.warning("⚠️ 過去データが十分に蓄積されていません。しばらくお待ちください。")
else:
    # タイムワープコントロール用のWebスライダー
    back_bars = st.slider(
        label="⏰ 過去へタイムワープ（何時間前に戻るか指定してください）",
        min_value=0,
        max_value=int(max_backtrack),
        value=0,
        step=1
    )

    # スライダーが指す「過去のターゲット位置」
    target_idx = len(df_all) - back_bars

    # パターンA：ターゲット時点までのデータだけを切り出し（未来を遮断）
    df_history_up_to_target = df_all.iloc[:target_idx]
    
    # そこから直近168本を切り出してグラフ表示用にする
    df_view_hist = df_history_up_to_target.tail(168)

    # --- 過去時点での指標の再計算 ---
    hist_current = df_view_hist['Close'].iloc[-1].item()  # その当時の最新価格
    hist_last_updated = df_view_hist.index[-1]           # その当時の日時
    
    # その当時までの「全期間の最高値」をP50として再捕捉
    p50_hist = df_history_up_to_target['Close'].max().item()
    
    # その当時時点での575本移動標準偏差
    std_hist = df_history_up_to_target['Close'].rolling(window=575, min_periods=10).std().iloc[-1].item()

    price_levels_hist = {
        "P50": p50_hist,
        "P48": p50_hist - std_hist,
        "P45": p50_hist - 2 * std_hist,
        "P40": p50_hist - 3 * std_hist,
        "P35": p50_hist - 4 * std_hist
    }

    # 過去時点でのDev計算
    if hist_current >= price_levels_hist["P48"]:
        hist_dev = 48 + 2 * (hist_current - price_levels_hist["P48"]) / (p50_hist - price_levels_hist["P48"])
    elif hist_current >= price_levels_hist["P45"]:
        hist_dev = 45 + 3 * (hist_current - price_levels_hist["P45"]) / (price_levels_hist["P48"] - price_levels_hist["P45"])
    else:
        hist_dev = 40 + 5 * (hist_current - price_levels_hist["P40"]) / (price_levels_hist["P45"] - price_levels_hist["P40"])

    # 過去検証用のグラフ描画
    fig_hist, ax_hist = plt.subplots(figsize=(16, 5))
    ax_hist.plot(range(len(df_view_hist)), df_view_hist['Close'], color='#2b2d42', lw=1.5)

    # 横の破線（過去基準の値）
    for label, price in price_levels_hist.items():
        ax_hist.axhline(price, color=colors_map[label], linestyle='--', alpha=0.6)

    # 当時を指す右端の縦線（色をリアルタイムと変えて青系の点線に）
    ax_hist.axvline(x=len(df_view_hist)-1, color='#457b9d', linestyle=':', lw=2.5)
    ax_hist.grid(True, linestyle=':', alpha=0.5)
    ax_hist.set_title(f"Historical Window Snapshot [ Base Time: {hist_last_updated.strftime('%Y-%m-%d %H:%M')} JST ]", fontsize=12, fontweight='bold', color='#1d3557')
    st.pyplot(fig_hist, use_container_width=True)

    # 過去検証用の指標表示（メトリック）
    st.write(f"📊 **【タイムワープ検証ボード】** 基準日時: {hist_last_updated.strftime('%Y-%m-%d %H:%M')} JST")
    cols_hist = st.columns(7)
    cols_hist[0].metric("Historical Price", f"{hist_current:.0f}")
    cols_hist[1].metric("Dev (Then)", f"{hist_dev:.1f}", delta=f"{hist_dev - current_dev:.1f}" if back_bars != 0 else None, delta_color="inverse")
    cols_hist[2].metric("P50 (Then)", f"{p50_hist:.0f}")
    cols_hist[3].metric("P48 (Then)", f"{price_levels_hist['P48']:.0f}")
    cols_hist[4].metric("P45 (Then)", f"{price_levels_hist['P45']:.0f}")
    cols_hist[5].metric("P40 (Then)", f"{price_levels_hist['P40']:.0f}")
    cols_hist[6].metric("P35 (Then)", f"{price_levels_hist['P35']:.0f}")
