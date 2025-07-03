import sqlite3
from datetime import datetime

Row = sqlite3.Row

class DatabaseManager:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._ensure_tables()

    def _ensure_tables(self):
        # Create sessions table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT
            )
            """
        )
        # Create buyins table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS buyins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                player TEXT,
                amount REAL,
                timestamp TEXT,
                notes TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
            """
        )
        # Create payouts table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                winner TEXT,
                amount REAL,
                timestamp TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
            """
        )
        self.conn.commit()

    def create_session(self, session_id: str) -> str:
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT OR IGNORE INTO sessions (session_id, created_at) VALUES (?, ?)",
            (session_id, now)
        )
        self.conn.commit()
        return session_id

    def list_sessions(self) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT session_id, created_at FROM sessions ORDER BY created_at DESC"
        )
        return [dict(row) for row in cursor.fetchall()]

    def add_buyin(self, record: dict):
        """
        Adds a buy-in or stacks onto an existing one if the player already bought in this session.
        record keys: session_id, sender (player), amount, timestamp, notes
        """
        session_id = record.get('session_id')
        player = record.get('sender')
        amount = record.get('amount', 0.0)
        timestamp = record.get('timestamp', datetime.now().isoformat())
        notes = record.get('notes')

        # Check for existing buy-in for this player/session
        row = self.conn.execute(
            "SELECT id, amount FROM buyins WHERE session_id = ? AND player = ?",
            (session_id, player)
        ).fetchone()

        if row:
            new_amount = row['amount'] + amount
            self.conn.execute(
                "UPDATE buyins SET amount = ?, timestamp = ?, notes = ? WHERE id = ?",
                (new_amount, timestamp, notes, row['id'])
            )
        else:
            self.conn.execute(
                "INSERT INTO buyins (session_id, player, amount, timestamp, notes) VALUES (?, ?, ?, ?, ?)",
                (session_id, player, amount, timestamp, notes)
            )
        self.conn.commit()

    def add_manual_buyin(self, session_id: str, player: str, amount: float, dt: datetime, notes: str = None):
        # Wrap manual into same logic
        record = {
            'session_id': session_id,
            'sender': player,
            'amount': amount,
            'timestamp': dt.isoformat(),
            'notes': notes
        }
        self.add_buyin(record)

    def get_buyins(self, session_id: str) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT id, player, amount, timestamp, notes FROM buyins WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def update_buyin(self, buyin_id: int, player: str = None, amount: float = None) -> bool:
        row = self.conn.execute(
            "SELECT player, amount FROM buyins WHERE id = ?",
            (buyin_id,)
        ).fetchone()
        if not row:
            return False
        new_player = player if player is not None else row['player']
        new_amount = amount if amount is not None else row['amount']
        self.conn.execute(
            "UPDATE buyins SET player = ?, amount = ? WHERE id = ?",
            (new_player, new_amount, buyin_id)
        )
        self.conn.commit()
        return True

    def delete_buyin(self, buyin_id: int):
        self.conn.execute(
            "DELETE FROM buyins WHERE id = ?",
            (buyin_id,)
        )
        self.conn.commit()

    def add_payout(self, session_id: str, winner: str, amount: float):
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO payouts (session_id, winner, amount, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, winner, amount, now)
        )
        self.conn.commit()

    def get_payouts(self, session_id: str) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT id, winner, amount, timestamp FROM payouts WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    

