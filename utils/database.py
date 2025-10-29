import aiosqlite
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import asyncio

DB_PATH = Path("data/moderation.db")

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS guild_settings (
  guild_id INTEGER PRIMARY KEY,
  prefix TEXT DEFAULT '!',
  mod_role_id INTEGER,
  admin_role_id INTEGER,
  mute_role_id INTEGER,
  log_channel_id INTEGER,
  mod_log_channel_id INTEGER,
  member_log_channel_id INTEGER,
  message_log_channel_id INTEGER,
  welcome_channel_id INTEGER,
  warn_threshold INTEGER DEFAULT 3,
  automod_enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS automod_settings (
  guild_id INTEGER PRIMARY KEY,
  spam_detection INTEGER DEFAULT 1,
  auto_delete_invites INTEGER DEFAULT 0,
  profanity_filter INTEGER DEFAULT 1,
  link_filter INTEGER DEFAULT 0,
  caps_filter INTEGER DEFAULT 1,
  repeated_text_filter INTEGER DEFAULT 1,
  auto_dehoist INTEGER DEFAULT 1,
  raid_protection INTEGER DEFAULT 1,
  max_mentions INTEGER DEFAULT 5,
  max_emoji INTEGER DEFAULT 10
);

CREATE TABLE IF NOT EXISTS warnings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  moderator_id INTEGER NOT NULL,
  reason TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_warnings_guild_user ON warnings(guild_id, user_id);

CREATE TABLE IF NOT EXISTS mod_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id INTEGER NOT NULL,
  action TEXT NOT NULL, -- ban, kick, mute, timeout, unban, unmute, purge
  target_id INTEGER NOT NULL,
  moderator_id INTEGER NOT NULL,
  reason TEXT,
  duration_seconds INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  extra JSON
);

CREATE INDEX IF NOT EXISTS idx_mod_actions_guild ON mod_actions(guild_id);
CREATE INDEX IF NOT EXISTS idx_mod_actions_target ON mod_actions(target_id);

"""

class Database:
    _instance = None

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._conn: Optional[aiosqlite.Connection] = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def connect(self):
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = await aiosqlite.connect(self.db_path.as_posix())
            await self._conn.executescript(SCHEMA_SQL)
            await self._conn.commit()
        return self._conn

    async def close(self):
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    # Guild settings
    async def get_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        conn = await self.connect()
        async with conn.execute("SELECT * FROM guild_settings WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            await conn.execute("INSERT INTO guild_settings(guild_id) VALUES (?)", (guild_id,))
            await conn.commit()
            async with conn.execute("SELECT * FROM guild_settings WHERE guild_id=?", (guild_id,)) as cur2:
                row = await cur2.fetchone()
        columns = [c[0] for c in cur.description] if 'cur' in locals() else [c[1] for c in await conn.execute("PRAGMA table_info(guild_settings)")]
        return {columns[i]: row[i] for i in range(len(row))}

    async def update_guild_settings(self, guild_id: int, **kwargs):
        if not kwargs:
            return
        conn = await self.connect()
        keys = ", ".join([f"{k}=?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [guild_id]
        await conn.execute(f"UPDATE guild_settings SET {keys} WHERE guild_id=?", values)
        await conn.commit()

    # AutoMod settings
    async def get_automod_settings(self, guild_id: int) -> Dict[str, Any]:
        conn = await self.connect()
        async with conn.execute("SELECT * FROM automod_settings WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            await conn.execute("INSERT INTO automod_settings(guild_id) VALUES (?)", (guild_id,))
            await conn.commit()
            async with conn.execute("SELECT * FROM automod_settings WHERE guild_id=?", (guild_id,)) as cur2:
                row = await cur2.fetchone()
        columns = [c[0] for c in cur.description]
        return {columns[i]: row[i] for i in range(len(row))}

    async def update_automod_settings(self, guild_id: int, **kwargs):
        if not kwargs:
            return
        conn = await self.connect()
        keys = ", ".join([f"{k}=?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [guild_id]
        await conn.execute(f"UPDATE automod_settings SET {keys} WHERE guild_id=?", values)
        await conn.commit()

    # Warnings
    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        conn = await self.connect()
        cur = await conn.execute(
            "INSERT INTO warnings(guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, reason)
        )
        await conn.commit()
        return cur.lastrowid

    async def get_warnings(self, guild_id: int, user_id: int) -> List[aiosqlite.Row]:
        conn = await self.connect()
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC",
            (guild_id, user_id)
        ) as cur:
            rows = await cur.fetchall()
        return rows

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        conn = await self.connect()
        cur = await conn.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        await conn.commit()
        return cur.rowcount

    # Moderation actions
    async def log_mod_action(
        self,
        guild_id: int,
        action: str,
        target_id: int,
        moderator_id: int,
        reason: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        extra: Optional[str] = None,
    ) -> int:
        conn = await self.connect()
        cur = await conn.execute(
            "INSERT INTO mod_actions(guild_id, action, target_id, moderator_id, reason, duration_seconds, extra) "
            "VALUES(?,?,?,?,?,?,?)",
            (guild_id, action, target_id, moderator_id, reason, duration_seconds, extra)
        )
        await conn.commit()
        return cur.lastrowid

    async def get_mod_actions(self, guild_id: int, target_id: Optional[int] = None, limit: int = 50) -> List[aiosqlite.Row]:
        conn = await self.connect()
        conn.row_factory = aiosqlite.Row
        if target_id is None:
            query = "SELECT * FROM mod_actions WHERE guild_id=? ORDER BY id DESC LIMIT ?"
            params = (guild_id, limit)
        else:
            query = "SELECT * FROM mod_actions WHERE guild_id=? AND target_id=? ORDER BY id DESC LIMIT ?"
            params = (guild_id, target_id, limit)
        async with conn.execute(query, params) as cur:
            rows = await cur.fetchall()
        return rows

DB = Database.get()
