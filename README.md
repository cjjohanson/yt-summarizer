# YT Summarizer

A containerized application that takes a YouTube video URL, transcribes the audio, and generates comprehensive summaries using an LLM. Get 80-90% of the value of a video in minutes instead of watching the whole thing.

Two interfaces:
- **Web UI** — paste a URL, browse your library of past summaries, search across all transcripts
- **CLI** — quick one-off summarization from the command line

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A [Groq API key](https://console.groq.com) (free, no credit card required)
- An [Anthropic API key](https://console.anthropic.com) for Claude summarization

### Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/yt-summarizer.git
cd yt-summarizer

# Create your .env file
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
GROQ_API_KEY=gsk_your_key_here
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

### Run the Web UI

```bash
docker compose up --build -d
```

Open **http://localhost:8000** in your browser. Paste a YouTube URL, pick a transcription backend, and click Summarize.

### Run via CLI

```bash
docker compose run cli "https://www.youtube.com/watch?v=VIDEO_ID"
```

Output files are saved to `./output/` as markdown.

## How It Works

```
YouTube URL
    │
    ▼
1. Download audio (yt-dlp → MP3)
    │
    ▼
2. Transcribe (Groq Whisper API, OpenAI Whisper API, or local whisper-server)
    │
    ▼
3. Summarize (Anthropic Claude or OpenAI GPT)
    │
    ▼
4. Two summaries:
   - Executive Summary — quick overview, key takeaways, who should watch
   - Detailed Summary — comprehensive breakdown of all topics, quotes, actionable items
```

Both the web UI and CLI share the same SQLite database, so videos summarized via CLI also appear in the web library.

## Configuration

### API Keys

| Variable | Required | How to Get |
|----------|----------|------------|
| `GROQ_API_KEY` | Yes (default transcriber) | [console.groq.com](https://console.groq.com) — free, no credit card |
| `ANTHROPIC_API_KEY` | Yes (default LLM) | [console.anthropic.com](https://console.anthropic.com) |
| `OPENAI_API_KEY` | Only if using OpenAI | [platform.openai.com](https://platform.openai.com) |

### Transcription Backends

| Backend | Flag / Dropdown | Cost | Speed | Setup |
|---------|----------------|------|-------|-------|
| **Groq** (default) | `--transcriber groq` | ~$0.04/hr | Very fast (216x realtime) | Just API key |
| OpenAI Whisper | `--transcriber openai` | ~$0.36/hr | Moderate | Just API key |
| Local whisper-server | `--transcriber local` | Free | Depends on GPU | See [Local Whisper Setup](#local-whisper-server-setup-optional) |

### LLM Providers

| Provider | Flag | Default Model |
|----------|------|---------------|
| **Anthropic** (default) | `--llm anthropic` | `claude-sonnet-5` |
| OpenAI | `--llm openai` | `gpt-4o` |

### All Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Groq API key for transcription |
| `ANTHROPIC_API_KEY` | — | Anthropic API key for summarization |
| `OPENAI_API_KEY` | — | OpenAI API key (optional) |
| `TRANSCRIBER` | `groq` | Transcription backend: `groq`, `openai`, or `local` |
| `LLM_PROVIDER` | `anthropic` | LLM provider: `anthropic` or `openai` |
| `LLM_MODEL` | Provider default | Override the LLM model |
| `WHISPER_SERVER_URL` | `http://host.docker.internal:8080` | Local whisper-server URL |
| `WHISPER_TIMEOUT` | `600` | Timeout in seconds for local whisper-server |

## CLI Options

```
docker compose run cli [OPTIONS] URL
```

| Option | Description |
|--------|-------------|
| `URL` | YouTube video URL (required) |
| `--transcriber {groq,openai,local}` | Transcription backend (default: groq) |
| `--llm {anthropic,openai}` | LLM provider (default: anthropic) |
| `--model MODEL` | Override LLM model (e.g., `gpt-4o`) |
| `--output-dir DIR` | Output directory (default: `/app/output`) |
| `--transcript-only` | Only transcribe, skip summarization |
| `--verbose` | Detailed progress logging |

### Examples

```bash
# Default: Groq transcription + Claude summarization
docker compose run cli "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Use OpenAI for everything
docker compose run cli --transcriber openai --llm openai "https://youtu.be/dQw4w9WgXcQ"

# Just get the transcript, no summary
docker compose run cli --transcript-only "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Use local whisper-server (must be running on host)
docker compose run cli --transcriber local "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## Web UI

The web interface runs at **http://localhost:8000** and provides:

- **Home** — paste a URL, choose transcription backend, submit
- **Processing** — live progress as the video is downloaded, transcribed, and summarized
- **Video Detail** — view executive summary, detailed summary, and full transcript in tabs
- **Library** — browse and search all past summaries

### Managing the App

```bash
# Start in background
docker compose up --build -d

# View logs
docker compose logs -f

# Stop
docker compose down

# Rebuild after code changes
docker compose up --build -d
```

## Project Structure

```
yt-summarizer/
├── Dockerfile              # Multi-stage build (Node + Python)
├── docker-compose.yml      # Web UI + CLI services
├── .env.example            # Template for API keys
│
├── backend/
│   ├── requirements.txt
│   ├── src/
│   │   ├── api.py          # FastAPI routes + static file serving
│   │   ├── config.py       # Environment variable handling
│   │   ├── database.py     # SQLite with FTS5 search
│   │   ├── downloader.py   # yt-dlp audio extraction
│   │   ├── main.py         # CLI entrypoint
│   │   ├── output.py       # Markdown file generation
│   │   ├── pipeline.py     # Background processing pipeline
│   │   ├── summarizer.py   # LLM summarization (Claude/GPT)
│   │   └── transcriber.py  # Transcription (Groq/OpenAI/local)
│   └── prompts/
│       ├── detailed_summary.txt
│       └── executive_summary.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js          # Backend API client
│   │   ├── pages/          # HomePage, VideoPage, LibraryPage, ProcessingPage
│   │   └── components/     # UrlInput, VideoCard, SummaryView, etc.
│   └── package.json
│
├── data/                   # SQLite database (Docker volume, git-ignored)
└── output/                 # Markdown output from CLI (Docker volume, git-ignored)
```

## Local Whisper Server Setup (Optional)

If you want free, GPU-accelerated transcription instead of using API credits, you can run a local whisper-server on your host machine. The Docker container communicates with it over the network.

### Why?

- **Free** after initial setup
- **Fast** with GPU acceleration (Metal on Mac, CUDA on Nvidia)
- **Private** — audio never leaves your machine

### Requirements

- macOS with Apple Silicon (M1/M2/M3/M4) or Linux with an NVIDIA GPU
- ~3GB disk space for the model file

### Build whisper.cpp

```bash
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp

# macOS with Metal GPU
cmake -B build -DWHISPER_METAL=ON
cmake --build build --config Release

# Download the model (large-v3-turbo recommended)
./models/download-ggml-model.sh large-v3-turbo
```

### Run the Server

```bash
./build/bin/whisper-server \
  -m models/ggml-large-v3-turbo.bin \
  --port 8080 \
  --convert
```

The `--convert` flag tells the server to auto-convert audio formats (including MP3) via ffmpeg.

### Verify It Works

```bash
curl http://127.0.0.1:8080/inference \
  -F file="@test-audio.mp3" \
  -F temperature="0.0" \
  -F response_format="json"
```

### Use It

In the web UI, select "Local whisper-server" from the dropdown. Or via CLI:

```bash
docker compose run cli --transcriber local "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Model Options

| Model | Size | RAM Needed | Quality | Speed |
|-------|------|------------|---------|-------|
| `tiny` | ~75MB | ~1GB | Low | Very fast |
| `base` | ~140MB | ~1GB | Decent | Fast |
| `small` | ~460MB | ~2GB | Good | Moderate |
| `medium` | ~1.5GB | ~4GB | Great | Slower |
| **`large-v3-turbo`** | **~1.6GB** | **~4GB** | **Excellent** | **Fast for its size** |
| `large-v3` | ~3GB | ~6GB | Best | Slowest |

**Recommendation:** `large-v3-turbo` is the best balance of speed and accuracy.

## Troubleshooting

**"GROQ_API_KEY is not set"**
- Make sure you have a `.env` file in the project root with your key
- Run `cp .env.example .env` and fill in your keys

**"Could not connect to whisper-server"**
- This only applies if using `--transcriber local`
- Make sure the whisper-server is running on your host machine on port 8080
- Or switch to `--transcriber groq` (the default) which requires no local setup

**Video download fails**
- Check that the URL is a valid, publicly accessible YouTube video
- Private, age-restricted, and region-locked videos are not supported
- Make sure `yt-dlp` is up to date (the Docker image handles this)

**Summaries look poorly formatted**
- Delete the video and re-summarize it — prompt improvements may have been made since it was first processed

**Docker build fails**
- Make sure Docker Desktop is running
- Try `docker compose build --no-cache` for a clean rebuild
