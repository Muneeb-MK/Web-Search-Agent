import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "app.db")

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Get sqlite connection and ensure table schema exists."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DB_PATH):
    """Initialize database tables."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Threads table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS threads (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL CHECK(status IN ('clarifying', 'active'))
    )
    """)
    
    # Messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
        content TEXT NOT NULL,
        sources TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
    )
    """)
    
    # Pending clarifications table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_clarifications (
        thread_id TEXT PRIMARY KEY,
        original_question TEXT NOT NULL,
        questions TEXT NOT NULL,
        answers TEXT NOT NULL,
        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

# --- Thread CRUD ---

def create_thread(title: str, status: str = "clarifying", thread_id: Optional[str] = None, db_path: str = DB_PATH) -> str:
    """Create a new thread and return its ID."""
    if not thread_id:
        thread_id = str(uuid.uuid4())
    
    # Truncate title for neatness
    display_title = title if len(title) <= 50 else title[:47] + "..."
    
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO threads (id, title, status, created_at) VALUES (?, ?, ?, ?)",
        (thread_id, display_title, status, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return thread_id

def get_thread(thread_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve thread details by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM threads WHERE id = ?", (thread_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_all_threads(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Fetch all threads ordered by newest first."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM threads ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_thread_status(thread_id: str, status: str, db_path: str = DB_PATH):
    """Update thread status ('clarifying' or 'active')."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE threads SET status = ? WHERE id = ?", (status, thread_id))
    conn.commit()
    conn.close()

def delete_thread(thread_id: str, db_path: str = DB_PATH):
    """Delete thread and all associated messages and pending clarifications."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
    cursor.execute("DELETE FROM pending_clarifications WHERE thread_id = ?", (thread_id,))
    cursor.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
    conn.commit()
    conn.close()

# --- Message CRUD ---

def add_message(thread_id: str, role: str, content: str, sources: Optional[List[Dict[str, str]]] = None, db_path: str = DB_PATH) -> int:
    """Insert a new message into a thread."""
    sources_json = json.dumps(sources) if sources is not None else None
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (thread_id, role, content, sources, created_at) VALUES (?, ?, ?, ?, ?)",
        (thread_id, role, content, sources_json, datetime.utcnow().isoformat())
    )
    msg_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return msg_id

def get_thread_messages(thread_id: str, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Fetch all messages for a thread in chronological order."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE thread_id = ? ORDER BY id ASC", (thread_id,))
    rows = cursor.fetchall()
    conn.close()
    
    messages = []
    for r in rows:
        m = dict(r)
        if m.get("sources"):
            try:
                m["sources"] = json.loads(m["sources"])
            except Exception:
                m["sources"] = None
        else:
            m["sources"] = None
        messages.append(m)
    return messages

# --- Pending Clarifications CRUD ---

def save_pending_clarifications(
    thread_id: str, 
    original_question: str, 
    questions: List[str], 
    answers: Optional[List[str]] = None, 
    db_path: str = DB_PATH
):
    """Save or update pending clarification questions/answers for a thread."""
    if answers is None:
        answers = [""] * len(questions)
    
    questions_json = json.dumps(questions)
    answers_json = json.dumps(answers)
    
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO pending_clarifications (thread_id, original_question, questions, answers)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(thread_id) DO UPDATE SET
        original_question = excluded.original_question,
        questions = excluded.questions,
        answers = excluded.answers
    """, (thread_id, original_question, questions_json, answers_json))
    conn.commit()
    conn.close()

def get_pending_clarifications(thread_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve pending clarification record for a thread."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pending_clarifications WHERE thread_id = ?", (thread_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(row)
        data["questions"] = json.loads(data["questions"])
        data["answers"] = json.loads(data["answers"])
        return data
    return None

def delete_pending_clarifications(thread_id: str, db_path: str = DB_PATH):
    """Delete pending clarification record once submitted."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_clarifications WHERE thread_id = ?", (thread_id,))
    conn.commit()
    conn.close()
