"""Background processing pipeline for the API."""

import os
import shutil
import tempfile
import traceback

from .config import Config
from .downloader import download_audio
from .transcriber import create_transcriber
from .summarizer import Summarizer
from . import database as db


def _format_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


async def process_video(video_id: str, url: str, config: Config):
    """
    Background task that processes a video through the full pipeline.
    Updates the database at each step so the frontend can poll for status.
    """
    tmp_dir = tempfile.mkdtemp()

    try:
        # Step 1: Download
        await db.update_video_status(video_id, "downloading", "Downloading audio from YouTube...")
        audio_path, metadata = download_audio(url, tmp_dir)

        # Step 2: Update metadata
        await db.update_video_metadata(video_id, metadata)

        # Step 3: Transcribe
        duration_str = _format_duration(metadata.get("duration", 0))
        backend_names = {
            "groq": "Groq Whisper",
            "openai": "OpenAI Whisper",
            "local": "local whisper-server",
        }
        backend_name = backend_names.get(config.transcriber, config.transcriber)
        await db.update_video_status(
            video_id, "transcribing",
            f"Transcribing {duration_str} of audio via {backend_name}..."
        )

        transcriber = create_transcriber(config)
        transcript_text = transcriber.transcribe(audio_path)

        # Step 4: Save transcript
        await db.insert_transcript(video_id, transcript_text)

        # Step 5: Summarize
        provider_name = "Claude" if config.llm_provider == "anthropic" else "GPT"
        await db.update_video_status(
            video_id, "summarizing",
            f"Generating summaries via {provider_name} ({config.llm_model})..."
        )

        summarizer = Summarizer(config)
        summaries = summarizer.summarize(transcript_text, metadata)

        # Step 6: Save summaries
        await db.insert_summary(video_id, "detailed", summaries["detailed"])
        await db.insert_summary(video_id, "executive", summaries["executive"])

        # Step 7: Update search index
        await db.update_search_index(video_id)

        # Step 8: Mark completed
        await db.update_video_status(video_id, "completed")

    except Exception as e:
        error_msg = str(e)
        print(f"Pipeline error for video {video_id}: {error_msg}")
        traceback.print_exc()
        await db.update_video_error(video_id, error_msg)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
