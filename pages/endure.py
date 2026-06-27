import pandas as pd
import yfinance as yf
import streamlit as st

def show_endure_board(slider_lookback_days=0):
    """
    タイムワープスライダーの値(slider_lookback_days)を引数として受け取り、
    スマホ画面に最適化された「トホホ・生還確率ボード」を描画する関数
    """
    st.subheader("🛡️ トホホ・生還確率シミュレーター")

    # 1. データ取得（スマホの負荷軽減のためStreamlitのキャッシュを利用）
    @st.cache_data(ttl=3600)
    def load_data():
        ticker = yf.Ticker("^N225")
        df = ticker.history(period="1y", interval="1d")
        # タイムゾーンを日本時間に統一
        df.index = df.index.tz_convert('Asia/Tokyo')
        return df

    try:
        df_daily = load_data()
    except Exception as e:
        st.error("データの取得に失敗しました。")
        return

    # 2. スライダーの位置に合わせて基準日（ターゲット）を決定
    last_idx = len(df_daily) - 1
    target_idx = last_idx - slider_lookback_days
    
    if target_idx < 10:
        st.warning("遡りすぎてデータが不足しています。")
        return

    # 3. 生還日数・最大逆行の計算ロジック
    def calculate_metrics(base_df, t_idx, p0_price):
        future_df = base_df.iloc[t_idx + 1:]
        if future_df.empty:
            return "未生還(0日目)", 0, 0
            
        max_reverse = 0
        recovery_days = None
        elapsed_days = 0
        
        for idx, row in future_df.iterrows():
            elapsed_days += 1
            # 最大逆行幅（ザラ場最安値ベース）
            drawdown = p0_price - row['Low']
            if drawdown > max_reverse:
                max_reverse = drawdown
            # 生還判定（ザラ場最高値ベース）
            if row['High'] >= p0_price and recovery_days is None:
                recovery_days = elapsed_days
                
        if recovery_days is not None:
            status_str = f"{recovery_days}日で生還"
        else:
            status_str = f"未生還({elapsed_days}日目)"
            
        micro_loss = -int(max_reverse * 10)
        return status_str, max_reverse, micro_loss

    # 4. 新聞データのパッキング（直近10日分）
    results = []
    for i in range(10, 0, -1):
        idx = target_idx - (10 - i)
        if idx < 10:
            continue
            
        curr_row = base_df = df_daily.iloc[idx]
        p0 = curr_row['Close']
        p1 = df_daily.iloc[idx - 1]['Close']
        p3 = df_daily.iloc[idx - 3]['Close']
        p10 = df_daily.iloc[idx - 10]['Close']
        date_str = curr_row.name.strftime('%m/%d')
        
        status_str, max_reverse, micro_loss = calculate_metrics(df_daily, idx, p0)
        
        def get_mark(today, past):
            return "○" if today > past else ("●" if today < past else "△")

        results.append({
            "日付": date_str,
            "終値": f"{int(p0):,}",
            "1日": get_mark(p0, p1),
            "3日": get_mark(p0, p3),
            "10日": get_mark(p0, p10),
            "最大逆行": f"-{int(max_reverse):,}円" if max_reverse > 0 else "0円",
            "マイクロ1枚": f"{micro_loss:,}円" if micro_loss < 0 else "0円",
            "ステータス": status_str,
            "_raw_days": recovery_days if recovery_days is not None else (999 if "未生還" in status_str else None)
        })

    res_df = pd.DataFrame(results)

    # 5. スマホ最適化：極小サイズ＆レスポンシブなHTMLテーブルの生成
    # 既存のStreamlitアプリのダークモード（黒背景）に溶け込む配色
    table_html = """
    <div style="overflow-x:auto; width:100%; -webkit-overflow-scrolling:touch;">
        <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:11px; text-align:center; color:#e0e0e0; background-color:#1e1e1e;">
            <thead>
                <tr style="background-color:#2d2d2d; border-bottom:2px solid #444;">
                    <th style="padding:6px 2px;">日付</th>
                    <th style="padding:6px 2px;">終値</th>
                    <th style="padding:6px 1px;">1日</th>
                    <th style="padding:6px 1px;">3日</th>
                    <th style="padding:6px 1px;">10日</th>
                    <th style="padding:6px 2px;">最大逆行</th>
                    <th style="padding:6px 2px; color:#ff6b6b;">マイ1枚</th>
                    <th style="padding:6px 2px;">ステータス</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for _, row in res_df.iterrows():
        # 未生還（現在捕まり中）はスマホ画面でも一発でわかるように背景を警戒色に
        bg_style = "background-color:#3a2222;" if "未生還" in row['ステータス'] else ""
        
        table_html += f"<tr style='border-bottom:1px solid #333; {bg_style}'>"
        table_html += f"<td style='padding:6px 2px; font-weight:bold;'>{row['日付']}</td>"
        table_html += f"<td style='padding:6px 2px;'>{row['終値']}</td>"
        table_html += f"<td style='padding:6px 1px;'>{row['1日']}</td>"
        table_html += f"<td style='padding:6px 1px;'>{row['3日']}</td>"
        table_html += f"<td style='padding:6px 1px;'>{row['10日']}</td>"
        table_html += f"<td style='padding:6px 2px;'>{row['最大逆行']}</td>"
        table_html += f"<td style='padding:6px 2px; color:#ff8787;'>{row['マイクロ1枚']}</td>"
        table_html += f"<td style='padding:6px 2px; font-weight:bold;'>{row['ステータス']}</td>"
        table_html += "</tr>"
        
    table_html += "</tbody></table></div>"
    
    # メイン画面にテーブルをフラットに流し込み（横ブレ防止）
    st.components.v1.html(table_html, height=320, scrolling=False)

    # 6. 【核心】タイムスパン別・生還確率推論（ st.info ですっきり配置 ）
    valid_days = res_df["_raw_days"].dropna()
    total_valid = len(valid_days)
    
    if total_valid > 0:
        p_3days = (valid_days <= 3).sum() / total_valid * 100
        p_7days = (valid_days <= 7).sum() / total_valid * 100
        p_14days = (valid_days <= 14).sum() / total_valid * 100
        
        st.markdown("### 🔮 タイムスパン別・生還確率推論")
        st.info(f"⏳ **3日以内** に無事生還（数日での戻り）: **{p_3days:.1f}%**")
        st.success(f"🔋 **7日以内** に粘って生還（1週間のノイズ）: **{p_7days:.1f}%**")
        st.warning(f"🛡️ **14日以内** にじっくり生還（HFT過剰調整）: **{p_14days:.1f}%**")
    else:
        st.text("生還確率：計算データ不足")

# テスト起動用（単体で動かす場合）
if __name__ == "__main__":
    st.title("Test App")
    # 既存のタイムワープスライダーの値を模したテスト（0＝最新）
    show_endure_board(slider_lookback_days=0)
  
