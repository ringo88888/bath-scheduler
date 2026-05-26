import streamlit as st
from datetime import date, timedelta, datetime
import database as db
from scheduler import generate_schedule

DAY_JP = ["月", "火", "水", "木", "金", "土", "日"]
def make_icon(label, bg, color):
    return (
        f"<span style='background:{bg};color:{color};"
        f"border-radius:50%;width:24px;height:24px;"
        f"display:inline-flex;align-items:center;justify-content:center;"
        f"font-size:11px;font-weight:700;margin-right:2px'>{label}</span>"
    )


def make_cell(assist, wc, mi, name, last_str):
    icons = assist
    if wc:
        icons += make_icon("車", "#185FA5", "#fff")
    if mi:
        icons += make_icon("見", "#1D9E75", "#fff")
    return (
        f"<div style='background:#EAF3DE;border:1px solid #C0DD97;"
        f"border-radius:4px;padding:6px 8px;height:90px;font-size:13px'>"
        f"{icons}<br>"
        f"<b style='font-size:14px'>{name}</b><br>"
        f"<span style='color:#3B6D11;font-size:12px'>{last_str}</span>"
        f"</div>"
    )

def get_assist_icon(assist_type):
    icons = {
        "duo":    make_icon("二", "#EEEDFE", "#3C3489"),
        "nurse":  make_icon("Ns", "#E6F1FB", "#0C447C"),
        "helper": make_icon("助", "#E1F5EE", "#085041"),
    }
    return icons.get(assist_type, "")


def render():
    settings = db.get_settings()
    if not settings.get("start_date"):
        st.warning("先に設定ページで開始日を設定してください")
        return

    origin = date.fromisoformat(settings["start_date"])

    if "current_week" not in st.session_state:
        st.session_state.current_week = str(origin)

    current_week = date.fromisoformat(st.session_state.current_week)

    # ─── 週ナビゲーション ──────────────────────────────────
    col1, col2, col3, col4 = st.columns([1, 2, 1, 2])
    with col1:
        if st.button("◀ 前の週"):
            if current_week > origin:
                st.session_state.current_week = str(current_week - timedelta(weeks=1))
                st.rerun()
    with col2:
        end_of_week = current_week + timedelta(days=6)
        st.markdown(
            f"**{current_week.month}/{current_week.day}"
            f"（{DAY_JP[current_week.weekday()]}）〜 "
            f"{end_of_week.month}/{end_of_week.day}"
            f"（{DAY_JP[end_of_week.weekday()]}）**"
        )
    with col3:
        if st.button("次の週 ▶"):
            next_week = current_week + timedelta(weeks=1)
            existing = db.get_schedules_for_week(str(next_week))
            if not existing:
                new_schedules = generate_schedule(next_week)
                db.save_history_snapshot(str(next_week), new_schedules)
                db.save_schedules_bulk(new_schedules)
            st.session_state.current_week = str(next_week)
            st.rerun()
    with col4:
        if st.button("🔄 この週を再生成"):
            schedules = generate_schedule(current_week)
            db.save_history_snapshot(str(current_week), schedules)
            db.save_schedules_bulk(schedules)
            st.rerun()

    st.divider()

    # ─── データ取得 ────────────────────────────────────────
    schedules = db.get_schedules_for_week(str(current_week))
    patients = db.get_all_patients()
    patient_map = {p["id"]: p for p in patients}

    if not patients:
        st.info("患者が登録されていません。設定ページから患者を追加してください。")
        return

    bath_days = list(map(int, settings.get("bath_days", "0,1,2,3,4,5").split(",")))
    am_only_days = list(map(int, settings.get("bath_days_am_only", "5").split(","))) \
        if settings.get("bath_days_am_only") else []
    pm_start = settings.get("pm_start", "13:30")
    am_end = settings.get("am_end", "12:00")

    from scheduler import generate_time_slots
    all_slots = set()
    week_dates = [current_week + timedelta(days=i) for i in range(7)]
    for d in week_dates:
        wd = d.weekday()
        if wd not in bath_days:
            continue
        include_pm = wd not in am_only_days
        times = generate_time_slots(
            settings["am_start"], am_end, pm_start,
            int(settings["duration_min"]), settings["end_limit"], include_pm
        )
        all_slots.update(times)

    sorted_slots = sorted(all_slots)

    schedule_map = {}
    for s in schedules:
        key = (s["date"], s["time_slot"])
        schedule_map[key] = s

    # ─── ヘッダー行 ────────────────────────────────────────
    header_cols = st.columns([1] + [1] * 7)
    with header_cols[0]:
        st.markdown("**時間**")
    for i, d in enumerate(week_dates):
        with header_cols[i + 1]:
            wd = d.weekday()
            if wd not in bath_days:
                st.markdown(f":gray[{DAY_JP[wd]}  \n{d.month}/{d.day}]")
            else:
                st.markdown(f"**{DAY_JP[wd]}**  \n{d.month}/{d.day}")

    # ─── 時間枠ごとの行 ────────────────────────────────────
    prev_section = None
    for slot_time in sorted_slots:
        section = "午後" if slot_time >= pm_start else "午前"
        if section != prev_section:
            st.markdown(
                f"<p style='color:gray;font-size:12px;margin:4px 0'>"
                f"── {section} ──</p>",
                unsafe_allow_html=True
            )
            prev_section = section

        end_dt = datetime.strptime(slot_time, "%H:%M") + timedelta(minutes=int(settings["duration_min"]))
        time_label = f"{slot_time}–{end_dt.strftime('%H:%M')}"

        row_cols = st.columns([1] + [1] * 7)
        with row_cols[0]:
            st.markdown(
                f"<small style='color:black'>{time_label}</small>",
                unsafe_allow_html=True
            )

        for i, d in enumerate(week_dates):
            with row_cols[i + 1]:
                wd = d.weekday()
                key = (str(d), slot_time)
                sched = schedule_map.get(key)

                if wd not in bath_days:
                    st.markdown(
                        "<div style='background:#B4B2A9;height:90px;border-radius:4px'></div>",
                        unsafe_allow_html=True
                    )
                elif wd in am_only_days and slot_time >= pm_start:
                    st.markdown(
                        "<div style='background:#B4B2A9;height:90px;border-radius:4px'></div>",
                        unsafe_allow_html=True
                    )
                elif slot_time >= am_end and slot_time < pm_start:
                    # 午前終了時間〜午後開始時間の間は入浴不可
                    st.markdown(
                        "<div style='background:#B4B2A9;height:90px;border-radius:4px'></div>",
                        unsafe_allow_html=True
                    )
                elif sched:
                    p = patient_map.get(sched["patient_id"])
                    if p:
                        assist = get_assist_icon(p["assist_type"])
                        wc = bool(p["wheelchair"])
                        mi = bool(p["monitoring"])
                        last = db.get_last_bath_date(p["id"], str(d))
                        last_str = ""
                        if last:
                            ld = date.fromisoformat(last)
                            last_str = f"last:{ld.month}/{ld.day}"
                        st.markdown(
                            make_cell(assist, wc, mi, p["name"], last_str),
                            unsafe_allow_html=True
                        )
                else:
                    st.markdown(
                        "<div style='background:#EAF3DE;height:90px;border-radius:4px;border:1px solid #C0DD97'></div>",
                        unsafe_allow_html=True
                    )

    st.divider()

    # ─── Undoボタン ────────────────────────────────────────
    if st.button("↩️ 自動調整前に戻す"):
        snapshot = db.get_latest_history(str(current_week))
        if snapshot:
            db.save_schedules_bulk(snapshot)
            st.success("スナップショットに戻しました")
            st.rerun()
        else:
            st.warning("戻せる履歴がありません")