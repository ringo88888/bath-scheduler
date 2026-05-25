from datetime import date, timedelta, datetime
from database import get_settings, get_all_patients, get_last_bath_date



#「入浴可能な時間枠のリストを生成する」関数
#   1. slotsを空で用意する
#   2. add_slots()で午前枠を生成してslotsに追加する
#   3. 午後ありならadd_slots()で午後枠も追加する
#   4. 完成したslotsを返す
def generate_time_slots(am_start:str, pm_start: str, duration_min: int, end_limit: str,include_pm: bool) -> list[str]:
    #「この関数は文字列のリストを返しますよ」という宣言

    slots = []
    #slots = ["09:30", "10:00", "10:30", ...]  # 文字列の時間枠が入る

    def add_slots(start_str, stop_str):
        current = datetime.strptime(start_str, "%H:%M") #strptimeは文字列を日時型に変換する
        stop = datetime.strptime(stop_str, "%H:%M")
        while True:
            next_time = current + timedelta(minutes=duration_min)
            if next_time > stop:
                break
            slots.append(current.strftime("%H:%M")) #appendはリストに要素を追加、strftimeは日時型を文字列に変換
            current = next_time

    add_slots(am_start, pm_start if not include_pm else end_limit)

    if include_pm:
        add_slots(pm_start, end_limit)

    return slots
    #完成した時間枠のリストを返す


#表示する日付を計算
def get_week_dates(week_start: date) -> list[date]:
    return [week_start + timedelta(days=i) for i in range(7)]
            #開始日に0～7日を足すことで、開始日に対応した日付を計算


#週の開始日を受け取って、その週の入浴スケジュールを自動生成してリストで返す関数
def generate_schedule(week_start:date) -> list[dict]:
    settings = get_settings()
    patients = get_all_patients()

    if not settings or not patients:
        return []
    
    bath_days = list(map(int, settings["bath_days"].split(",")))
    #["文字列"].split(",")で文字列のままカンマで分解する、mapで整数に変換する
    am_only_days = list(map(int, settings.get("bath_days_am_only", "5").split(","))) \
        if settings.get("bath_days_am_only") else []
    #.get(キー, デフォルト値),キーがあれば取得、なければデフォルト値を使う。もしエラーなどでキーがなければデフォルト"5"を使う
    am_start = settings["am_start"] # "09:30"
    pm_start = settings["pm_start"] # "13:30"
    duration = int(settings["duration_min"]) # 30
    end_limit = settings["end_limit"] # "17:00"
    weekly_count = int(settings["weekly_count"]) # 2
    min_interval = int(settings["min_interval_days"]) # 2

    week_dates = get_week_dates(week_start)

    #入浴可能な枠全部入れるリスト
    available_slots = []
    #例(date(2025,5,25), "09:30"),  # 月曜9:30

    #曜日ごとの午前/午後枠を一時的に入れる
    am_slots_by_day = {}
    #例date(2025,5,25): ["09:30", "10:00", "10:30"],  # 月曜の午前枠
    pm_slots_by_day = {}


    for d in week_dates:  #week_datesの日付を1つずつdに入れながら繰り返す
        weekday = d.weekday()  #日付から曜日番号を取得
        if weekday not in bath_days:   #もしdが、weekday＝入用可能な曜日に含まれていなければ
            continue  #スキップする
        include_pm = weekday not in am_only_days
        #現在am_only_daysはデフォの5=土曜、include_pmは午後ありなので、土曜はデフォで午後ないのでFalseになる

        times = generate_time_slots(am_start, pm_start, duration, end_limit, include_pm)

        am_times = [t for t in times if t < pm_start]
        #timesの中からpm_start（13:30）より前の時間だけ取り出す
        pm_times = [t for t in times if t >= pm_start]

        #曜日ごとに午前枠・午後枠を辞書に入れる
        am_slots_by_day[d] = am_times
        pm_slots_by_day[d] = pm_times

    #入浴可能な枠を分散配置の順番でavailable_slotsに並べる
    #am_slots_by_dayはyぷ尾ごとの午前枠リスト,各曜日の午前枠数を調べて最大値を取得
    max_am = max((len(v) for v in am_slots_by_day.values()), default=0)
    #枠番号（0,1,2）でループ
    for slot_idx in range(max_am):
        #各枠番号に対して全曜日をループ
        for d in week_dates:
            if d in am_slots_by_day and slot_idx < len(am_slots_by_day[d]):
                available_slots.append((d, am_slots_by_day[d][slot_idx]))

    max_pm = max((len(v) for v in pm_slots_by_day.values()), default=0)
    for slot_idx in range(max_pm):
        for d in week_dates:
            if d in pm_slots_by_day and slot_idx < len(pm_slots_by_day[d]):
                available_slots.append((d, pm_slots_by_day[d][slot_idx]))

    #①max_am = 3  # 一番枠数が多い曜日が3枠
    #➁slot_idx = 0 → 1枠目（09:30）, slot_idx = 1 → 2枠目（10:00）, slot_idx = 2 → 3枠目（10:30）
    #➂slot_idx=0のとき：月09:30 → 火09:30 → 水09:30 → 木09:30 → 金09:30 → 土09:30
    #  slot_idx=1のとき：月10:00 → 火10:00 → 水10:00 → 木10:00 → 金10:00 → 土10:00
    #  slot_idx=2のとき：月10:30 → 火10:30 → 水10:30 → 木10:30 → 金10:30 → 土（スキップ）
    #④最終的なavailable_slotsの中身
    #  [
#     (5/25, "09:30"),  # 月・午前1枠目
#     (5/26, "09:30"),  # 火・午前1枠目
#     (5/27, "09:30"),  # 水・午前1枠目
#     ...
#     (5/25, "10:00"),  # 月・午前2枠目
#     (5/26, "10:00"),  # 火・午前2枠目
#     ...
#     (5/25, "13:30"),  # 月・午後1枠目
#     (5/26, "13:30"),  # 火・午後1枠目
#     ...
# ]


    booked_slots = set() #集合体 例booked_slots.add(("2025-05-25", "09:30"))
    result = [] #最終的に追加されるスケジュール

    week_start_str = str(week_start) #week_startはdate型なのでstr文字型に変換
    last_bath = {  #各患者の最終入浴日を取得して辞書を作る
        p["id"]: get_last_bath_date(p["id"], week_start_str) #辞書内包表記 {キー: 値 for 変数 in リスト}
        for p in patients
    }

    week_count = {p["id"]: 0 for p in patients}  #入浴した回数を取得して辞書を作る 辞書内包表記、最初は全員０回

    #全患者の最終入浴日のリスト ※前回から何日空いているか計算用
    week_last = {p["id"]: (
        date.fromisoformat(last_bath[p["id"]]) if last_bath[p["id"]] else None
        #date.fromisoformatでISO形式の文字列をdate型に変換 つまり
        #last_bath[p["id"]]最終入浴日が存在(True)ならば、date型に変換する、最終入浴日がないならNoneのまま
    ) for p in patients}


    for _ in range(weekly_count): #週２回繰り返す（weekly_countの設定数）
        for p in patients: #全患者を順番に処理する
            if week_count[p["id"]] >= weekly_count: #すでに2回割り当て済みならスキップ
                continue

            assigned = False #その患者に枠が割り当てられたかどうかを記録する変数。最初はFalse（未割り当て）
            for slot_date, slot_time in available_slots: #available_slots(日付, 時刻)のタプルリストを、日付と時刻それぞれの変数に分けられるようにする（アンパックという）
                slot_key = (str(slot_date), slot_time) #予約済みチェックに使うキーを作る。例slot_key = ("2025-05-25", "09:30")booked_slotsに同じキーがあれば「すでに予約済み」とわかる

                if slot_key in booked_slots:
                    continue

                prev = week_last[p["id"]] #辞書名[キー]でキーに対応する値が取れる
                if prev is not None: #前回入浴日が存在する場合だけ間隔チェック is not Noneは「None」ではない
                    gap = (slot_date - prev).days
                    if gap < min_interval:
                        continue

                booked_slots.add(slot_key)
                week_count[p["id"]] += 1  #そのidの患者の今週の入浴回数に1を足す
                week_last[p["id"]] = slot_date #そのidの患者の最終入浴日を今回割り当てた日付で上書きする

                result.append({
                    "patient_id": p["id"],
                    "date": str(slot_date), #入浴する日
                    "time_slot": slot_time,  #入浴する時間
                    "is_actual": 0,
                    "is_extra": 0,
                    "note": None,
                })
                assigned = True
                break

    return result