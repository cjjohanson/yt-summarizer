"""FastAPI application and route definitions."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import Config
from .downloader import extract_video_id, validate_youtube_url
from . import database as db
from .pipeline import process_video


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await db.init_db()
    yield


app = FastAPI(title="YouTube Video Summarizer", lifespan=lifespan)


# --- Request/Response models ---

class SubmitVideoRequest(BaseModel):
    url: str
    transcriber: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None


# --- API Routes ---

@app.post("/api/videos", status_code=202)
async def submit_video(req: SubmitVideoRequest, background_tasks: BackgroundTasks):
    """Submit a YouTube URL for processing."""
    if not validate_youtube_url(req.url):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_url",
                "message": "Not a valid YouTube URL.",
                "suggestion": "Use a URL like https://www.youtube.com/watch?v=VIDEO_ID",
            },
        )

    youtube_id = extract_video_id(req.url)

    # Check for existing video
    existing = await db.get_video_by_youtube_id(youtube_id)
    if existing:
        if existing["status"] == "completed":
            return existing
        if existing["status"] in ("pending", "downloading", "transcribing", "summarizing"):
            return existing
        if existing["status"] == "failed":
            await db.delete_video(existing["id"])

    # Build config with any overrides from the request
    overrides = {}
    if req.transcriber:
        overrides["transcriber"] = req.transcriber
    if req.llm_provider:
        overrides["llm_provider"] = req.llm_provider
    if req.llm_model:
        overrides["llm_model"] = req.llm_model

    config = Config(overrides)
    config.validate_for_api()

    # Create video record
    video = await db.create_video(
        youtube_id=youtube_id,
        youtube_url=req.url,
        transcriber=config.transcriber,
        llm_provider=config.llm_provider,
        llm_model=config.llm_model,
    )

    # Kick off background processing
    background_tasks.add_task(process_video, video["id"], req.url, config)

    return video


@app.get("/api/videos")
async def list_videos(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = None,
):
    """List all videos, optionally filtered by status or search query."""
    if q:
        results = await db.search_videos(q, limit=limit)
        return {"videos": results, "total": len(results), "limit": limit, "offset": 0, "query": q}

    videos, total = await db.list_videos(status=status, limit=limit, offset=offset)
    return {"videos": videos, "total": total, "limit": limit, "offset": offset}


@app.get("/api/videos/{video_id}")
async def get_video(video_id: str):
    """Get full details for a single video including transcript and summaries."""
    video = await db.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    transcript = await db.get_transcript(video_id)
    summaries = await db.get_summaries(video_id)

    result = dict(video)
    result["transcript"] = (
        {"content": transcript["content"], "word_count": transcript["word_count"]}
        if transcript
        else None
    )
    result["summaries"] = {}
    if "detailed" in summaries:
        result["summaries"]["detailed"] = {
            "content": summaries["detailed"]["content"],
            "word_count": summaries["detailed"]["word_count"],
        }
    if "executive" in summaries:
        result["summaries"]["executive"] = {
            "content": summaries["executive"]["content"],
            "word_count": summaries["executive"]["word_count"],
        }

    return result


@app.get("/api/videos/{video_id}/status")
async def get_video_status(video_id: str):
    """Lightweight status endpoint for polling."""
    video = await db.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        "id": video["id"],
        "status": video["status"],
        "progress_detail": video["progress_detail"],
        "title": video["title"],
        "error_message": video["error_message"],
    }


@app.delete("/api/videos/{video_id}", status_code=204)
async def delete_video(video_id: str):
    """Delete a video and all associated data."""
    video = await db.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    await db.delete_video(video_id)


@app.get("/api/search")
async def search(q: str = Query(..., min_length=1), limit: int = Query(default=20, ge=1, le=100)):
    """Full-text search across all video content."""
    results = await db.search_videos(q, limit=limit)
    return {"results": results, "total": len(results), "query": q}


# --- Static file serving for React frontend ---

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
# When running from /app, static files are at /app/static
if not os.path.isdir(STATIC_DIR):
    STATIC_DIR = "/app/static"

if os.path.isdir(STATIC_DIR):
    # Serve static assets (JS, CSS, images) if the assets dir exists
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React SPA for any non-API route."""
        # Try to serve a static file first
        file_path = os.path.join(STATIC_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fall back to index.html for client-side routing
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404)
