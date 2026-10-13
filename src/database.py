"""
Database Service for StudyMate AI
Handles local SQLite persistence for study sessions, notes, quizzes, and chat history.
"""

import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

def get_db_path(custom_path: Optional[str] = None) -> str:
    """Return database path and ensure target directory exists."""
    path = custom_path or os.getenv("DATABASE_PATH", os.path.join("data", "studymate.db"))
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    return path


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create a SQLite database connection with row factory enabled."""
    resolved_path = get_db_path(db_path)
    conn = sqlite3.connect(resolved_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize SQLite database schema if not already present.
    Creates the study_history table with appropriate indexes.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_type TEXT NOT NULL,
                title TEXT NOT NULL,
                input_excerpt TEXT,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_type
            ON study_history(session_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_created
            ON study_history(created_at DESC)
        """)
        conn.commit()


def add_history_entry(
    session_type: str,
    title: str,
    content: str,
    input_excerpt: Optional[str] = None,
    metadata: Optional[str] = "{}",
    db_path: Optional[str] = None,
) -> int:
    """
    Insert a new study session record.
    Uses parameterized SQL to prevent SQL injection.
    """
    init_db(db_path)
    # Truncate input excerpt if excessively long to keep database compact
    truncated_input = (input_excerpt[:500] + "...") if input_excerpt and len(input_excerpt) > 500 else (input_excerpt or "")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO study_history (session_type, title, input_excerpt, content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_type,
                title.strip(),
                truncated_input.strip(),
                content.strip(),
                metadata or "{}",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_history(
    search_query: str = "",
    session_type: str = "All",
    limit: int = 50,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve study history entries with optional full-text search and type filtering.
    """
    init_db(db_path)
    query = "SELECT id, session_type, title, input_excerpt, content, metadata, created_at FROM study_history WHERE 1=1"
    params: List[Any] = []

    if session_type and session_type != "All":
        query += " AND session_type = ?"
        params.append(session_type)

    if search_query.strip():
        search_pattern = f"%{search_query.strip()}%"
        query += " AND (title LIKE ? OR input_excerpt LIKE ? OR content LIKE ?)"
        params.extend([search_pattern, search_pattern, search_pattern])

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_history_by_id(entry_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single history entry by primary key ID."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, session_type, title, input_excerpt, content, metadata, created_at FROM study_history WHERE id = ?",
            (entry_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_history_entry(entry_id: int, db_path: Optional[str] = None) -> bool:
    """Delete an individual history record by ID."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM study_history WHERE id = ?", (entry_id,))
        conn.commit()
        return cursor.rowcount > 0


def clear_all_history(db_path: Optional[str] = None) -> bool:
    """Clear all records from study_history table."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM study_history")
        conn.commit()
        return True


def get_history_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Return genuine aggregated statistics from SQLite database.
    Does not invent fake activity numbers.
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM study_history")
        total_sessions = cursor.fetchone()[0]

        cursor.execute("""
            SELECT session_type, COUNT(*) as count
            FROM study_history
            GROUP BY session_type
        """)
        type_counts = {row["session_type"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("SELECT MAX(created_at) FROM study_history")
        last_active = cursor.fetchone()[0]

    return {
        "total_sessions": total_sessions,
        "type_counts": type_counts,
        "last_active": last_active,
    }
