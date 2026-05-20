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
                fetch_cycle TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                pair TEXT NOT NULL,
                bid REAL,
                ask REAL,
                mid REAL,
                source TEXT
            );
            CREATE TABLE IF NOT EXISTS bank_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fetch_cycle TEXT NOT NULL,
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

    def save_market_quotes_batch(self, fetch_cycle, quotes_dict, source):
        """保存一轮抓取的所有市场报价（同一 fetch_cycle）"""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        for pair, data in quotes_dict.items():
            conn.execute(
                "INSERT INTO market_quotes (fetch_cycle, timestamp, pair, bid, ask, mid, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (fetch_cycle, now, pair, data.get("bid"), data.get("ask"), data["mid"], source),
            )
        conn.commit()
        conn.close()

    def get_latest_cycle_quotes(self):
        """获取最新一轮抓取的所有报价"""
        conn = self._get_conn()
        cycle = conn.execute(
            "SELECT fetch_cycle FROM market_quotes ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not cycle:
            conn.close()
            return None
        rows = conn.execute(
            "SELECT pair, bid, ask, mid FROM market_quotes WHERE fetch_cycle = ?",
            (cycle[0],),
        ).fetchall()
        conn.close()
        return {row[0]: {"bid": row[1], "ask": row[2], "mid": row[3]} for row in rows}

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
