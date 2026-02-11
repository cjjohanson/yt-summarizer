"""SQLite database models and queries with async support."""

import os
import uuid
from datetime import datetime

import aiosqlite

DB_PATH = os.getenv("DB_PATH", "/app/data/yt-summarizer.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    youtube_id TEXT NOT NULL UNIQUE,
    youtube_url TEXT NOT NULL,
    title TEXT,
    channel TEXT,
    duration_seconds INTEGER,
    upload_date TEXT,
    thumbnail_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    progress_detail TEXT,
    transcriber_used TEXT,
    llm_provider_used TEXT,
    llm_model_used TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    word_count INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS summaries (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    summary_type TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    UNIQUE(video_id, summary_type)
);

CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    video_id,
    title,
    channel,
    transcript_content,
    detailed_summary,
    executive_summary,
    content='',
    tokenize='porter unicode61'
);

CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
"""


async def get_db() -> aiosqlite.Connection:
    """Get a database connection with WAL mode and foreign keys enabled."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """Initialize the database schema."""
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
    finally:
        await db.close()


async def create_video(youtube_id: str, youtube_url: str, transcriber: str = None, llm_provider: str = None, llm_model: str = None) -> dict:
    """Create a new video record. Returns the video dict."""
    video_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO videos (id, youtube_id, youtube_url, transcriber_used, llm_provider_used, llm_model_used)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (video_id, youtube_id, youtube_url, transcriber, llm_provider, llm_model),
        )
        await db.commit()
        return await get_video(video_id, db=db)
    finally:
        await db.close()


async def get_video(video_id: str, db: aiosqlite.Connection = None) -> dict | None:
    """Get a video by its internal UUID."""
    should_close = db is None
    if db is None:
        db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        if should_close:
            await db.close()


async def get_video_by_youtube_id(youtube_id: str) -> dict | None:
    """Get a video by its YouTube video ID."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM videos WHERE youtube_id = ?", (youtube_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def list_videos(status: str = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    """List videos ordered by created_at desc. Returns (videos, total_count)."""
    db = await get_db()
    try:
        if status:
            count_cursor = await db.execute("SELECT COUNT(*) FROM videos WHERE status = ?", (status,))
            total = (await count_cursor.fetchone())[0]
            cursor = await db.execute(
                "SELECT * FROM videos WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            )
        else:
            count_cursor = await db.execute("SELECT COUNT(*) FROM videos")
            total = (await count_cursor.fetchone())[0]
            cursor = await db.execute(
                "SELECT * FROM videos ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows], total
    finally:
        await db.close()


async def update_video_status(video_id: str, status: str, progress_detail: str = None):
    """Update a video's processing status."""
    db = await get_db()
    try:
        now = datetime.utcnow().isoformat()
        if status == "completed":
            await db.execute(
                """UPDATE videos SET status = ?, progress_detail = ?, completed_at = ?, updated_at = ?
                   WHERE id = ?""",
                (status, progress_detail, now, now, video_id),
            )
        else:
            await db.execute(
                """UPDATE videos SET status = ?, progress_detail = ?, updated_at = ?
                   WHERE id = ?""",
                (status, progress_detail, now, video_id),
            )
        await db.commit()
    finally:
        await db.close()


async def update_video_metadata(video_id: str, metadata: dict):
    """Update a video record with metadata from yt-dlp."""
    db = await get_db()
    try:
        await db.execute(
            """UPDATE videos SET title = ?, channel = ?, duration_seconds = ?,
               upload_date = ?, thumbnail_url = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (
                metadata.get("title"),
                metadata.get("channel"),
                metadata.get("duration"),
                metadata.get("upload_date"),
                metadata.get("thumbnail_url"),
                video_id,
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def update_video_error(video_id: str, error_message: str):
    """Mark a video as failed with an error message."""
    db = await get_db()
    try:
        await db.execute(
            """UPDATE videos SET status = 'failed', error_message = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (error_message, video_id),
        )
        await db.commit()
    finally:
        await db.close()


async def insert_transcript(video_id: str, content: str):
    """Insert a transcript for a video."""
    db = await get_db()
    try:
        transcript_id = str(uuid.uuid4())
        word_count = len(content.split())
        await db.execute(
            "INSERT INTO transcripts (id, video_id, content, word_count) VALUES (?, ?, ?, ?)",
            (transcript_id, video_id, content, word_count),
        )
        await db.commit()
    finally:
        await db.close()


async def get_transcript(video_id: str) -> dict | None:
    """Get the transcript for a video."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM transcripts WHERE video_id = ?", (video_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def insert_summary(video_id: str, summary_type: str, content: str):
    """Insert a summary for a video."""
    db = await get_db()
    try:
        summary_id = str(uuid.uuid4())
        word_count = len(content.split())
        await db.execute(
            "INSERT INTO summaries (id, video_id, summary_type, content, word_count) VALUES (?, ?, ?, ?, ?)",
            (summary_id, video_id, summary_type, content, word_count),
        )
        await db.commit()
    finally:
        await db.close()


async def get_summaries(video_id: str) -> dict:
    """Get summaries for a video. Returns dict with 'detailed' and 'executive' keys."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM summaries WHERE video_id = ?", (video_id,))
        rows = await cursor.fetchall()
        result = {}
        for row in rows:
            row_dict = dict(row)
            result[row_dict["summary_type"]] = row_dict
        return result
    finally:
        await db.close()


async def delete_video(video_id: str):
    """Delete a video and all associated data (cascading)."""
    db = await get_db()
    try:
        # Delete from FTS index first
        await db.execute("DELETE FROM search_index WHERE video_id = ?", (video_id,))
        await db.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        await db.commit()
    finally:
        await db.close()


async def update_search_index(video_id: str):
    """Update the FTS search index for a video."""
    db = await get_db()
    try:
        # Get video info
        video = await get_video(video_id, db=db)
        if not video:
            return

        # Get transcript
        t_cursor = await db.execute("SELECT content FROM transcripts WHERE video_id = ?", (video_id,))
        t_row = await t_cursor.fetchone()
        transcript_content = t_row["content"] if t_row else ""

        # Get summaries
        s_cursor = await db.execute("SELECT summary_type, content FROM summaries WHERE video_id = ?", (video_id,))
        s_rows = await s_cursor.fetchall()
        detailed = ""
        executive = ""
        for row in s_rows:
            if row["summary_type"] == "detailed":
                detailed = row["content"]
            elif row["summary_type"] == "executive":
                executive = row["content"]

        # Remove existing index entry
        await db.execute("DELETE FROM search_index WHERE video_id = ?", (video_id,))

        # Insert new index entry
        await db.execute(
            "INSERT INTO search_index (video_id, title, channel, transcript_content, detailed_summary, executive_summary) VALUES (?, ?, ?, ?, ?, ?)",
            (video_id, video.get("title", ""), video.get("channel", ""), transcript_content, detailed, executive),
        )
        await db.commit()
    finally:
        await db.close()


async def search_videos(query: str, limit: int = 20) -> list[dict]:
    """Full-text search across videos, transcripts, and summaries."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT search_index.video_id,
                      snippet(search_index, 3, '<mark>', '</mark>', '...', 40) as snippet,
                      v.youtube_id, v.title, v.channel, v.thumbnail_url, v.status
               FROM search_index
               JOIN videos v ON v.id = search_index.video_id
               WHERE search_index MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (query, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()
