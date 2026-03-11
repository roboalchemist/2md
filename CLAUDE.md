# 2md - Media to Markdown Toolkit

## Overview

A toolkit for converting media (YouTube videos, audio files, PDFs) to markdown with YAML frontmatter. Built on [mlx-audio](https://github.com/Blaizzy/mlx-audio) (Parakeet v3) for transcription and [pymupdf4llm](https://github.com/pymupdf/RAG) for PDF extraction. Optimized for Apple Silicon.

## Project Structure

```
2md/
├── yt2md.py               # YouTube/audio/video → markdown/SRT/text
├── pdf2md.py              # PDF → markdown/text (page-delineated)
├── whisper_benchmark.py   # Interactive benchmark: compare STT models
├── benchmark_models.py    # Automated benchmark: warmup + timed runs
├── download_models.py     # Pre-download mlx-audio models from HuggingFace
├── quant_test.py          # Quick model smoke test
├── transcription_cleanup_prompt.txt  # LLM prompt for cleaning raw transcripts
├── requirements.txt       # Dependencies
├── test_yt2md.py          # Unit tests for yt2md
├── test_pdf2md.py         # Unit tests for pdf2md
├── test_benchmark.py      # Tests for whisper_benchmark.py
├── test_audio/            # Test audio files (mp3/wav)
├── benchmark-results/     # Generated benchmark reports
├── worklog.md             # Development history
└── .cursor/mcp.json       # Cursor MCP config
```

## Key Libraries & Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `mlx-audio[stt]` | >=0.4.0 | Parakeet/Whisper STT on Apple Silicon (MLX) |
| `pymupdf4llm` | >=0.2.0 | PDF text extraction to markdown |
| `typer` | >=0.9.0 | CLI framework |
| `yt-dlp` | >=2023.11.14 | YouTube audio download |
| `ffmpeg`/`ffprobe` | system | Audio conversion and duration detection |

## Tools

### yt2md.py — Audio/Video to Markdown
- **Input auto-detection**: YouTube URL, YouTube ID (11 chars), or local file path
- **Pipeline**: Download (yt-dlp) → Convert to 16kHz mono WAV (ffmpeg) → Transcribe (mlx-audio) → output
- **Formats**: `md` (default, with YAML frontmatter + timestamps), `srt`, `txt`
- **YouTube frontmatter**: title, channel, upload_date, duration, tags, chapters, view/like/comment counts, thumbnail, description, fetched_at
- **Long audio**: mlx-audio handles chunking internally via `--chunk-duration` (default 30s)
- **Model aliases**: `parakeet-v3`, `parakeet-v2`, `parakeet-1.1b`, `parakeet-ctc`, `whisper-turbo` → full HuggingFace IDs

### pdf2md.py — PDF to Markdown
- **Extraction**: pymupdf4llm text-layer extraction (instant, no VLM needed)
- **Page filtering**: `--pages 1-10,15,20-25` passed directly to pymupdf4llm (no full-doc scan)
- **Formats**: `md` (default, with YAML frontmatter + `## Page N` headings), `txt`
- **PDF frontmatter**: title, author, subject, keywords, creator, producer, created, modified, format, pages, source, fetched_at
- **Thin page detection**: Pages with <50 chars flagged as image-only (future VLM support)
- **Shared code**: Reuses `build_frontmatter()` from yt2md

## Testing

- **Framework**: `unittest` (stdlib), run via `pytest`
- **yt2md tests** (15): `python -m pytest test_yt2md.py`
- **pdf2md tests** (10): `python -m pytest test_pdf2md.py`
- **All tests**: `python -m pytest test_yt2md.py test_pdf2md.py test_benchmark.py`

## Installation

```bash
brew install ffmpeg
pip install -r requirements.txt

# Optional: pre-download STT models
python download_models.py
```

## Usage

```bash
# --- yt2md ---
python yt2md.py jNQXAC9IVRw                          # YouTube video → markdown
python yt2md.py my_video.mp4 -m parakeet-1.1b         # local file, bigger model
python yt2md.py podcast.mp3 -f srt                     # SRT subtitles
python yt2md.py lecture.mp4 -f txt -c 60               # plain text, 60s chunks

# --- pdf2md ---
python pdf2md.py document.pdf                          # full PDF → markdown
python pdf2md.py slides.pdf -p 1-10 -o ~/notes/        # first 10 pages
python pdf2md.py report.pdf -f txt                      # plain text
```
