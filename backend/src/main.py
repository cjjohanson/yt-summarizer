"""CLI entrypoint for the YouTube Video Summarizer."""

import argparse
import os
import shutil
import sys
import tempfile

from .config import Config
from .downloader import download_audio, validate_youtube_url
from .transcriber import create_transcriber
from .summarizer import Summarizer
from .output import save_output


def _format_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def main():
    parser = argparse.ArgumentParser(
        description="Summarize a YouTube video: download, transcribe, and generate summaries."
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--transcriber", choices=["groq", "openai", "local"], default=None,
        help="Transcription backend (default: groq)"
    )
    parser.add_argument(
        "--llm", choices=["anthropic", "openai"], default=None,
        help="LLM provider for summarization (default: anthropic)"
    )
    parser.add_argument(
        "--model", default=None,
        help="LLM model override (e.g., claude-sonnet-4-20250514, gpt-4o)"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory for markdown files (default: /app/output)"
    )
    parser.add_argument(
        "--transcript-only", action="store_true",
        help="Only generate the transcript, skip summarization"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable detailed progress logging"
    )
    args = parser.parse_args()

    # Build config with CLI overrides
    overrides = {}
    if args.transcriber:
        overrides["transcriber"] = args.transcriber
    if args.llm:
        overrides["llm_provider"] = args.llm
    if args.model:
        overrides["llm_model"] = args.model
    if args.output_dir:
        overrides["output_dir"] = args.output_dir

    config = Config(overrides)
    config.validate()

    url = args.url
    if not validate_youtube_url(url):
        print(
            f"\nERROR: Invalid YouTube URL: {url}\n"
            f"  → Supported formats:\n"
            f"    https://www.youtube.com/watch?v=VIDEO_ID\n"
            f"    https://youtu.be/VIDEO_ID",
            file=sys.stderr,
        )
        sys.exit(1)

    tmp_dir = tempfile.mkdtemp()
    total_steps = 3 if args.transcript_only else 4

    try:
        # Step 1: Download
        step = 1
        print(f"\n[{step}/{total_steps}] Downloading audio from: {url}")
        audio_path, metadata = download_audio(url, tmp_dir)
        title = metadata.get("title", "Unknown")
        duration = _format_duration(metadata.get("duration", 0))
        print(f"      Title: \"{title}\"")
        print(f"      Duration: {duration}")

        # Step 2: Transcribe
        step = 2
        transcriber = create_transcriber(config)
        backend_names = {
            "groq": "Groq Whisper API",
            "openai": "OpenAI Whisper API",
            "local": "local whisper-server",
        }
        backend_name = backend_names.get(config.transcriber, config.transcriber)
        print(f"[{step}/{total_steps}] Transcribing audio via {backend_name}...")
        transcript = transcriber.transcribe(audio_path)

        # Step 3: Summarize (unless --transcript-only)
        summaries = None
        if not args.transcript_only:
            step = 3
            provider_name = "Anthropic Claude" if config.llm_provider == "anthropic" else "OpenAI GPT"
            print(f"[{step}/{total_steps}] Generating summaries via {provider_name}...")
            summarizer = Summarizer(config)
            summaries = summarizer.summarize(transcript, metadata)

        # Final step: Save output
        step = total_steps
        print(f"[{step}/{total_steps}] Saving output files...")
        paths = save_output(
            metadata=metadata,
            transcript=transcript,
            summaries=summaries,
            output_dir=config.output_dir,
            transcriber_name=config.transcriber,
            llm_model=config.llm_model,
        )

        # Print results
        print(f"      Transcript:        {paths['transcript']}")
        if "detailed_summary" in paths:
            print(f"      Detailed Summary:  {paths['detailed_summary']}")
        if "executive_summary" in paths:
            print(f"      Executive Summary: {paths['executive_summary']}")
        print("Done!\n")

    except (RuntimeError, ValueError) as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Clean up temp directory
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
