import sqlite3
from datetime import datetime
from config import DB_PATH


class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_tables()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS market_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pair TEXT NOT NULL,
                bid REAL,
                ask REAL,
                mid REAL,
                source TEXT
            );
            CREATE TABLE IF NOT EXISTS bank_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                bank TEXT NOT NULL,
                pair TEXT NOT NULL,
                bid REAL,
                ask REAL
            );
            CREATE TABLE IF NOT EXISTS user_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pair TEXT NOT NULL,
                bank TEXT NOT NULL,
                direction TEXT NOT NULL,
                user_quote REAL,
                market_cost REAL,
                bank_cost REAL,
                bp_vs_market REAL,
                bp_vs_bank REAL
            );
        """)
        conn.commit()
        conn.close()

    def save_market_quote(self, pair, bid, ask, mid, source):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO market_quotes (timestamp, pair, bid, ask, mid, source) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), pair, bid, ask, mid, source),
        )
        conn.commit()
        conn.close()

    def get_latest_market_quote(self, pair):
        conn = self._get_conn()
        row = conn.execute(
            "SELECT bid, ask, mid FROM market_quotes WHERE pair = ? ORDER BY id DESC LIMIT 1",
            (pair,),
        ).fetchone()
        conn.close()
        return row

    def get_recent_market_quotes(self, pair, limit=100):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT timestamp, bid, ask, mid FROM market_quotes WHERE pair = ? ORDER BY id DESC LIMIT ?",
            (pair, limit),
        ).fetchall()
        conn.close()
        return list(reversed(rows))

    def save_user_entry(self, pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO user_entries (timestamp, pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank),
        )
        conn.commit()
        conn.close()

    def get_recent_user_entries(self, limit=20):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT timestamp, pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank FROM user_entries ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return list(reversed(rows))
