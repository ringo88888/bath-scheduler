import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "bath.db"

def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn