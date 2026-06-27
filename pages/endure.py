import pandas as pd
import yfinance as yf
import streamlit as st

def show_endure_board(slider_lookback_days=0):
    """
    スマホ画面特化：最新1時間足の自動マージ ＆ 生還確率シミュレーター (未来世界追跡＆赤バツ版)
    """
    st.subheader("🛡️ トホホ・生還確率シミュレーター")

    # 1. 確定日足と最新1時間足の取得（キャッシュ化）
    @st.cache_data(ttl=600)
    def load_combined_data():
        ticker = yf.Ticker("^N225")
        df_daily_raw = ticker.history(period="1y", interval="1d")
        df_hourly_raw = ticker.history(period="1mo", interval="1h")
        
        df_daily_raw.index = df_daily_raw.index.tz_convert('Asia/Tokyo')
        df_hourly_raw.index = df_hourly_raw.index.tz_convert('Asia/Tokyo')
        
        latest_hourly_idx = df_hourly_raw.index[-1]
        today_date_str = latest_hourly_idx.strftime('%Y-%m-%d')
        
        if df_daily_raw.index[-1].strftime('%Y-%m-%d') == today_date_str:
            df_base = df_daily_raw.iloc[:-1].copy()
        else:
            df_base = df_daily_raw.copy()
            
        today_hourly = df_hourly_raw[df_hourly_raw.index.strftime('%Y-%m-%d') == today_date_str]
        
        if not today_hourly.empty:
            today_row = pd.DataFrame([{
                'Open': today_hourly['Open'].iloc[0],
                'High': today_hourly['High'].max(),
                'Low': today_hourly['Low'].min(),
                'Close': today_hourly['Close'].iloc[-1],
                'Volume': today_hourly['Volume'].sum()
            }], index=[latest_hourly_idx])
            df_final = pd.concat([df_base, today_row])
        else:
            df_final = df_base.copy()
            
        return df_final

    try:
        df_daily = load_combined_data()
    except Exception as e:
        st.error("データの取得に失敗しました。")
        return

    # 2. スライダーの位置に合わせて基準日を決定
    last_idx = len(df_daily) - 1
    target_idx = last_idx - slider_lookback_days
    
    if target_idx < 10:
        st.warning("遡りすぎてデータが不足しています。")
        return

    # 3. 生還日数・最大逆行の計算ロジック
    def calculate_metrics(base_df, t_idx, p0_price):
        future_df = base_df.iloc[t_idx + 1:]
        if future_df.empty:
            return "追跡中", 0, 0
            
        max_reverse = 0
        recovery_days = None
        elapsed_days = 0
        
        for idx, row in future_df.iterrows():
            elapsed_days += 1
            drawdown = p0_price - row['Low']
            if drawdown > max_reverse:
                max_reverse = drawdown
            
            if row['Close'] >= p0_price and recovery_days is None:
                recovery_days = elapsed_days
                break
                
        if recovery_days is not None:
            status_str = f"{recovery_days}日で生還"
        else:
            status_str = f"未生還({elapsed_days}日目)"
            
        micro_loss = -int(max_reverse * 10)
        return status_str, max_reverse, micro_loss

    # 4. 未来世界のパッキング（直近10日分）
    results = []
    for i in range(10, 0, -1):
        idx = target_idx - (10 - i)
        if idx < 0 or idx > last_idx:
            continue
            
        curr_row = df_daily.iloc[idx]
        p0 = curr_row['Close'] # エントリーした日の終値
        
        # 🎯 【超重要・大手術】過去(idx - n)ではなく、未来(idx + n)の世界を見に行く
        # もし未来のデータがまだ存在しない場合は「-（未確定）」にする
        p1 = df_daily.iloc[idx + 1]['Close'] if (idx + 1) <= last_idx else None
        p3 = df_daily.iloc[idx + 3]['Close'] if (idx + 3) <= last_idx else None
        p10 = df_daily.iloc[idx + 10]['Close'] if (idx + 10) <= last_idx else None
        
        is_latest_row = (idx == last_idx)
        date_str = curr_row.name.strftime('%m/%d') + ("*" if is_latest_row else "")
        
        status_str, max_reverse, micro_loss = calculate_metrics(df_daily, idx, p0)
        
        # 未来の終値が建値(p0)より高ければ「○」、低ければ「×」、未確定なら「-」
        def get_future_mark(base_price, future_price):
            if future_price is None:
                return "-"
            return "○" if future_price >= base_price else "×"

        raw_days = None
        if "日で生還" in status_str:
            raw_days = int(status_str.split("日")[0])
        elif "未生還" in status_str:
            raw_days = 999

        results.append({
            "日付": date_str,
            "終値": f"{int(p0):,}",
            "1日後": get_future_mark(p0, p1),
            "3日後": get_future_mark(p0, p3),
            "10日後": get_future_mark(p0, p10),
            "最大逆行": f"-{int(max_reverse):,}円" if max_reverse > 0 else "0円",
            "マイクロ1枚": f"{micro_loss:,}円" if micro_loss < 0 else "0円",
            "ステータス": status_str,
            "_raw_days": raw_days
        })

    res_df = pd.DataFrame(results)

    # 5. スマホ専用極小レスポンシブHTMLテーブル（未来対応＆赤バツ自動装飾）
    table_html = """
    <div style="overflow-x:auto; width:100%; -webkit-overflow-scrolling:touch;">
        <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:11px; text-align:center; color:#e0e0e0; background-color:#1e1e1e;">
            <thead>
                <tr style="background-color:#2d2d2d; border-bottom:2px solid #444;">
                    <th style="padding:6px 2px;">日付</th>
                    <th style="padding:6px 2px;">終値</th>
                    <th style="padding:6px 1px;">1日後</th>
                    <th style="padding:6px 1px;">3日後</th>
                    <th style="padding:6px 1px;">10日後</th>
                    <th style="padding:6px 2px;">最大逆行</th>
                    <th style="padding:6px 2px; color:#ff6b6b;">マイ1枚</th>
                    <th style="padding:6px 2px;">ステータス</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for _, row in res_df.iterrows():
        bg_style = ""
        if "未生還" in row['ステータス']:
            bg_style = "background-color:#3a2222;"
        elif "追跡中" in row['ステータス']:
            bg_style = "background-color:#223a22;"
            
        table_html += f"<tr style='border-bottom:1px solid #333; {bg_style}'>"
        table_html += f"<td style='padding:6px 2px; font-weight:bold;'>{row['日付']}</td>"
        table_html += f"<td style='padding:6px 2px;'>{row['終値']}</td>"
        
        # 「×」の時だけ赤文字にするインラインCSS
        m1_style = "color:#ff5555; font-weight:bold;" if row['1日後'] == "×" else ("color:#888;" if row['1日後'] == "-" else "")
        m3_style = "color:#ff5555; font-weight:bold;" if row['3日後'] == "×" else ("color:#888;" if row['3日後'] == "-" else "")
        m10_style = "color:#ff5555; font-weight:bold;" if row['10日後'] == "×" else ("color:#888;" if row['10日後'] == "-" else "")
        
        table_html += f"<td style='padding:6px 1px; {m1_style}'>{row['1日後']}</td>"
        table_html += f"<td style='padding:6px 1px; {m3_style}'>{row['3日後']}</td>"
        table_html += f"<td style='padding:6px 1px; {m10_style}'>{row['10日後']}</td>"
        
        table_html += f"<td style='padding:6px 2px;'>{row['最大逆行']}</td>"
        table_html += f"<td style='padding:6px 2px; color:#ff8787;'>{row['マイクロ1枚']}</td>"
        table_html += f"<td style='padding:6px 2px; font-weight:bold;'>{row['ステータス']}</td>"
        table_html += "</tr>"
        
    table_html += "</tbody></table></div>"
    
    st.components.v1.html(table_html, height=300, scrolling=False)

    # 6. タイムスパン別・生還確率推論
    valid_days = res_df["_raw_days"].dropna()
    total_valid = len(valid_days)
    
    if total_valid > 0:
        p_3days = (valid_days <= 3).sum() / total_valid * 100
        p_7days = (valid_days <= 7).sum() / total_valid * 100
        p_14days = (valid_days <= 14).sum() / total_valid * 100
        
        st.markdown("### 🔮 タイムスパン別・生還確率推論")
        st.info(f"⏳ **3日以内** に無事生還: **{p_3days:.1f}%**")
        st.success(f"🔋 **7日以内** に粘って生還: **{p_7days:.1f}%**")
        st.warning(f"🛡️ **14日以内** にじっくり生還: **{p_14days:.1f}%**")
    else:
        st.text("生還確率：計算データ不足")

if __name__ == "__main__":
    st.title("🎛️ タイムワープコントロール")
    lookback = st.slider("⏰ 過去へタイムワープ（遡る日数）", min_value=0, max_value=100, value=0, step=1)
    show_endure_board(slider_lookback_days=lookback)
