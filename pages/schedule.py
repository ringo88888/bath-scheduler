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
        weekday = d.weekday()  #日付から入浴可能な曜日番号を取得
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