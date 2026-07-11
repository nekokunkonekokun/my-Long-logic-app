import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, time, timedelta

# スマホ向けにレイアウトを「centered」に設定
st.set_page_config(layout="centered", page_title="Heat Map Mobile Pro")
st.title("📱 Market War Map: Intelligence")

# スマホの操作性を考慮し、設定は折りたたみ式のエキスパンダーに集約
with st.expander("⚙️ 分析設定 (期間・感度)", expanded=False):
    ticker = st.text_input("銘柄コード", value="NIY=F")
    
    today = datetime.now().date()
    start_date = st.date_input("開始日", value=today - timedelta(days=5))
    a_start = st.slider("開始時間 (時)", 0, 24, 0)
    
    end_date = st.date_input("終了日", value=today)
    b_end = st.slider("終了時間 (時)", 0, 24, 24)
    
    spike_threshold = st.slider("感度 (σ)", 1.0, 3.0, 2.0, 0.1)
    
    # 【アップデート】固定の日数ではなく、全データに対する相対比率で指定
    halflife_ratio = st.slider("時間減衰の鋭さ (全期間に対する比率)", 0.05, 0.50, 0.25, 0.05)
    
    run_btn = st.button("🔥 需給ダイナミクスを分析", use_container_width=True)

if run_btn:
    start_dt = datetime.combine(start_date, time(hour=a_start))
    if b_end == 24:
        end_dt = datetime.combine(end_date + timedelta(days=1), time(0, 0))
    else:
        end_dt = datetime.combine(end_date, time(hour=b_end))
    
    with st.spinner("市場のしこり・清算データを解析中..."):
        # 指定された期間でデータを取得（30分足）
        df = yf.download(ticker, start=start_dt, end=end_dt, interval="30m")
        
        if df.empty or len(df) < 10:
            st.warning("⚠️ 指定した期間に十分なデータ数がありません。期間を広げてください。")
        else:
            # MultiIndexの解除処理
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            # データクレンジングと基本統計の計算
            df['Volume'] = df['Volume'].fillna(0)
            df['Range'] = df['High'] - df['Low']
            
            # ボラティリティ統計 (期間の長さに応じて窓関数を動的に変更)
            window = max(10, int(len(df) * 0.15)) # 全データ数の15%を統計窓とする
            mean_r = df['Range'].rolling(window, min_periods=1).mean()
            std_r = df['Range'].rolling(window, min_periods=1).std()
            
            # 0以下のstdによるゼロ除算を防ぐ
            std_r = std_r.replace(0, np.nan).fillna(1e-6)
            df['Vol_Factor'] = ((df['Range'] - mean_r) / std_r).clip(lower=0)
            df['Direction'] = np.sign(df['Close'] - df['Open'])
            
            # ==========================================
            # 1. 【核心】スケール不変型・時間重み付け（Time-decay）
            # ==========================================
            # 全期間の秒数を取得
            total_duration = (df.index[-1] - df.index[0]).total_seconds()
            if total_duration == 0: total_duration = 1
            
            # 現在（最新データ）からの「相対的な経過時間（0.0〜1.0）」を算出
            # 最も新しいデータが 0.0、最も古いデータが 1.0 になる
            df['Relative_Time_Distance'] = (df.index[-1] - df.index).total_seconds() / total_duration
            
            # 指数減衰ウェイトの計算
            # 最新＝1.0、指定比率の過去に遡ると重みが半分（0.5）になる
            df['Time_Weight'] = np.exp(-np.log(2) * df['Relative_Time_Distance'] / halflife_ratio)
            
            # War Map 計算の実行
            bins = np.linspace(float(df['Low'].min()), float(df['High'].max()), 80)
            labels = bins[:-1] + (bins[1] - bins[0]) / 2
            v_profile, buy_spike, sell_spike = np.zeros(len(labels)), np.zeros(len(labels)), np.zeros(len(labels))
            
            for _, row in df.iterrows():
                vol, factor = float(row['Volume']), float(row['Vol_Factor'])
                weight = float(row['Time_Weight']) # 相対時間による重み
                
                mask = (labels >= float(row['Low'])) & (labels <= float(row['High']))
                count = np.sum(mask)
                if count == 0: continue
                
                # 時間重みを出来高に乗算
                v_profile[mask] += (vol / count) * weight
                
                if factor > spike_threshold:
                    val = (vol * factor / count) * weight
                    if row['Direction'] >= 0: buy_spike[mask] += val
                    else: sell_spike[mask] += val
            
            # ==========================================
            # スマホ最適化グラフィック表示
            # ==========================================
            fig, ax = plt.subplots(figsize=(6, 10)) # 縦長画面専用比率
            plt.style.use('dark_background')
            fig.patch.set_facecolor('#0e1117')
            ax.set_facecolor('#0e1117')
            
            bin_w = bins[1] - bins[0]
            ax.barh(labels, v_profile, height=bin_w*0.8, color='gray', alpha=0.15, label='Time-Decayed Vol')
            ax.barh(labels, buy_spike, height=bin_w*0.8, color='#00FFFF', alpha=0.7, label='Weighted Buy Panic')
            ax.barh(labels, -sell_spike, height=bin_w*0.8, color='#FF3333', alpha=0.7, label='Weighted Sell Panic')
            
            curr = float(df['Close'].iloc[-1])
            ax.axhline(y=curr, color='#00FF00', linestyle='--', linewidth=2, label=f'Current: {curr:,.0f}')
            
            ax.set_title(f"Time-Weighted War Map: {ticker}", fontsize=12, color='white')
            ax.legend(loc='upper right', fontsize=9)
            ax.tick_params(colors='white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            st.pyplot(fig, use_container_width=True)
            
            # ==========================================
            # 2. 【核心】スケール不変型・需給ダイナミクス解析
            # ==========================================
            st.subheader("📊 需給インテリジェンス・レポート")
            
            # 全データ数の「直近20%」を分析対象のウィンドウ（Recent Window）とする
            lookback_ratio = 0.2 
            lookback_count = max(2, int(len(df) * lookback_ratio))
            recent_df = df.tail(lookback_count)
            
            # ① 直近ウィンドウ内での最安値とその時のパニック判定
            lowest_idx = recent_df['Low'].idxmin()
            lowest_price = recent_df.loc[lowest_idx, 'Low']
            is_panic_drop = (recent_df.loc[lowest_idx, 'Vol_Factor'] > spike_threshold) and (recent_df.loc[lowest_idx, 'Direction'] < 0)
            
            # ② 現在値より上の価格帯にある「最大ボリュームの売り圧力」の新鮮度を測る
            upper_zone = df[(df['Low'] > curr)]
            if not upper_zone.empty:
                # 最も出来高スパイクが激しかった行を抽出
                heavy_sell_zone = upper_zone.sort_values(by='Vol_Factor', ascending=False).head(1)
                heavy_sell_price = float(heavy_sell_zone['Close'].iloc[0])
                # その売りが発生したタイミングの、全体における相対位置（0=最新, 1=最古）
                heavy_sell_age_ratio = float(heavy_sell_zone['Relative_Time_Distance'].iloc[0])
            else:
                heavy_sell_price = curr
                heavy_sell_age_ratio = 0
            
            # テキストの動的生成
            analysis_text = ""
            
            # ロスカット（清算）の推測ロジック
            if is_panic_drop and curr > lowest_price:
                analysis_text += f"**【ロングの強制清算とリセット】**\n分析期間の直近（終盤20%の区間）において、{lowest_price:,.0f}円への急落時にボラティリティを伴う激しいSell Panic（投げ売り）が観測されています。この時点で捕まっていたロング勢の多くが**「強制ロスカット（売らされた）」**され、過去の買いしこりは一度リセットされた可能性が高いです。\n\n"
            else:
                analysis_text += f"**【底堅さの検証】**\n直近の最安値 {lowest_price:,.0f}円付近では、致命的なパニック売り（出来高を伴う垂直落下）までは発展しておらず、断断続的な買い戻しが下値を支えている状態です。\n\n"
            
            # 上値の「しこり」vs「新規ショート」の推測ロジック
            if heavy_sell_price > curr:
                # 全期間の直近25%以内の時間で発生した売りなら「新鮮な新規ショート」とみなす
                if heavy_sell_age_ratio < 0.25:
                    analysis_text += f"**【上値の軽さと新規ショートの台頭】**\n現在値より上の {heavy_sell_price:,.0f}円付近で見られる売り圧力は、過去の古い死に玉（しこり）ではなく、直近のトレンドの中で形成された**「追随の新規ショート（売り崩し）」**である可能性が濃厚です。このショート勢が買い戻し（踏み上げ）を迫られた場合、上値は真空地帯となり、予想以上に軽くなるシナリオを警戒すべきです。"
                else:
                    analysis_text += f"**【過去の遺物化した壁】**\n上の {heavy_sell_price:,.0f}円付近に赤のボリュームが見えますが、これは指定期間の中では比較的「古い時間帯」に発生したデータです。時間減衰ロジックにより、現在の実際の壁としての強度は大きく低下しており、見た目のグラフほど強力な抵抗帯にはならない可能性があります。"
            else:
                analysis_text += "**【青天井・真空地帯】**\n現在値より上に目立った売り圧力の壁（赤のスパイク）は観測されません。ショートの買い戻しを巻き込んだ上昇トレンドが継続しやすい需給バランスです。"
                
            st.chat_message("assistant").write(analysis_text)
