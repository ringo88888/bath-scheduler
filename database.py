import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "bath.db"

#dataフォルダ、bath.dbを作成してsqliteに接続する
def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

#connはデータベースへの接続回線、cursorは受話器
def initialize_db():
    conn = get_connection()
    c = conn.cursor() #ここでbath.dataとsqlitedatabaseの接続しました
    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (

        )
    """)

