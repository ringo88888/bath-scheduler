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

    c.execute("""
        CREATE TABLE IF NOT EXISTS schedule_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL,
            snapshot TEXT NOT NULL,
            saved_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    conn.commit() #ここまでの変更を確定してbath.dbに書き込む
    conn.close() #データベースへの接続を切ります。使い終わったら必ず閉じる、というルール

    #　↑ここまでinitialize関数