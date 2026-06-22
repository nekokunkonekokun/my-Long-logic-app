import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# ページの基本設定（pages配下で独立して動作可能）
st.set_page_config(page_title="ボリンジャーバンド未来予測", layout="wide")

st.title("🔍 ボリンジャーバンド未来予測・タイムワープ")

# --- 1. バックテスト用データの事前取得（キャッシュ化して高速化） ---
@st.cache_data(ttl=3600)  # 1時間キャッシュを保持
def load_data():
    # 過去100営業日前＋ボリンジャーバンド計算（25日分）を考慮し、余裕を持って2年分取得
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

# --- 2. メイン画面へのインライン・スライダー配置 ---
st.markdown("### 📅 バックテスト・タイムワープ・スライダー")

# st.sidebar を外して直接 st.slider を使うことでメイン画面に表示（0＝直近最新）
過去へのタイムワープ_日数 = st.slider(
    "過去何営業日前に遡るか (0 = 最新リアルタイム時点)", 
    min_value=0, 
    max_value=100, 
    value=0, 
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

    # --- 5. メイン画面の情報表示（スライダーのすぐ下） ---
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label=f"基準日 ({base_date_str}) の株価", value=f"{global_data[target_idx]:,.1f} 円")
    with col2:
        change_val = global_data[target_idx] - global_data[target_idx - 1]
        st.metric(label=f"前日 ({prev_date_str}) からの変化", value=f"{change_val:,.1f} 円", delta=f"{change_val:,.1f} 円")

    # --- 6. プロット（Matplotlibによる視認性特化のグラフ描写） ---
    fig, ax = plt.subplots(figsize=(12, 5.5))

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

    # グラフの各種装飾
    ax.set_title(f"Nikkei225 Future Band Browser (Base: {base_date_str})", fontsize=13, pad=10)
    ax.set_xlabel("Days (-1 = Prev Day, 0 = Base Date, 1~5 = Future Concept)", fontsize=10)
    ax.set_ylabel("Price (Yen)", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(['Prev', 'Today', '+1d', '+2d', '+3d', '+4d', '+5d'])
    ax.legend(loc='upper left')

    # Streamlit上にグラフを描写
    st.pyplot(fig)

    #7. 数値補足（スマホ視認性特化：タップ切り替え＆縦型グラデーション配置）
    st.markdown("---")
    st.subheader("📊 予測境界値（目安）")
    
    # ラジオボタンを横並びで配置して「ポチッとな」で切り替え
    days_option = st.radio(
        "予測日数を選択：",
        options=["1日後", "5日後"],
        index=0,  # 初期状態は「1日後」
        horizontal=True
    )
    
    # 移動平均線（25MA）レベルの平滑化を考慮し、σ幅は拡大させず固定（実戦仕様）
    if days_option == "1日後":
        target_ma = future_ma[0]          # 1日目の予測25MA
        target_std = std_val              # 現在のσ幅をそのまま適用
        display_label = "1日後"
    else:
        target_ma = future_ma[-1]         # 5日目の予測25MA
        target_std = std_val              # 5日後も同じσ幅で実戦的に固定
        display_label = "5日後"
    
    # スマホ用に1列（縦並び）で、上（高価格）から下（低価格）へ配置
    st.markdown(
        f"""
        <div style="text-align: center; font-weight: bold; color: #1f77b4; margin-bottom: 15px;">
            現在の表示：【 {display_label}予測（25MAベース） 】
        </div>
        <div style="padding: 10px; border-radius: 5px; background-color: rgba(255,75,75,0.1); margin-bottom: 10px;">
            <span style="font-size:12px; color:gray;">【上限警戒】</span><br>
            <strong style="color:#ff4b4b; font-size:18px;">＋3σ : {target_ma + 3*target_std:,.1f} 円</strong>
        </div>
        <div style="padding: 10px; border-radius: 5px; background-color: rgba(255,127,14,0.1); margin-bottom: 10px;">
            <span style="font-size:12px; color:gray;">【上昇目安】</span><br>
            <strong style="color:#ff7f0e; font-size:18px;">＋2σ : {target_ma + 2*target_std:,.1f} 円</strong>
        </div>
        <div style="padding: 10px; border-radius: 5px; background-color: rgba(255,165,0,0.1); margin-bottom: 10px;">
            <span style="font-size:12px; color:gray;">【巡航上昇】</span><br>
            <strong style="color:#ffa500; font-size:18px;">＋1σ : {target_ma + target_std:,.1f} 円</strong>
        </div>
        <div style="padding: 10px; border-radius: 5px; background-color: rgba(31,119,180,0.1); margin-bottom: 10px;">
            <span style="font-size:12px; color:gray;">【中心線】</span><br>
            <strong style="color:#1f77b4; font-size:18px;">予測25MA : {target_ma:,.1f} 円</strong>
        </div>
        <div style="padding: 10px; border-radius: 5px; background-color: rgba(40,167,69,0.1); margin-bottom: 10px;">
            <span style="font-size:12px; color:gray;">| 巡航下落 |</span><br>
            <strong style="color:#28a745; font-size:18px;">－1σ : {target_ma - target_std:,.1f} 円</strong>
        </div>
        <div style="padding: 10px; border-radius: 5px; background-color: rgba(40,167,69,0.15); margin-bottom: 10px;">
            <span style="font-size:12px; color:gray;">【下落目安】</span><br>
            <strong style="color:#218838; font-size:18px;">－2σ : {target_ma - 2*target_std:,.1f} 円</strong>
        </div>
        <div style="padding: 10px; border-radius: 5px; background-color: rgba(36,161,72,0.2); margin-bottom: 10px;">
            <span style="font-size:12px; color:gray;">【下限警戒】</span><br>
            <strong style="color:#1e7e34; font-size:18px;">－3σ : {target_ma - 3*target_std:,.1f} 円</strong>
        </div>
        """,
        unsafe_allow_html=True
    )
