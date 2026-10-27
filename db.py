"""Долгосрочная память на SQLite.

Одна таблица на сущность (а не таблица на пользователя, как в уроке) —
так проще чистить и анализировать данные; пользователи различаются по user_id.
  history — последние реплики диалога (краткосрочный контекст, переживает рестарт)
  theses  — тезисы диалога (долгосрочная память)
"""
import os
import sqlite3
from contextlib import closing

DB_PATH = os.getenv("DB_PATH", "bot_database.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with closing(_conn()) as c, c:
        c.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS theses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            thesis TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("CREATE INDEX IF NOT EXISTS ix_history_user ON history(user_id, id)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_theses_user ON theses(user_id, id)")


def add_message(user_id: int, role: str, content: str):
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO history(user_id, role, content) VALUES (?,?,?)",
                  (user_id, role, content))


def get_recent_messages(user_id: int, limit: int) -> list[tuple[str, str]]:
    """Последние `limit` реплик в хронологическом порядке: [(role, content), ...]."""
    with closing(_conn()) as c:
        rows = c.execute(
            "SELECT role, content FROM history WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit)).fetchall()
    return rows[::-1]


def add_theses(user_id: int, theses: list[str]):
    existing = set(get_theses(user_id))
    new = []
    for t in theses:
        t = t.strip()
        if t and t not in existing and t not in new:
            new.append(t)
    if not new:
        return
    with closing(_conn()) as c, c:
        c.executemany("INSERT INTO theses(user_id, thesis) VALUES (?,?)",
                      [(user_id, t) for t in new])


def get_theses(user_id: int, limit: int | None = None) -> list[str]:
    """Тезисы пользователя; с `limit` — последние N (в хронологическом порядке)."""
    if limit:
        sql = ("SELECT thesis FROM (SELECT id, thesis FROM theses WHERE user_id=? "
               "ORDER BY id DESC LIMIT ?) ORDER BY id")
        args = (user_id, int(limit))
    else:
        sql = "SELECT thesis FROM theses WHERE user_id=? ORDER BY id"
        args = (user_id,)
    with closing(_conn()) as c:
        return [r[0] for r in c.execute(sql, args).fetchall()]


def clear_user(user_id: int) -> tuple[int, int]:
    """Полный сброс памяти пользователя. Возвращает (удалено реплик, удалено тезисов)."""
    with closing(_conn()) as c, c:
        h = c.execute("DELETE FROM history WHERE user_id=?", (user_id,)).rowcount
        t = c.execute("DELETE FROM theses WHERE user_id=?", (user_id,)).rowcount
    return h, t


def clear_history(user_id: int) -> int:
    """Сброс только краткосрочного контекста (тезисы остаются). Возвращает число удалённых реплик."""
    with closing(_conn()) as c, c:
        return c.execute("DELETE FROM history WHERE user_id=?", (user_id,)).rowcount


def stats() ->tuple[int, int, int]:
    """(пользователей, реплик, тезисов) — для лога при старте."""
    with closing(_conn()) as c:
        users = c.execute(
            "SELECT COUNT(*) FROM (SELECT user_id FROM history UNION SELECT user_id FROM theses)"
        ).fetchone()[0]
        h = c.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        t = c.execute("SELECT COUNT(*) FROM theses").fetchone()[0]
    return users, h, t
