import sqlite3
from typing import Any, Dict, List
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path: str = 'poker.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS buyins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player TEXT NOT NULL,
            amount REAL NOT NULL,
            timestamp TEXT NOT NULL,
            session_id TEXT,
            ref TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            notes TEXT
        )
        ''')
        c.execute('''
        CREATE TABLE IF NOT EXISTS payouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            winner TEXT NOT NULL,
            amount REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
        ''')
        self.conn.commit()

    def add_buyin(self, record: Dict[str, Any]) -> None:
        session = record.get('session_id') or record['datetime'].date().isoformat()
        c = self.conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO buyins (player, amount, timestamp, session_id, ref)
            VALUES (?, ?, ?, ?, ?)
        ''', (record['sender'], record['amount'], record['datetime'].isoformat(), session, record.get('ref')))
        self.conn.commit()

    def add_manual_buyin(self, player: str, amount: float, dt: datetime, notes: str = None) -> None:
        session = dt.date().isoformat()
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO buyins (player, amount, timestamp, session_id, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (player, amount, dt.isoformat(), session, notes))
        self.conn.commit()

    def list_sessions(self) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT session_id, COUNT(*), SUM(amount) FROM buyins GROUP BY session_id")
        rows = c.fetchall()
        return [{'session_id': row[0], 'count': row[1], 'total': row[2]} for row in rows]

    def get_buyins(self, session_id: str = None) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        if session_id:
            c.execute("SELECT id, player, amount, timestamp, status, notes FROM buyins WHERE session_id = ?", (session_id,))
        else:
            c.execute("SELECT id, player, amount, timestamp, status, notes FROM buyins")
        cols = [description[0] for description in c.description]
        rows = c.fetchall()
        return [dict(zip(cols, row)) for row in rows]

    def delete_buyin(self, buyin_id: int) -> None:
        c = self.conn.cursor()
        c.execute("DELETE FROM buyins WHERE id = ?", (buyin_id,))
        self.conn.commit()

    def update_buyin(self, buyin_id: int, player: str, amount: float, status: str = 'confirmed') -> None:
        c = self.conn.cursor()
        c.execute("UPDATE buyins SET player = ?, amount = ?, status = ? WHERE id = ?", (player, amount, status, buyin_id))
        self.conn.commit()

    def add_payout(self, session_id: str, winner: str, amount: float) -> None:
        timestamp = datetime.now().isoformat()
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO payouts (session_id, winner, amount, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (session_id, winner, amount, timestamp))
        self.conn.commit()

    def get_payouts(self, session_id: str) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute('SELECT id, winner, amount, timestamp FROM payouts WHERE session_id = ?', (session_id,))
        cols = [description[0] for description in c.description]
        rows = c.fetchall()
        return [dict(zip(cols, row)) for row in rows]
