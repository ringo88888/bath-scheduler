import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "bath.db"

#dataフォルダ、bath.dbを作成してsqliteに接続する
def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True) #bath.dbがなければ作る
    conn = sqlite3.connect(DB_PATH) #bath.dbに接続する← ここで初めてbath.dbが作られる
    conn.row_factory = sqlite3.Row #列名でアクセスできるようにする
    return conn #接続を呼び出し元に返す

# ─── 初期化initialize関数 ───────────────────────────────────────────────
#connはデータベースへの接続回線、cursorは受話器(窓口)
def initialize_db(): #initializeイニシャライズ＝初期化
    conn = get_connection()
    c = conn.cursor() #ここでbath.dataとsqlitedatabaseをcursorを通じて回線接続しました
    #c.execute()は「cursorを通じてSQLを実行する」＝受話器を持つ
    #もしpatientsテーブルが無ければ作る
    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            assist_type TEXT NOT NULL,
            wheelchair INTEGER DEFAULT 0,
            monitoring INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            start_date TEXT,
            bath_days TEXT DEFAULT '0,1,2,3,4,5',
            bath_days_am_only TEXT DEFAULT '5',
            am_start TEXT DEFAULT '09:30',
            pm_start TEXT DEFAULT '13:30',
            duration_min INTEGER DEFAULT 30,
            end_limit TEXT DEFAULT '17:00',
            am_end TEXT DEFAULT '12:00',
            weekly_count INTEGER DEFAULT 2,
            min_interval_days INTEGER DEFAULT 2
        )
    """)
    #患者は何人も追加するが、設定は「このアプリ全体でひとつ」で常にid=1の1行だけを更新して使う
    #bath_days TEXT DEFAULT 月=0、火=1、水=2、木=3、金=4、土=5、日=6
    #bath_days_am_only TEXT 午前のみ入浴可能な曜日


    #設定レコードを初回だけ自動挿入する
    c.execute("""
        INSERT OR IGNORE INTO settings (id) VALUES (1)
    """)
    #settingsテーブルにid=1のレコードがなければ挿入する。
    # OR IGNOREは「すでにあれば何もしない」という意味。これによってアプリを起動するたびにデフォルト設定が自動で用意される。


    c.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            is_actual INTEGER DEFAULT 0,
            is_extra INTEGER DEFAULT 0,
            note TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)
    #patient_id INTEGER NOT NULL　どの患者の予定かを示す
    # date TEXT NOT NULL　入浴予定日。'2025-05-25'
    # time_slot TEXT NOT NULL　入浴開始時刻。'09:30'
    # is_actual INTEGER　0が「予定」、1が「実施済み」。実際に入浴が完了したら1に更新。
    # is_extra INTEGER　0が「通常の予定」、1が「予備外入浴」。急に追加した入浴がここに入る。
    # note TEXT　メモ欄


    #どの週の予定なのか、その週の予定内容を保存する、いつ保存したかを保存テーブル
    c.execute("""
        CREATE TABLE IF NOT EXISTS schedule_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL,
            snapshot TEXT NOT NULL,
            saved_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    #week_start 2025-05-25'のようにその週の月曜日の日付を保存
    #snapshot その週の全予定をまるごと保存
    #saved_at スナップショットを保存した日時

    # デモ用初期データ（患者が0人のときだけ挿入）
    patient_count = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    if patient_count == 0:
        demo_patients = [
            ("佐藤 太郎", "duo", 0, 0),
            ("林 花子", "helper", 0, 1),
            ("鈴木 次郎", "helper", 1, 0),
            ("田中 良子", "nurse", 0, 0),
        ]
        conn.executemany("""
            INSERT INTO patients (name, assist_type, wheelchair, monitoring)
            VALUES (?, ?, ?, ?)
        """, demo_patients)

    # デモ用初期設定
    conn.execute("""
        UPDATE settings SET
            start_date = '2026-05-27',
            bath_days = '0,1,2,3,4,5',
            bath_days_am_only = '5',
            am_start = '09:30',
            am_end = '12:00',
            pm_start = '13:30',
            duration_min = 45,
            end_limit = '17:00',
            weekly_count = 2,
            min_interval_days = 3
        WHERE id = 1
    """)

    conn.commit() #ここまでの変更を確定してbath.dbに書き込む
    conn.close() #データベースへの接続を切ります。使い終わったら必ず閉じる、というルール

#↑ここまでinitialize関数


# ─── 設定 ───────────────────────────────────────────────

#id:1の行のデータを辞書型に変換するという一連の動作をおこない、関数呼びだし場所に返す関数
def get_settings():
    conn = get_connection()
    row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone() #excuteはsql文の実行
    conn.close()
    if row:
        return dict(row)
    return {}

#設定情報更新のための関数
def save_settings(data: dict):
    conn = get_connection()
    conn.execute("""
        UPDATE settings SET
            start_date = :start_date,
            bath_days = :bath_days,
            bath_days_am_only = :bath_days_am_only,
            am_start = :am_start,
            pm_start = :pm_start,
            duration_min = :duration_min,
            am_end = :am_end,
            end_limit = :end_limit,
            weekly_count = :weekly_count,
            min_interval_days = :min_interval_days
        WHERE id = 1
    """, data)
    conn.commit()
    conn.close()
    #プレイスホルダー:名前で対応（save_settingsのように列が多い時に便利）



# ─── 患者 ───────────────────────────────────────────────

#全入院中患者データを取得
def get_all_patients(active_only=True):
    conn = get_connection()
    query = "SELECT * FROM patients"
    if active_only:
        query += " WHERE is_active = 1" #sqlではpythonの変数をよめないので、PythonのTrueをSQL文の条件に翻訳
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows] #rowsの中のrそれぞれをdict(r)にしたリスト

#車いすと見守りをしないverの患者の追加
def add_patient(name, assist_type, wheelchair=False, monitoring=False):
    conn = get_connection()
    conn.execute("""
        INSERT INTO patients (name, assist_type, wheelchair, monitoring)
        VALUES (?, ?, ?, ?)
    """, (name, assist_type, int(wheelchair), int(monitoring)))
    conn.commit()
    conn.close()
    #プレイスホルダー?は順番で対応（add_patientのように引数が少ない時に便利）
    #この?に何を入れるかを、次の引数で指定(,の後の部分)

#患者を退院させる
def discharge_patient(patient_id):
    conn = get_connection()
    conn.execute(
        "UPDATE patients SET is_active = 0 WHERE id = ?", (patient_id,)
    )
    conn.commit()
    conn.close()
    #更新するpatinet_idの？には、(patient_id,)が入る



# ─── 予定 ───────────────────────────────────────────────

#指定した週の月曜〜日曜の予定を、患者情報と結合して取得する関数
def get_schedules_for_week(week_start: str):
    from datetime import date, timedelta  #週の開始日から終了日を計算するためにインポート
    start = date.fromisoformat(week_start) #文字列を日付方に変換し計算可能にする。日付から月曜日（週の開始日）を計算して開始日を設定
    end = start + timedelta(days=6) #週の終了日を計算
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.*, p.name, p.assist_type, p.wheelchair, p.monitoring
        FROM schedules s
        JOIN patients p ON s.patient_id = p.id
        WHERE s.date BETWEEN ? AND ?
        ORDER BY s.date, s.time_slot
    """, (str(start), str(end))).fetchall()
    #schedulesテーブル → s,patientsテーブル  → p
    #SELECTで「schedulesテーブルの全列」,「patientsテーブルから名前と介助情報」
    #WHERE s.date BETWEEN ? AND ? 日付がstartからendの範囲内の行だけを取得します。
    #ORDER BY s.date, s.time_slot 日付順、同じ日なら時間順に並べます。

    conn.close()
    return [dict(r) for r in rows]


#その週の通常予定を一度削除して、新しい予定を一括で入れ直す関数
def save_schedules_bulk(schedules: list):
    if not schedules:
        return
    week_dates = list({s["date"] for s in schedules}) #重複を削除することでその週に予定がある日付の一覧をだす
    conn = get_connection()
    for d in week_dates:
        conn.execute(
            "DELETE FROM schedules WHERE date = ? AND is_extra = 0", (d,)
        )
    conn.executemany("""
        INSERT INTO schedules (patient_id, date, time_slot, is_actual, is_extra, note)
        VALUES (:patient_id, :date, :time_slot, :is_actual, :is_extra, :note)
    """, schedules)
    conn.commit()
    conn.close()

#指定した患者の、指定した日より前の最終入浴日を取得する
def get_last_bath_date(patinet_id: int, before_date: str):
    conn = get_connection()
    row = conn.execute("""
        SELECT date FROM schedules
        WHERE patient_id = ? AND date < ?
        ORDER BY date DESC, time_slot DESC
        LIMIT 1
    """, (patinet_id, before_date)).fetchone()
    #patinet_id（指定患者）とbefore_date（指定した日付）のdateデータを選択
    #そのdataデータをtime_slot加味して降順（新しい順）に並び替え、
    #その中から、一番新しい１行のみを選択
    conn.close()
    return row["date"] if row else None


# ─── 履歴（Undo用） ──────────────────────────────────────

#週の開始日と週の予定をまるごと文字列に変換してschedule_historyテーブルに保存する関数
def save_history_snapshot(week_start: str, schedules: list):
    conn = get_connection()
    conn.execute("""
        INSERT INTO schedule_history (week_start, snapshot)
        VALUES (?, ?)
    """, (week_start, json.dumps(schedules, ensure_ascii=False)))
    #schedulesはPythonのリスト.json.dumps()はPythonのリストをJSON文字列に変換する
    #ensure_ascii=Falseは「日本語をそのまま保存する
    conn.commit()
    conn.close()

#chedule_historyテーブルに保存された履歴から、最新だけ取得する関数
def get_latest_history(week_start: str):
    conn = get_connection()
    row = conn.execute("""
        SELECT snapshot FROM schedule_history
        WHERE week_start = ?
        ORDER BY id DESC
        LIMIT 1
    """, (week_start,)).fetchone()
    conn.close()
    return json.loads(row["snapshot"]) if row else None
    # rowがあればjson.loads()を実行、なければNone




# ─── initialize関数実行 ──────────────────────────────────────

initialize_db()
#database.pyが読み込まれた瞬間に自動で実行される
#初回起動 → テーブルがない → テーブルを作成する
#2回目以降 → テーブルがある → IF NOT EXISTSでスキップ