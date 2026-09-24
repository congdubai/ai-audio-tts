import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = Path(__file__).parent / "tts_history.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_history (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                speed REAL NOT NULL,
                duration REAL NOT NULL,
                phonemes TEXT,
                filename TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def add_history_entry(item_id: str, text: str, speed: float, duration: float, phonemes: str, filename: str, file_size: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audio_history (id, text, speed, duration, phonemes, filename, file_size, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, text, speed, duration, phonemes, filename, file_size, datetime.now().isoformat()))
        conn.commit()

def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, text, speed, duration, phonemes, filename, file_size, created_at
            FROM audio_history
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_history_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, text, speed, duration, phonemes, filename, file_size, created_at
            FROM audio_history
            WHERE id = ?
        """, (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_history_entry(item_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audio_history WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0
