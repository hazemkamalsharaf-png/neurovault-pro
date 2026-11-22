"""
db_manager.py — Database layer for NeuroVault Pro.

Provides a robust, context-managed SQLite interface with full-text search,
CRUD operations for code snippets, tags, and chat history.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

_CREATE_SNIPPETS = """
CREATE TABLE IF NOT EXISTS snippets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    language    TEXT    NOT NULL DEFAULT 'plaintext',
    content     TEXT    NOT NULL,
    summary     TEXT    DEFAULT '',
    created_at  TEXT    NOT NULL
);
"""

_CREATE_TAGS = """
CREATE TABLE IF NOT EXISTS tags (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    snippet_id INTEGER REFERENCES snippets(id) ON DELETE CASCADE,
    tag_name   TEXT    NOT NULL
);
"""

_CREATE_CHAT_HISTORY = """
CREATE TABLE IF NOT EXISTS chat_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role        TEXT    NOT NULL,       -- 'user' | 'assistant'
    content     TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL
);
"""


# ---------------------------------------------------------------------------
# DbManager — thread-safe SQLite wrapper with context-manager support
# ---------------------------------------------------------------------------

class DbManager:
    """Manages a single SQLite database file for NeuroVault Pro.

    Usage::

        db = DbManager("data/neurovault.db")
        with db.connect() as conn:
            conn.execute("SELECT …")
    """

    def __init__(self, db_path: str | Path = "data/neurovault.db"):
        self._db_path = Path(db_path)
        self._lock = threading.Lock()          # serialises writes
        self._ensure_parent_dir()

    # -- lifecycle ----------------------------------------------------------

    def _ensure_parent_dir(self) -> None:
        """Create the parent directory for the database file if needed."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Return a new connection with row-factory and pragmas enabled."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_schema(self) -> None:
        """Create all tables if they do not already exist."""
        with self.connect() as conn:
            conn.executescript(_CREATE_SNIPPETS)
            conn.executescript(_CREATE_TAGS)
            conn.executescript(_CREATE_CHAT_HISTORY)
            conn.commit()

    # -- snippets -----------------------------------------------------------

    def save_snippet(
        self,
        title: str,
        language: str,
        content: str,
        summary: str = "",
    ) -> int:
        """Insert a new snippet and return its id."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO snippets (title, language, content, summary, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (title, language, content, summary, now),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_snippet_summary(self, snippet_id: int, summary: str) -> None:
        """Update the generated summary for a snippet."""
        with self._lock, self.connect() as conn:
            conn.execute(
                "UPDATE snippets SET summary = ? WHERE id = ?",
                (summary, snippet_id),
            )
            conn.commit()

    def get_snippet(self, snippet_id: int) -> Optional[dict]:
        """Return a single snippet as a dict, or ``None``."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM snippets WHERE id = ?", (snippet_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_snippets(self) -> list[dict]:
        """Return every snippet ordered newest-first."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, title, language, summary, created_at "
                "FROM snippets ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_snippet(self, snippet_id: int) -> None:
        """Remove a snippet and its associated tags (CASCADE)."""
        with self._lock, self.connect() as conn:
            conn.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
            conn.commit()

    # -- full-text / keyword search -----------------------------------------

    def search_snippets(self, keywords: str) -> list[dict]:
        """Search *title*, *summary* and *content* using SQL LIKE.

        Supports multiple space-separated keywords — each one is matched
        independently (AND semantics).
        """
        terms = [t.strip() for t in keywords.split() if t.strip()]
        if not terms:
            return self.get_all_snippets()

        # Build a WHERE clause like:
        #   title LIKE '%foo%' AND summary LIKE '%bar%' OR content LIKE '%baz%'
        conditions: list[str] = []
        params: list[str] = []
        for term in terms:
            pattern = f"%{term}%"
            conditions.append(
                "(title LIKE ? OR summary LIKE ? OR content LIKE ?)"
            )
            params.extend([pattern, pattern, pattern])

        sql = (
            "SELECT id, title, language, summary, created_at "
            "FROM snippets WHERE " + " AND ".join(conditions)
            + " ORDER BY created_at DESC"
        )
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    # -- tags ---------------------------------------------------------------

    def get_tags_for_snippet(self, snippet_id: int) -> list[str]:
        """Return a deduplicated tag list for the given snippet."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT tag_name FROM tags WHERE snippet_id = ?",
                (snippet_id,),
            ).fetchall()
            return [r["tag_name"] for r in rows]

    def set_tags_for_snippet(self, snippet_id: int, tags: list[str]) -> None:
        """Replace all existing tags with the provided list."""
        with self._lock, self.connect() as conn:
            conn.execute(
                "DELETE FROM tags WHERE snippet_id = ?", (snippet_id,)
            )
            if tags:
                conn.executemany(
                    "INSERT INTO tags (snippet_id, tag_name) VALUES (?, ?)",
                    [(snippet_id, t) for t in tags],
                )
            conn.commit()

    # -- chat history -------------------------------------------------------

    def append_chat_message(self, role: str, content: str) -> None:
        """Persist a user or assistant message."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self.connect() as conn:
            conn.execute(
                "INSERT INTO chat_history (role, content, timestamp) VALUES (?, ?, ?)",
                (role, content, now),
            )
            conn.commit()

    def get_chat_history(self, limit: int = 50) -> list[dict]:
        """Return the most recent *limit* messages ordered chronologically."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM chat_history "
                "ORDER BY timestamp ASC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def clear_chat_history(self) -> None:
        """Remove all stored messages."""
        with self._lock, self.connect() as conn:
            conn.execute("DELETE FROM chat_history")
            conn.commit()
