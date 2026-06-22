import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# ページの基本設定（pages配下で独立して動作可能）
st.set_page_config(page_title="ボリンジャーバンド未来予測", layout="wide")

st.title("🔍 ボリンジャーバンド未来予測・タイムワープ")
st.caption("スライダーを動かして過去の流れを追いながら、予測バンドをヒントに『勘』で次の展開を読み切るツール")

# --- 1. バックテスト用データの事前取得（キャッシュ化して高速化） ---
@st.cache_data(ttl=3600)  # 1時間キャッシュを保持
def load_data():
    # 過去100営業日前＋ボリンジャーバンド計算（25日分）＋マージンを考慮し、余裕を持って2年分取得
    df = yf.download("^N225", period="2y")
    
    # yfinanceの階層構造（MultiIndex）対策
    if isinstance(df.columns, pd.MultiIndex):
        close_series = df['Close']['^N225']
    else:
        close_series = df['Close']
        
    close_series = close_series.dropna()
    return close_series.index, close_series.values

try:
    global_dates, global_data = load_data()
except Exception as e:
    st.error(f"データの取得に失敗しました: {e}")
    st.stop()

# --- 2. サイドバー / コントロールUI ---
st.sidebar.header("⏳ タイムワープ設定")

# 過去100営業日をスライダーで選択（1日前〜100日前）
# 1が最も直近（最新営業日）になります
過去へのタイムワープ_日数 = st.sidebar.slider(
    "過去何営業日前に遡るか", 
    min_value=1, 
    max_value=100, 
    value=1, 
    step=1
)

# --- 3. 選択された過去の特定時点のデータを抽出 ---
# 全データから指定された日数分だけ遡った位置を「今日（0日目）」とする
target_idx = len(global_data) - 1 - 過去へのタイムワープ_日数

# 25MAの計算に十分なデータがあるかチェック
if target_idx < 25:
    st.warning("データが不足しています。スライダーの数値を小さくしてください。")
else:
    # 基準日（今日）までの過去データ
    sub_data = global_data[:target_idx + 1]

    # 移動平均と標準偏差の計算
    ma25 = pd.Series(sub_data).rolling(window=25).mean().values
    std25 = pd.Series(sub_data).rolling(window=25).std().values

    # 4. 予測データ作成（未来5日分）
    future_n = 5
    # 前営業日からの傾き（勢い）を算出
    drift = ma25[-1] - ma25[-2]

    # 未来5日間の25MAトレンド線（直線予測）
    future_ma = np.array([ma25[-1] + drift * i for i in range(future_n + 1)])
    
    # 今回は「過去1日（前日、今日）＋未来5日」なので、プロット用の中心線は計7点
    # インデックスとしては: -1(前日), 0(今日), 1, 2, 3, 4, 5
    ma_extended = np.concatenate([[ma25[-2]], future_ma])

    # 標準偏差は基準日（今日）の値をそのまま未来5日間キープ
    std_val = std25[-1]
    std_extended = np.full(len(ma_extended), std_val)

    # 横軸の定義（-1:前日, 0:今日, 1〜5:未来）
    x = np.arange(-1, future_n + 1)

    # 日付ラベルの取得
    prev_date_str = global_dates[target_idx - 1].strftime('%Y-%m-%d')
    base_date_str = global_dates[target_idx].strftime('%Y-%m-%d')

    # --- 5. メイン画面の情報表示 ---
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label=f"基準日 ({base_date_str}) の株価", value=f"{global_data[target_idx]:,.1f} 円")
    with col2:
        change_val = global_data[target_idx] - global_data[target_idx - 1]
        st.metric(label=f"前日 ({prev_date_str}) からの変化", value=f"{change_val:,.1f} 円", delta=f"{change_val:,.1f} 円")

    # --- 6. プロット（Matplotlibによる極限まで削ぎ落とした描画） ---
    fig, ax = plt.subplots(figsize=(12, 6))

    # Y軸の範囲を、表示するデータ（±3σの範囲）に合わせて自動で最適化して画面切れを防止
    y_max = np.max(ma_extended + 3 * std_extended)
    y_min = np.min(ma_extended - 3 * std_extended)
    margin = (y_max - y_min) * 0.1
    ax.set_ylim(y_min - margin, y_max + margin)

    # 背景グリッド
    ax.grid(True, linestyle='--', alpha=0.5)

    # 25MAトレンド予測線（前日〜未来5日）
    ax.plot(x, ma_extended, color='#1f77b4', linewidth=2, label='Predicted 25MA Trend')

    # ±1σ〜±3σ 予測バンドの塗りつぶし
    for i in range(1, 4):
        ax.fill_between(x, ma_extended - i*std_extended, ma_extended + i*std_extended,
                        color='#ff7f0e', alpha=0.15 - (i * 0.03), label=f'Predicted ±{i}σ')

    # 実価格（前日[-1] から 今日[0] までの実績流れ：黒線）
    ax.plot([-1, 0], [global_data[target_idx-1], global_data[target_idx]], 
            color='black', marker='o', linewidth=3, markersize=8, label='Actual Price (Past 1-Day Flow)')

    # 現在地（今日）を強調する垂直線
    ax.axvline(x=0, color='gray', linestyle=':', alpha=0.7)
    ax.text(0.1, y_min, 'Base Date (Today)', color='gray', fontsize=10)

    # グラフの各種装飾
    ax.set_title(f"Nikkei225 Future Band Browser\n[ Base Date: {base_date_str} ]", fontsize=14, pad=15)
    ax.set_xlabel("Days (-1 = Prev Day, 0 = Base Date, 1~5 = Future Concept)", fontsize=11)
    ax.set_ylabel("Price (Yen)", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(['Prev', 'Today', '+1d', '+2d', '+3d', '+4d', '+5d'])
    ax.legend(loc='upper left')

    # Streamlit上にグラフを描写
    st.pyplot(fig)

    # --- 7. 数値補足（バンドの正確な枠を文字でも把握） ---
    st.markdown("---")
    st.subheader("📊 5日後の予測境界値（目安）")
    
    final_ma = future_ma[-1]
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**+3σ（上限目安）**<br><span style='color:#ff4b4b;font-size:20px;font-weight:bold;'>{final_ma + 3*std_val:,.1f} 円</span>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"**予測25MA（中心）**<br><span style='color:#1f77b4;font-size:20px;font-weight:bold;'>{final_ma:,.1f} 円</span>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"**-3σ（下限目安）**<br><span style='color:#24a148;font-size:20px;font-weight:bold;'>{final_ma - 3*std_val:,.1f} 円</span>", unsafe_allow_html=True)
