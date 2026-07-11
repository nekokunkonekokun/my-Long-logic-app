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
# 【修正】網羅的需給ダイナミクス・マトリクス
# ==========================================
st.subheader("📊 需給インテリジェンス・レポート")

# 1. 基礎データの抽出
total_len = len(df)
lookback_count = max(2, int(total_len * 0.20))
recent_df = df.tail(lookback_count)

# 期間内の全体値幅と現在地の相対位置 (0=最安値, 1=最高値)
global_min = df['Low'].min()
global_max = df['High'].max()
price_range = global_max - global_min if (global_max - global_min) > 0 else 1
current_position_ratio = (curr - global_min) / price_range

# 直近ウィンドウの最安値とパニック判定
lowest_idx = recent_df['Low'].idxmin()
lowest_price = recent_df.loc[lowest_idx, 'Low']
is_panic_drop = (recent_df.loc[lowest_idx, 'Vol_Factor'] > spike_threshold) and (recent_df.loc[lowest_idx, 'Direction'] < 0)

# パニック後の反発力判定
average_range = recent_df['Range'].mean()
rebound_amt = curr - lowest_price
is_strong_rebound = rebound_amt > (average_range * 1.5)

# 上値の最大しこりゾーンの解析
upper_zone = df[(df['Low'] > curr)]
has_upper_wall = False
is_fresh_short = False

if not upper_zone.empty:
    heavy_sell_zone = upper_zone.sort_values(by='Vol_Factor', ascending=False).head(1)
    heavy_sell_price = float(heavy_sell_zone['Close'].iloc[0])
    heavy_sell_age = float(heavy_sell_zone['Relative_Time_Distance'].iloc[0])
    
    # 出来高が一定以上ある場合のみ「壁」とみなす
    if float(heavy_sell_zone['Vol_Factor'].iloc[0]) > spike_threshold:
        has_upper_wall = True
        if heavy_sell_age < 0.25: # 直近25%以内の新しい売り
            is_fresh_short = True

# 2. 多層条件分岐によるテキストの動的生成
analysis_text = ""

# --- パターンA：現在地が高値圏（上昇トレンド・踏み上げ） ---
if current_position_ratio > 0.75:
    analysis_text += "**【市場支配：踏み上げ（ショートスクイーズ）局面】**\n"
    analysis_text += f"現在値は指定期間の最高値圏（相対位置: {current_position_ratio:.0%}）を猛烈に売り崩そうとしたショート勢の限界ラインに達しています。\n"
    
    if has_upper_wall and is_fresh_short:
        analysis_text += f"直近で {heavy_sell_price:,.0f}円付近に形成された売りボリュームは、捕まったロングのしこりではなく、上値を抑え込もうとした『新規の強気ショート』です。この水準を明確にブレイクした場合、これらショート勢の買い戻し（強制清算）を巻き込んだ**青天井の踏み上げ相場**に発展する確率が極めて高くなります。"
    else:
        analysis_text += "現在値より上に目立った売り圧力（しこり）の壁は観測されません。売り手の降伏による真空地帯を上昇する買い手優位のダイナミクスが継続しています。"

# --- パターンB：現在地が安値圏かつ、パニックからの強い反発（本物の大底・主客逆転） ---
elif current_position_ratio < 0.35 and is_panic_drop and is_strong_rebound:
    analysis_text += "**【需給反転：スマートマネーによる吸収（大底の形成）】**\n"
    analysis_text += f"過去の安値圏において {lowest_price:,.0f}円への垂直落下に伴う激しいSell Panic（投げ売り）が発生しましたが、そこから現在の {curr:,.0f}円までV字の力強い反発が確認されています。\n"
    analysis_text += "これは、パニックに陥った個人投資家の投げ玉を、大口投資家（スマートマネー）が下値で完全に吸収し尽くした（ドレインした）動かぬ証拠です。**過去のしこり玉は完全に清算（リセット）され、需給の主客逆転が完了した『絶好の仕込み時』の構造**を示しています。"

# --- パターンC：現在地が安値圏だが、反発せず張り付き（落ちてくるナイフ・罠） ---
elif current_position_ratio < 0.35 and is_panic_drop and not is_strong_rebound:
    analysis_text += "**【危険地帯：偽の底打ち・セリングクライマックス未遂】**\n"
    analysis_text += f"直近で {lowest_price:,.0f}円への急落と激しいパニック売りが発生していますが、現在値はその安値圏から全く浮上できていません。\n"
    analysis_text += "これは『投げ売りは出たが、それを上回る大口の買い手がまだ市場に参入していない』ことを意味します。過去の捕まり玉が清算されたからといって安易に反転を期待すべきではなく、**買い手不在のまま底が抜ける「落ちてくるナイフ」の典型例**です。静観を推奨します。"

# --- パターンD：現在地が中間のレンジ圏で、上に明確な古いしこりがある（上値が重い） ---
elif 0.35 <= current_position_ratio <= 0.75 and has_upper_wall and not is_fresh_short:
    analysis_text += "**【上値重配：過去の遺恨（しこり玉）による阻害】**\n"
    analysis_text += f"現在値はレンジの中間帯に位置していますが、上値の {heavy_sell_price:,.0f}円付近に、時間減衰を経てもなお根深く残る過去の巨大な買いスタック（捕まり玉）がそびえ立っています。\n"
    analysis_text += "価格が上昇するたびに、これら『助かりたいロング勢』のやれやれ売り（同値撤退注文）が降ってくるため、需給構造としては非常に上値が重く、ブレイクには相当なエネルギー（材料や大口の圧倒的な買い）が必要です。"

# --- パターンE：それ以外のニュートラル・レンジ状態 ---
else:
    analysis_text += "**【均衡状態：需給のパワーバランス拮抗】**\n"
    analysis_text += f"現在の価格（相対位置: {current_position_ratio:.0%}）付近では、直近で極端なパニック売買や大口の仕込みの偏りは見られません。\n"
    analysis_text += "過去の清算イベントの影響はすでに薄れており、市場は次の明確なトレンドや大口の仕掛け（ブレイクアウト）を待つ方向感のない均衡状態（パワーバランスのニュートラル）にあります。"

st.chat_message("assistant").write(analysis_text)

           
