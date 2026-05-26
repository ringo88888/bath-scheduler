import streamlit as st
from datetime import date, time
import database as db

#col2で使用している、文字列をtime型に直す関数
def _parse_time(time_str):
    parts = time_str.split(":")  # "09:30" → ["09", "30"]
    h = int(parts[0])  # "09" → 9
    m = int(parts[1])  # "30" → 30
    return time(h, m)  # time(9, 30) を返す

def render():
    st.subheader("⚙️ 設定")

    settings = db.get_settings()
    patients = db.get_all_patients()


    st.markdown("#### 基本設定") #見出しレベル４、「＃」は見出しレベルを数で表す

    col1, col2 = st.columns(2) #画面を２分割
    with col1:
        start_date = st.date_input(
            "開始日",
            value=date.fromisoformat(settings["start_date"]) if settings.get("start_date") else date.today()
        )

        #st.selectbox("ラベル", options=..., index=...)ドロップダウンメニューを表示するStreamlitの決まった書き方
        duration_options = list(range(10, 65, 5)) #10-60まで、5分間隔のリスト作成
        duration = st.selectbox(
            "1人あたりの入浴時間（分）",
            options=duration_options,
            index=duration_options.index(int(settings.get("duration_min", 30)))
            if int(settings.get("duration_min", 30)) in duration_options else 4
        )
#         ①もし
# settings.get("duration_min", 30)→設定値から取得する、つまりdatabase.pyのget_settings関数がsettingsデータベースから＊をとってきた中の、suration_minだけを、それをint型に変換したもの
# が、
# ➁Trueなら（設定値がリスト内にあれば）
# duration_options = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
# その値（ここでいう30という整数）をduration_optionsリストの何番目にあるかを調べるのがduration_options.index(30)
# duration_options = [10, 15, 20, 25, 30, ...]
# #                   0   1   2   3   4
# なので、０番目から数えて30は４番目
# つまり、今回は４番目を初期設定にする
# ➂Falseなら（なければ）
# ４番目の（３０分）を初期設定にする

        #数字を入力する部品を表示するStreamlitの決まった書き方
        weekly_count = st.number_input(
            "週の入浴回数",
            min_value=1, max_value=7,
            value=int(settings.get("weekly_count", 2))
        )

        min_interval = st.number_input(
            "前回入浴からの最小間隔（日）",
            min_value=0, max_value=6,
            value=int(settings.get("min_interval_days", 2)),
            help="週2回以上の場合に有効"
        )

    with col2:
        #st.time_input("ラベル", value=初期値) 時間を選択する
        am_start = st.time_input(
            "午前の開始時間",
            value=_parse_time(settings.get("am_start", "09:30")) #文字列→time型に変換
        )
        pm_start = st.time_input(
            "午後の開始時間",
            value=_parse_time(settings.get("pm_start", "13:30"))
        )
        end_limit = st.time_input(
            "絶対終了時刻",
            value=_parse_time(settings.get("end_limit", "17:00"))
        )

        #入浴の曜日選択の関数
        #st.multiselect("ラベル", options=選択肢リスト, default=最初から選ばれているもの)
        days_options = ["月", "火", "水", "木", "金", "土", "日"]
        available_days = st.multiselect(
            "入浴可能曜日",
            options=days_options,
            default=settings.get("available_days", "月,水,金,土").split(",")
        )

    if st.button("💾 設定を保存"):
        db.save_settings({
            "start_date": str(start_date),
            "duration_min": duration,
            "weekly_count": weekly_count,
            "min_interval_days": min_interval,
            "am_start": str(am_start),
            "pm_start": str(pm_start),
            "end_limit": str(end_limit),
            "available_days":",".join(available_days)
        })
        st.success("設定を保存しました")

    # -------------------------------------------------------
    # TODO: 患者個別設定（発表後に追加予定）
    # ・リハビリ・検査の時間を避ける設定
    # ・午前／午後の入浴希望設定
    # -------------------------------------------------------