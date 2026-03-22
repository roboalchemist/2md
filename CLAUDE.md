# any2md — Convert Anything to Markdown

## Overview

A toolkit for converting any media, document, or data format to markdown with YAML frontmatter. AI inference runs locally on Apple Silicon via MLX. No cloud APIs. 16 converters, 7 zero-dependency (stdlib only).

## Project Structure

```
any2md/
├── src/any2md/
│   ├── __init__.py      # Package init, __version__
│   ├── cli.py           # Unified entry point — auto-detect + subcommands (200 lines)
│   ├── common.py        # Shared: build_frontmatter(), setup_logging(), OutputFormat, write_output() (155 lines)
│   ├── yt.py            # Audio/video/YouTube transcription + Sortformer diarization (847 lines)
│   ├── pdf.py           # PDF extraction + optional VLM OCR via mlx-vlm (578 lines)
│   ├── img.py           # Image OCR via Qwen3.5 (mlx-vlm) (422 lines)
│   ├── web.py           # Web URL → markdown via ReaderLM-v2 (mlx-lm) (448 lines)
│   ├── html.py          # Local HTML → markdown via ReaderLM-v2 (285 lines)
│   ├── doc.py           # Office docs via markitdown (DOCX/PPTX/XLSX/EPUB/ODT/RTF) (334 lines)
│   ├── rst.py           # reStructuredText via pypandoc/docutils fallback (397 lines)
│   ├── csv.py           # CSV/TSV → markdown tables, stdlib only (456 lines)
│   ├── data.py          # JSON/YAML/JSONL → smart markdown, stdlib + optional PyYAML (565 lines)
│   ├── db.py            # SQLite → schema + sample data, stdlib only (545 lines)
│   ├── sub.py           # Subtitles (SRT/VTT/ASS) via pysubs2 (407 lines)
│   ├── nb.py            # Jupyter notebooks, stdlib only (400 lines)
│   ├── eml.py           # Email (.eml/.mbox), stdlib only (505 lines)
│   ├── org.py           # Org-mode, pure regex (669 lines)
│   ├── tex.py           # LaTeX, pure regex (766 lines)
│   └── man.py           # Unix man pages, mandoc + regex fallback (733 lines)
├── tests/
│   ├── conftest.py      # Minimal (docstring only)
│   ├── create_fixtures.py
│   ├── fixtures/        # sample.{docx,html,ipynb,jpg,pdf,pptx,rst,xlsx}
│   ├── audio/           # test audio files (mp3/wav)
│   ├── test_yt.py       # 18 tests (unittest.TestCase)
│   ├── test_pdf.py      # 10 tests
│   ├── test_web.py      # 13 tests
│   ├── test_html.py     # 22 tests
│   ├── test_doc.py      # 16 tests
│   ├── test_img.py      # 32 tests
│   ├── test_rst.py      # 27 tests
│   ├── test_csv.py      # 74 tests
│   ├── test_data.py     # 97 tests
│   ├── test_db.py, test_sub.py, test_nb.py, test_eml.py, test_org.py, test_tex.py, test_man.py
│   ├── test_inference.py    # 14 @pytest.mark.slow (real model inference)
│   └── test_integration.py  # 9 @pytest.mark.integration (real file fixtures)
├── scripts/
│   ├── benchmark_models.py
│   └── download_models.py
├── pyproject.toml       # hatchling build, optional deps groups
├── pytest.ini
├── requirements.txt
├── GOALS.md             # Full expansion plan and MLX model stack
├── GOAL.md
└── README.md
```

**Total**: ~9,500 lines of source code across 18 modules. 766 tests.

## Key Libraries & Dependencies

| Library | Purpose | Optional Group |
|---------|---------|----------------|
| `typer` | CLI framework (required for all) | core |
| `mlx-audio[stt]` | Parakeet STT + Sortformer diarization | `[stt]` |
| `yt-dlp` | YouTube audio download | `[stt]` |
| `pymupdf4llm` | PDF text extraction | `[pdf]` |
| `mlx-vlm` | Image/PDF OCR via Qwen3.5 | `[img]` |
| `mlx-lm` | HTML→markdown via ReaderLM-v2 | `[web]` |
| `httpx` | HTTP fetching for web URLs | `[web]` |
| `markitdown` | Office document conversion | `[doc]` |
| `pypandoc` | RST conversion (docutils fallback) | `[rst]` |
| `pysubs2` | Subtitle parsing | runtime |
| `trafilatura` | Web metadata extraction fallback | runtime |
| `Pillow` | Image handling for VLM | runtime |
| `ffmpeg`/`ffprobe` | Audio conversion (system dep) | system |

**Zero-dep converters** (stdlib only): csv, data, db, nb, eml, org, tex, man

## Architecture

### Entry Point

`any2md.cli:app` — registered as `any2md` console script via pyproject.toml.

**Auto-detection**: `_detect_tool(input)` maps file extensions/URLs to converter names. YouTube URLs and 11-char IDs → `yt`, HTTP URLs → `web`, then by extension.

**Lazy imports**: `_get_tool_apps()` wraps each converter import in try/except to tolerate missing optional deps. Each converter exports a `typer.Typer()` app.

**Subcommands**: `yt`, `audio`, `video`, `pdf`, `img`, `web`, `html`, `doc`, `rst`, `csv`, `data`, `db`, `sub`, `nb`, `eml`, `org`, `tex`, `man`. `audio` and `video` are aliases for `yt`.

### Converter Pattern

Every converter module follows the same pattern:
1. Imports `build_frontmatter`, `OutputFormat`, `write_output`, `setup_logging` from `any2md.common`
2. Defines a `typer.Typer()` app with consistent CLI flags: `--output-dir`, `--format`, `--verbose`
3. Has a `process_*_file()` main function
4. Extracts metadata → builds frontmatter → converts content → writes output
5. External deps wrapped in try/except with graceful fallbacks

### Shared Module: `common.py`

- `build_frontmatter(metadata: dict) -> str` — Hand-rolled YAML formatter (no PyYAML dep). Handles scalars, lists, nested dicts (chapters), multi-line strings (description via `|` block scalar), auto-quoting special chars.
- `OutputFormat(str, Enum)` — `md`, `txt`
- `setup_logging(verbose)` — Configures root logger to stderr explicitly
- `write_output(content, path)` — File writer with parent dir creation
- `write_json_output(metadata, content, source, converter, fields)` — JSON output to stdout for `--json` mode
- `_filter_fields(data, fields_str)` — Dot-notation field selection for `--fields`
- `write_json_error(code, message, recoverable)` — Structured JSON errors to stderr
- `set_json_mode(enabled)` / `is_json_mode()` — Global JSON mode flag
- `load_vlm(model)` — Stub for mlx-vlm loading

### Data Flow

```
cli.py: argv → _detect_tool() or explicit subcommand → lazy import converter → converter.app()
Each converter: input → extract metadata → convert content → build_frontmatter() → write_output()
yt.py: input → auto_detect → [yt-dlp | local file] → ffmpeg 16kHz WAV → mlx-audio transcribe → format
pdf.py: PDF → pymupdf4llm extract (fast) or VLM OCR (scanned pages) → format
web.py: URL → httpx fetch → ReaderLM-v2 (mlx-lm) → markdown
img.py: image → Qwen3.5 (mlx-vlm) → markdown
```

### Model System

| Model | Library | Default ID | Use |
|-------|---------|-----------|-----|
| Parakeet v3 | mlx-audio | `mlx-community/parakeet-tdt-0.6b-v3` | Audio/video STT |
| Sortformer | mlx-audio | sortformer diarization model | Speaker diarization |
| ReaderLM-v2 | mlx-lm | `mlx-community/jinaai-ReaderLM-v2` | HTML→markdown |
| Qwen3.5-9B | mlx-vlm | `mlx-community/Qwen3.5-9B-MLX-4bit` | Image OCR, PDF OCR |

Model aliases in yt.py: `parakeet-v3`, `parakeet-v2`, `parakeet-1.1b`, `parakeet-ctc`
Model aliases in img.py: `qwen3.5-4b`, `qwen3.5-9b` (default), `qwen3.5-27b`, `qwen3.5-35b`, `smoldocling`

## Installation

```bash
# Editable install with all optional deps
uv pip install -e '.[all]'

# Or only what you need
uv pip install -e '.[stt]'    # Audio/video
uv pip install -e '.[pdf]'    # PDF
uv pip install -e '.[img]'    # Image OCR
uv pip install -e '.[web]'    # Web pages
uv pip install -e '.[doc]'    # Office docs

# System dep for audio/video
brew install ffmpeg

# Pre-download AI models
python scripts/download_models.py --all
```

## Testing

- **Framework**: unittest.TestCase classes, run via pytest
- **Test count**: 766 collected tests
- **Run all unit tests**: `python -m pytest tests/`
- **Run specific**: `python -m pytest tests/test_csv.py -v`
- **Slow tests** (real inference): `python -m pytest tests/test_inference.py -m slow -v -s`
- **Integration tests** (real fixtures): `python -m pytest tests/test_integration.py -m integration -v`
- **Markers**: `@pytest.mark.slow` (14 tests), `@pytest.mark.integration` (9 tests)
- **Pattern**: unittest.TestCase with `unittest.mock.patch()` for mocking. FakeAlignedSentence objects for mlx-audio mocks. Tests auto-skip if models not cached.
- **Fixtures**: `tests/fixtures/` (sample files), `tests/audio/` (audio files)
- **Config**: `pyproject.toml` `[tool.pytest.ini_options]` + `pytest.ini`

## CLI Reference

```bash
# Auto-detect (just pass a file or URL)
any2md <input>

# Explicit subcommands
any2md yt <input> [--model NAME] [--diarize] [--format md|srt|txt] [--chunk-duration FLOAT] [--keep-audio]
any2md pdf <input> [--pages "1-10,15"] [--ocr]
any2md img <input> [--model NAME]
any2md web <url>
any2md csv <input> [--max-rows N] [--max-col-width N]
any2md db <input> [--max-rows N] [--skip-views]
any2md sub <input>
any2md nb <input> [--no-outputs]

# Global flags (all subcommands)
  --json, -j                # JSON output to stdout (agent-friendly)
  --fields FIELDS           # Field selection for --json (dot-notation: frontmatter.rows,content)
  --quiet, -q               # Suppress INFO logs
  --version, -V             # Print version and exit
  -o, --output-dir PATH     # Output directory (default: cwd)
  -f, --format [md|txt]     # Output format (default: md)
  -v, --verbose             # DEBUG logging

# Utility subcommands
any2md deps                 # Show installed/missing optional dependencies
```

## Roadmap

See [GOAL.md](GOAL.md) for current goals and phase status.

## Project History

Originally `yt2srt` on `lightning-whisper-mlx`. Migrated to `yt2md` on `mlx-audio` with Parakeet, rewritten from argparse to typer. Then expanded from 2 tools (yt2md + pdf2md) to 16 converters as a proper Python package (`src/any2md/`) with unified CLI, optional dependency groups, and 740 tests.
