"""Transcription backends — Groq Whisper API, OpenAI Whisper API, and local whisper-server."""

import math
import os
import subprocess
import tempfile

import requests


MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".webm": "audio/webm",
    ".flac": "audio/flac",
}


def _get_mime_type(audio_path: str) -> str:
    """Detect MIME type from file extension."""
    ext = os.path.splitext(audio_path)[1].lower()
    return MIME_TYPES.get(ext, "audio/mpeg")


def _parse_duration(ffmpeg_output: str) -> float:
    """Parse duration in seconds from ffmpeg stderr output."""
    for line in ffmpeg_output.split("\n"):
        if "Duration:" in line:
            time_str = line.split("Duration:")[1].split(",")[0].strip()
            parts = time_str.split(":")
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
    return 0


def _split_audio(audio_path: str, chunk_duration: int) -> list[str]:
    """Split audio into MP3 chunks using ffmpeg."""
    result = subprocess.run(
        ["ffmpeg", "-i", audio_path, "-f", "null", "-"],
        capture_output=True, text=True,
    )
    duration = _parse_duration(result.stderr)
    if duration <= 0:
        raise RuntimeError("Could not determine audio duration for chunking.")

    num_chunks = math.ceil(duration / chunk_duration)
    chunk_dir = tempfile.mkdtemp()
    chunks = []

    for i in range(num_chunks):
        start = i * chunk_duration
        chunk_path = os.path.join(chunk_dir, f"chunk_{i:03d}.mp3")
        subprocess.run(
            [
                "ffmpeg", "-i", audio_path,
                "-ss", str(start),
                "-t", str(chunk_duration),
                "-codec:a", "libmp3lame", "-b:a", "128k",
                chunk_path, "-y",
            ],
            capture_output=True, text=True, check=True,
        )
        chunks.append(chunk_path)

    return chunks


class BaseTranscriber:
    def transcribe(self, audio_path: str) -> str:
        """Takes a path to an audio file. Returns the full transcript as plain text."""
        raise NotImplementedError


class GroqWhisperTranscriber(BaseTranscriber):
    """Transcribe via Groq's OpenAI-compatible Whisper API (default)."""

    MAX_FILE_SIZE = 90 * 1024 * 1024  # 90 MB (safety margin under 100MB paid-tier limit)
    CHUNK_DURATION_SECONDS = 60 * 60  # 60-minute chunks

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Groq API key is required for Groq Whisper transcription.")
        self.api_key = api_key

    def transcribe(self, audio_path: str) -> str:
        file_size = os.path.getsize(audio_path)

        if file_size <= self.MAX_FILE_SIZE:
            return self._transcribe_file(audio_path)

        # Split into chunks and transcribe each
        chunks = _split_audio(audio_path, self.CHUNK_DURATION_SECONDS)
        try:
            transcripts = []
            for i, chunk_path in enumerate(chunks, 1):
                print(f"      Transcribing chunk {i}/{len(chunks)}...")
                transcripts.append(self._transcribe_file(chunk_path))
            return " ".join(transcripts)
        finally:
            for chunk_path in chunks:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)

    def _transcribe_file(self, audio_path: str) -> str:
        """Send a single audio file to the Groq Whisper API."""
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        mime_type = _get_mime_type(audio_path)

        with open(audio_path, "rb") as f:
            response = requests.post(
                url,
                headers=headers,
                files={"file": (os.path.basename(audio_path), f, mime_type)},
                data={
                    "model": "whisper-large-v3-turbo",
                    "response_format": "json",
                },
                timeout=600,
            )

        if response.status_code == 401:
            raise RuntimeError(
                "Groq API authentication failed.\n"
                "  → Check that your GROQ_API_KEY is valid."
            )
        if response.status_code == 429:
            raise RuntimeError(
                "Groq API rate limit exceeded.\n"
                "  → Wait a moment and try again."
            )
        if response.status_code == 413:
            raise RuntimeError(
                "Audio file is too large for Groq Whisper API.\n"
                "  → This should have been handled by automatic chunking. Please report this bug."
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"Groq Whisper API error ({response.status_code}):\n{response.text}"
            )

        return response.json().get("text", "")


class OpenAIWhisperTranscriber(BaseTranscriber):
    """Transcribe via OpenAI's Whisper API."""

    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
    CHUNK_DURATION_SECONDS = 20 * 60  # 20-minute chunks

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OpenAI API key is required for Whisper transcription.")
        self.api_key = api_key

    def transcribe(self, audio_path: str) -> str:
        file_size = os.path.getsize(audio_path)

        if file_size <= self.MAX_FILE_SIZE:
            return self._transcribe_file(audio_path)

        # Split into chunks and transcribe each
        chunks = _split_audio(audio_path, self.CHUNK_DURATION_SECONDS)
        try:
            transcripts = []
            for i, chunk_path in enumerate(chunks, 1):
                print(f"      Transcribing chunk {i}/{len(chunks)}...")
                transcripts.append(self._transcribe_file(chunk_path))
            return " ".join(transcripts)
        finally:
            for chunk_path in chunks:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)

    def _transcribe_file(self, audio_path: str) -> str:
        """Send a single audio file to the OpenAI Whisper API."""
        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        mime_type = _get_mime_type(audio_path)

        with open(audio_path, "rb") as f:
            response = requests.post(
                url,
                headers=headers,
                files={"file": (os.path.basename(audio_path), f, mime_type)},
                data={"model": "whisper-1", "response_format": "json"},
                timeout=600,
            )

        if response.status_code == 401:
            raise RuntimeError(
                "OpenAI API authentication failed.\n"
                "  → Check that your OPENAI_API_KEY is valid."
            )
        if response.status_code == 429:
            raise RuntimeError(
                "OpenAI API rate limit exceeded.\n"
                "  → Wait a moment and try again."
            )
        if response.status_code == 413:
            raise RuntimeError(
                "Audio file is too large for OpenAI Whisper API (25MB limit).\n"
                "  → This should have been handled by automatic chunking. Please report this bug."
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"OpenAI Whisper API error ({response.status_code}):\n{response.text}"
            )

        return response.json().get("text", "")


class LocalWhisperTranscriber(BaseTranscriber):
    """Transcribe via a local whisper-server running on the host."""

    def __init__(self, server_url: str, timeout: int = 600):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout

    def transcribe(self, audio_path: str) -> str:
        url = f"{self.server_url}/inference"
        mime_type = _get_mime_type(audio_path)

        try:
            with open(audio_path, "rb") as f:
                response = requests.post(
                    url,
                    files={"file": (os.path.basename(audio_path), f, mime_type)},
                    data={
                        "temperature": "0.0",
                        "temperature_inc": "0.2",
                        "response_format": "json",
                    },
                    timeout=self.timeout,
                )
        except requests.ConnectionError:
            raise RuntimeError(
                f"Could not connect to whisper-server at {self.server_url}\n"
                f"  → Make sure whisper-server is running on the host machine.\n"
                f"  → See README for setup instructions.\n"
                f"  → Or use --transcriber groq to use Groq's Whisper API instead."
            )
        except requests.Timeout:
            raise RuntimeError(
                f"Whisper-server request timed out after {self.timeout}s.\n"
                f"  → Try increasing WHISPER_TIMEOUT for very long audio files.\n"
                f"  → Current timeout: {self.timeout} seconds."
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Whisper-server error ({response.status_code}):\n{response.text}"
            )

        data = response.json()
        return data.get("text", "")


def create_transcriber(config) -> BaseTranscriber:
    """Factory function to create the appropriate transcriber backend."""
    if config.transcriber == "groq":
        return GroqWhisperTranscriber(config.groq_api_key)
    elif config.transcriber == "openai":
        return OpenAIWhisperTranscriber(config.openai_api_key)
    elif config.transcriber == "local":
        return LocalWhisperTranscriber(
            config.whisper_server_url, config.whisper_timeout
        )
    else:
        raise ValueError(
            f"Unknown transcriber: {config.transcriber}\n"
            f"  → Supported values: groq, openai, local"
        )
