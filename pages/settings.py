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
        am_end = st.time_input(
            "午前の終了時間",
            value=_parse_time(settings.get("am_end", "12:00"))
        )
        pm_start = st.time_input(
            "午後の開始時間",
            value=_parse_time(settings.get("pm_start", "13:30"))
        )
        end_limit = st.time_input(
            "午後終了時刻",
            value=_parse_time(settings.get("end_limit", "17:00"))
        )

        day_labels = ["月", "火", "水", "木", "金", "土", "日"]
        current_days = list(map(int, settings.get("bath_days", "0,1,2,3,4,5").split(",")))
        current_am_only = list(map(int, settings.get("bath_days_am_only", "5").split(","))) \
            if settings.get("bath_days_am_only") else []

        st.markdown("**入浴可能曜日**")
        day_cols = st.columns(7)
        selected_days = []
        am_only_days = []
        for i, (col, label) in enumerate(zip(day_cols, day_labels)):
            with col:
                if st.checkbox(label, value=(i in current_days), key=f"day_{i}"):
                    selected_days.append(i)
                    if st.checkbox("午前のみ", value=(i in current_am_only), key=f"amonly_{i}"):
                        am_only_days.append(i)

    if st.button("設定を保存"):
        db.save_settings({
            "start_date": str(start_date),
            "bath_days": ",".join(map(str, selected_days)),
            "bath_days_am_only": ",".join(map(str, am_only_days)),
            "am_start": am_start.strftime("%H:%M"),
            "pm_start": pm_start.strftime("%H:%M"),
            "duration_min": duration,
            "am_end": am_end.strftime("%H:%M"),
            "end_limit": end_limit.strftime("%H:%M"),
            "weekly_count": weekly_count,
            "min_interval_days": min_interval,
        })
        st.success("設定を保存しました")

    st.divider()

    # ─── 患者一覧 ──────────────────────────────────────────
    st.markdown("#### 患者一覧")

    if patients:
        for p in patients:
            with st.expander(f"{p['name']}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    assist_label = {"duo": "二人介助", "nurse": "看護師一人介助", "helper": "補助者一人介助"}
                    st.write(f"介助タイプ: **{assist_label.get(p['assist_type'], '')}**")
                    opts = []
                    if p["wheelchair"]: opts.append("車いす")
                    if p["monitoring"]: opts.append("見守り")
                    if opts: st.write(f"オプション: {', '.join(opts)}")
                with col2:
                    if st.button("退院", key=f"discharge_{p['id']}"):
                        db.discharge_patient(p["id"])
                        st.rerun()
    else:
        st.info("患者が登録されていません。下のフォームから追加してください。")

    st.divider()

    # ─── 患者追加フォーム ────────────────────────────────────
    st.markdown("#### 患者を追加する")

    with st.form("add_patient_form", clear_on_submit=True):
        name = st.text_input("患者氏名 *")
        assist_type = st.radio(
            "介助タイプ *",
            options=["duo", "nurse", "helper"],
            format_func=lambda x: {"duo": "二人介助", "nurse": "看護師一人介助", "helper": "補助者一人介助"}[x],
            horizontal=True
        )
        col1, col2 = st.columns(2)
        with col1:
            wheelchair = st.checkbox("車いす")
        with col2:
            monitoring = st.checkbox("見守り")

        submitted = st.form_submit_button("追加する")
        if submitted:
            if not name.strip():
                st.error("患者氏名を入力してください")
            else:
                db.add_patient(name.strip(), assist_type, wheelchair, monitoring)
                st.success(f"「{name}」を追加しました")
                st.rerun()

    st.divider()

    # ─── 管理表作成ボタン ─────────────────────────────────────
    if st.button(" 管理表を作成する → 管理表ページへ", type="primary", use_container_width=True):
        if not db.get_all_patients():
            st.error("先に患者を登録してください")
        elif not db.get_settings().get("start_date"):
            st.error("開始日を設定して保存してください")
        else:
            from scheduler import generate_schedule
            from datetime import date as d_cls
            settings = db.get_settings()
            week_start = d_cls.fromisoformat(settings["start_date"])
            schedules = generate_schedule(week_start)
            db.save_schedules_bulk(schedules)
            db.save_history_snapshot(str(week_start), schedules)
            st.session_state.current_week = str(week_start)
            st.session_state.page = "schedule"
            st.rerun()

    # -------------------------------------------------------
    # TODO: 患者個別設定（発表後に追加予定）
    # ・リハビリ・検査の時間を避ける設定
    # ・午前／午後の入浴希望設定
    # -------------------------------------------------------