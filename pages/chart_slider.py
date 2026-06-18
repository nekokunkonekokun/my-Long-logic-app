# ==============================================================================
# 1. ページ独立型ライブラリインポート
# ==============================================================================
import datetime
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# ==============================================================================
# 2. Streamlit ページ設定 & UI コントロール
# ==============================================================================
st.set_page_config(page_title="Nikkei 225 5-Day Return Map", layout="wide")

st.title("📄 Nikkei 225 Futures - 5-Day Rate of Change Map")
st.markdown("---")

# Streamlit専用のインタラクティブ・Webスライダー
# 初期値を「0」にすることで、最新の30分足リアルタイムデータを常に右端に含めます
Days_Ago_to_Verify = st.slider(
    label="🔍 バックテスト・シミュレーション・スライダー (0 = 今日/リアルタイム)",
    min_value=0,
    max_value=120,
    value=0,
    step=1
)

# ==============================================================================
# 3. データ取得 & UTC統一ハイブリッド処理 (NIY=F 単体)
# ==============================================================================
@st.cache_data(ttl=60)  # データの過剰ダウンロードを防ぐため1分間キャッシュ
def get_pure_utc_data():
    ticker = "NIY=F"
    
    # 1. 日足データの取得（UTC基準）
    df_daily = yf.download(ticker, start="2025-01-01", interval="1d", auto_adjust=True)
    if df_daily.empty:
        st.error(f"❌ {ticker} の日足データの取得に失敗しました。")
        return pd.DataFrame()
        
    if isinstance(df_daily.columns, pd.MultiIndex):
        df_daily.columns = df_daily.columns.get_level_values(0)
    
    # 欠損日（空の行）を完全に除外してソート
    df_daily = df_daily.dropna(subset=['Close']).sort_index()

    # 2. 30分足データの取得（最新リアルタイム値用）
    try:
        df_intra = yf.download(ticker, period="3d", interval="30m", auto_adjust=True)
        if isinstance(df_intra.columns, pd.MultiIndex):
            df_intra.columns = df_intra.columns.get_level_values(0)
    except Exception:
        df_intra = pd.DataFrame()

    # 3. UTC基準でのドッキング
    if not df_intra.empty:
        # 30分足の最後の1行（現在のリアルタイム価格と時間）を取得
        latest_intra_row = df_intra.iloc[-1]
        latest_intra_price = latest_intra_row['Close']
        latest_intra_time = df_intra.index[-1]
        
        # タイムスタンプの日付部分（UTC）をそのまま使用し、形式を日足に統一
        target_utc_date = pd.Timestamp(latest_intra_time.date())
        
        # 最新の30分足の値を「当日の日足終値」として末尾にドッキング（または最新に上書き）
        df_daily.loc[target_utc_date, 'Close'] = latest_intra_price

    # 再度、欠損日を除外して日付順にソート
    df_daily = df_daily.dropna(subset=['Close']).sort_index()
    return df_daily

# データの読み込み
df = get_pure_utc_data()

if not df.empty:
    # ==============================================================================
    # 4. 5日騰落率（%）の計算 ※欠損日除外後の5営業日前と比較
    # ==============================================================================
    df['5d_Return'] = df['Close'].pct_change(5) * 100
    df_2026 = df[df.index >= '2026-01-01'].copy()

    # 2026年の限界突破の壁（最大・最小）
    max_wall = df_2026['5d_Return'].max()
    min_wall = df_2026['5d_Return'].min()

    # ==============================================================================
    # 5. データ切り出し (バックテスト・エンジン & エラー回避)
    # ==============================================================================
    target_idx = len(df_2026) - Days_Ago_to_Verify

    if target_idx < 30:
        st.warning("⚠️ 2026年のデータが不足しています。スライダーの値を小さくしてください。")
    else:
        # 過去30営業日分のデータを切り出し（0のときは末尾の最新30分足まで含む）
        df_view = df_2026.iloc[target_idx-30 : target_idx]

        # 未来データの切り出し（スライダー0の時はエラー回避のため空にする）
        if Days_Ago_to_Verify <= 0:
            df_future = pd.DataFrame()
        else:
            df_future = df_2026.iloc[target_idx : target_idx+5]

        current_val = df_view['5d_Return'].iloc[-1]
        current_date = df_view.index[-1].strftime('%Y-%m-%d')
        target_price = df_view['Close'].iloc[-1]

        # ==============================================================================
        # 6. Matplotlib グラフ描画
        # ==============================================================================
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(14, 7), facecolor='white')
        ax.set_facecolor('white')

        # ① 過去30営業日の軌跡（赤実線）
        ax.plot(df_view.index, df_view['5d_Return'], color='#e63946', linewidth=2.5,
                marker='o', markersize=6, label='5-Day Return (Past 30 Days)')

        # ② 未来の5日間の答え合わせ（オレンジ点線：検証用）
        if not df_future.empty and len(df_future) > 0:
            df_future_conn = pd.concat([df_view.tail(1), df_future])
            ax.plot(df_future_conn.index, df_future_conn['5d_Return'], color='#f5a623',
                    linestyle='--', linewidth=2, marker='x', markersize=8, label='Next 5 Days (Result)')

        # ③ 各種補助線（破線・点線）
        ax.axhline(0, color='black', linestyle='--', alpha=0.7, linewidth=1.2, label='Baseline (0%)')
        ax.axhline(5, color='#8d99ae', linestyle=':', linewidth=1.2, label='Alert Line (+5%)')
        ax.axhline(-5, color='#8d99ae', linestyle=':', linewidth=1.2, label='Alert Line (-5%)')

        # ④ 2026年の限界突破の壁（一点鎖線）
        ax.axhline(max_wall, color='#e07a5f', linestyle='-.', linewidth=1, alpha=0.7, label=f'2026 Max Wall ({max_wall:.2f}%)')
        ax.axhline(min_wall, color='#457b9d', linestyle='-.', linewidth=1, alpha=0.7, label=f'2026 Min Wall ({min_wall:.2f}%)')

        # ⑤ 現在のリアルタイムスポットを強調する大きな青丸
        label_latest_dot = 'Current Real-Time Spot (NIY=F Daily + 30m)' if Days_Ago_to_Verify == 0 else 'Selected Verification Date'
        ax.plot(df_view.index[-1], df_view['5d_Return'].iloc[-1],
                marker='o', color='#457b9d', markersize=12, label=label_latest_dot)

        # グラフ装飾・タイトル
        ax.set_title('Nikkei 225 Futures (NIY=F) - 5-Day Rate of Change Map (UTC Hybrid)', fontsize=14, pad=15, fontweight='bold', color='#1d3557')
        ax.set_ylabel('Rate of Change (%)', fontsize=12, color='#1d3557')
        ax.grid(True, linestyle=':', alpha=0.5, color='#cbd5e1')
        
        # 凡例表示
        ax.legend(loc='upper left', fontsize=10, facecolor='white', edgecolor='#cbd5e1', framealpha=0.9)

        # 縦軸の余白調整
        padding = (max_wall - min_wall) * 0.15
        ax.set_ylim(min_wall - padding, max_wall + padding)

        # ⑥ 左下の情報ボックス
        box_title = "【CURRENT REAL-TIME (UTC)】" if Days_Ago_to_Verify == 0 else "【BACKTEST HISTORICAL】"
        text_str = (
            f"{box_title}\n"
            f"Base Date: {current_date}\n"
            f"Latest Price (30m): {target_price:,.0f} JPY\n"
            f"Calculated 5D Return: {current_val:.2f}%\n"
            f"2026 Ceil/Floor: {max_wall:.2f}% / {min_wall:.2f}%"
        )
        ax.text(0.02, 0.04, text_str, transform=ax.transAxes, fontsize=10.5, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.6', facecolor='#f8f9fa', alpha=0.95, edgecolor='#cbd5e1'))

        # Streamlit用のグラフ描画命令（重要）
        st.pyplot(fig)

