"""Markdown file output generation."""

import os
import re
from datetime import date


def _sanitize_dirname(title: str, video_id: str = "") -> str:
    """Convert a video title to a filesystem-safe directory name."""
    name = title.lower()
    name = name.replace(" ", "-")
    name = re.sub(r"[^a-z0-9\-_]", "", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-")
    name = name[:80]
    if not name:
        name = video_id or "untitled"
    return name


def _format_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def save_output(
    metadata: dict,
    transcript: str,
    summaries: dict | None,
    output_dir: str,
    transcriber_name: str,
    llm_model: str = "",
) -> dict:
    """
    Save transcript and summaries as markdown files.

    Returns dict with keys: dir, transcript, detailed_summary, executive_summary
    """
    title = metadata.get("title", "Unknown Title")
    video_id = metadata.get("video_id", "")
    url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
    channel = metadata.get("channel", "Unknown")
    duration = _format_duration(metadata.get("duration", 0))
    upload_date = metadata.get("upload_date", "Unknown")
    today = date.today().isoformat()

    # Create output directory
    dirname = _sanitize_dirname(title, video_id)
    dir_path = os.path.join(output_dir, dirname)

    # Handle existing directory by appending video ID
    if os.path.exists(dir_path):
        dirname = f"{dirname}-{video_id}"
        dir_path = os.path.join(output_dir, dirname)

    os.makedirs(dir_path, exist_ok=True)

    paths = {"dir": dir_path}

    # Write transcript
    transcript_path = os.path.join(dir_path, "transcript.md")
    with open(transcript_path, "w") as f:
        f.write(f"# {title}\n\n")
        f.write(f"**Source:** {url}\n")
        f.write(f"**Channel:** {channel}\n")
        f.write(f"**Duration:** {duration}\n")
        f.write(f"**Upload Date:** {upload_date}\n")
        f.write(f"**Transcribed:** {today}\n")
        f.write(f"**Transcription Method:** {transcriber_name}\n\n")
        f.write("---\n\n")
        f.write(transcript)
    paths["transcript"] = transcript_path

    # Write summaries if provided
    if summaries:
        if summaries.get("detailed"):
            detailed_path = os.path.join(dir_path, "detailed-summary.md")
            with open(detailed_path, "w") as f:
                f.write(f"# {title} — Detailed Summary\n\n")
                f.write(f"**Source:** {url}\n")
                f.write(f"**Channel:** {channel}\n")
                f.write(f"**Duration:** {duration}\n")
                f.write(f"**Summarized:** {today}\n")
                f.write(f"**Model:** {llm_model}\n\n")
                f.write("---\n\n")
                f.write(summaries["detailed"])
            paths["detailed_summary"] = detailed_path

        if summaries.get("executive"):
            executive_path = os.path.join(dir_path, "executive-summary.md")
            with open(executive_path, "w") as f:
                f.write(f"# {title} — Executive Summary\n\n")
                f.write(f"**Source:** {url}\n")
                f.write(f"**Channel:** {channel}\n")
                f.write(f"**Duration:** {duration}\n")
                f.write(f"**Summarized:** {today}\n")
                f.write(f"**Model:** {llm_model}\n\n")
                f.write("---\n\n")
                f.write(summaries["executive"])
            paths["executive_summary"] = executive_path

    return paths
