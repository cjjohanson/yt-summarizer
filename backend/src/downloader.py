"""Download audio from YouTube videos using yt-dlp."""

import json
import os
import subprocess
import sys


def validate_youtube_url(url: str) -> bool:
    """Check if the URL looks like a valid YouTube URL."""
    valid_prefixes = [
        "https://www.youtube.com/watch?v=",
        "https://youtube.com/watch?v=",
        "https://m.youtube.com/watch?v=",
        "https://www.youtube.com/live/",
        "https://youtube.com/live/",
        "https://m.youtube.com/live/",
        "https://www.youtube.com/shorts/",
        "https://youtube.com/shorts/",
        "https://m.youtube.com/shorts/",
        "https://youtu.be/",
        "http://www.youtube.com/watch?v=",
        "http://youtube.com/watch?v=",
        "http://m.youtube.com/watch?v=",
        "http://www.youtube.com/live/",
        "http://youtube.com/live/",
        "http://m.youtube.com/live/",
        "http://www.youtube.com/shorts/",
        "http://youtube.com/shorts/",
        "http://m.youtube.com/shorts/",
        "http://youtu.be/",
    ]
    return any(url.startswith(p) for p in valid_prefixes)


def extract_video_id(url: str) -> str:
    """Extract the YouTube video ID from a URL."""
    if "youtu.be/" in url:
        path = url.split("youtu.be/")[1]
        return path.split("?")[0].split("&")[0]
    if "/live/" in url:
        path = url.split("/live/")[1]
        return path.split("?")[0].split("&")[0]
    if "/shorts/" in url:
        path = url.split("/shorts/")[1]
        return path.split("?")[0].split("&")[0]
    if "v=" in url:
        params = url.split("v=")[1]
        return params.split("&")[0]
    raise ValueError(f"Could not extract video ID from URL: {url}")


def download_audio(url: str, output_dir: str) -> tuple[str, dict]:
    """
    Download audio from a YouTube video as MP3.

    Returns:
        Tuple of (path_to_mp3_file, metadata_dict)
        metadata_dict contains: title, duration, channel, upload_date, video_id
    """
    if not validate_youtube_url(url):
        raise ValueError(
            f"Invalid YouTube URL: {url}\n"
            "  → Supported formats:\n"
            "    https://www.youtube.com/watch?v=VIDEO_ID\n"
            "    https://youtu.be/VIDEO_ID"
        )

    os.makedirs(output_dir, exist_ok=True)

    video_id = extract_video_id(url)
    output_template = os.path.join(output_dir, f"{video_id}.%(ext)s")

    # Download audio with yt-dlp as MP3 (~128kbps, keeps files small)
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "5",
        "-o", output_template,
        "--print-json",
        "--no-playlist",
        url,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
    except FileNotFoundError:
        raise RuntimeError(
            "yt-dlp is not installed.\n"
            "  → Install it with: pip install yt-dlp\n"
            "  → Or run inside the Docker container which has it pre-installed."
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip()
        if "Video unavailable" in stderr or "Private video" in stderr:
            raise RuntimeError(
                f"Could not download video: Video is unavailable.\n"
                f"  → Check that the URL is correct and the video is publicly accessible.\n"
                f"  → Private or age-restricted videos are not supported."
            )
        raise RuntimeError(
            f"yt-dlp failed:\n{stderr}\n"
            f"  → Check that the URL is correct and the video is publicly accessible."
        )

    # Parse metadata from yt-dlp JSON output
    try:
        info = json.loads(result.stdout.strip().split("\n")[-1])
    except (json.JSONDecodeError, IndexError):
        raise RuntimeError("Failed to parse yt-dlp metadata output.")

    metadata = {
        "title": info.get("title", "Unknown Title"),
        "duration": info.get("duration", 0),
        "channel": info.get("channel", info.get("uploader", "Unknown Channel")),
        "upload_date": info.get("upload_date", ""),
        "video_id": video_id,
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
    }

    # Format upload_date from YYYYMMDD to YYYY-MM-DD
    ud = metadata["upload_date"]
    if ud and len(ud) == 8:
        metadata["upload_date"] = f"{ud[:4]}-{ud[4:6]}-{ud[6:8]}"

    # Find the output file — yt-dlp may have created .mp3 directly or another format
    mp3_path = os.path.join(output_dir, f"{video_id}.mp3")
    if os.path.exists(mp3_path):
        return mp3_path, metadata

    # Look for any file with the video ID and convert to MP3
    for f in os.listdir(output_dir):
        if f.startswith(video_id) and not f.endswith(".mp3"):
            input_path = os.path.join(output_dir, f)
            mp3_path = os.path.join(output_dir, f"{video_id}.mp3")
            try:
                subprocess.run(
                    [
                        "ffmpeg", "-i", input_path,
                        "-codec:a", "libmp3lame",
                        "-b:a", "128k",
                        mp3_path,
                        "-y",
                    ],
                    capture_output=True, text=True, check=True,
                )
                os.remove(input_path)
                return mp3_path, metadata
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"ffmpeg conversion failed:\n{e.stderr}\n"
                    f"  → Make sure ffmpeg is installed."
                )

    raise RuntimeError(
        f"Could not find downloaded audio file for video {video_id} in {output_dir}"
    )
