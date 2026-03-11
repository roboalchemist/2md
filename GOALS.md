# 2md Goals

## Vision

Turn 2md into a comprehensive **anything-to-markdown** toolkit that runs entirely on Apple Silicon, leveraging MLX for all AI inference. Every converter produces clean markdown with YAML frontmatter. No cloud APIs required.

## Philosophy

- **Local-first**: All AI runs on-device via MLX (mlx-audio, mlx-lm, mlx-vlm)
- **Consistent output**: Every tool produces markdown with YAML frontmatter
- **One tool per source type**: `yt2md`, `pdf2md`, `web2md`, `doc2md`, `img2md`, etc.
- **Shared code**: Common frontmatter builder, CLI patterns (typer), and output formatting
- **Minimal dependencies**: Prefer single-purpose libraries over kitchen-sink frameworks
- **Hybrid approach**: Use fast non-AI extraction first, fall back to VLM only when needed

## MLX Model Stack

| Layer | Library | Models | Purpose |
|-------|---------|--------|---------|
| **STT** | `mlx-audio[stt]` | Parakeet v3 (0.6b, 1.1b) | Audio/video transcription |
| **HTML→MD** | `mlx-lm` | ReaderLM-v2 (`mlx-community/jinaai-ReaderLM-v2`, 4-bit, 869MB) | Clean web content extraction from raw HTML |
| **Vision/OCR** | `mlx-vlm` | Qwen3.5 (all sizes natively multimodal) | Image OCR, document understanding, diagrams, slides |
| **Document AI** | `mlx-vlm` | SmolDocling-256M | Lightweight document extraction fallback |
| **Text** | `mlx-lm` | (optional, for cleanup) | Transcript cleanup, summarization |

### Qwen3.5 — The Primary VLM

**All Qwen3.5 models are natively multimodal** (text+image+video). There is no separate "-VL" variant — vision is built into every size. This is a fundamental shift from older Qwen generations.

Available on mlx-community (all 4-bit quantized):

| Model | HuggingFace ID | 4-bit Size | Speed (M4 Max) | Notes |
|-------|---------------|-----------|----------------|-------|
| 0.8B | `mlx-community/Qwen3.5-0.8B-MLX-8bit` | <1 GB | Very fast | Any Mac |
| 4B | `mlx-community/Qwen3.5-4B-MLX-4bit` | ~2.5 GB | Fast | MacBook Air viable |
| 9B | `mlx-community/Qwen3.5-9B-MLX-4bit` | ~6 GB | 60+ tok/s | Outperforms prev-gen 30B |
| **27B** | `mlx-community/Qwen3.5-27B-4bit` | **~17 GB** | ~30-40 tok/s | **Default for this machine (36GB)** |
| 35B-A3B | `mlx-community/Qwen3.5-35B-A3B-4bit` | ~20 GB | 60-70 tok/s | MoE, only 3B active, very fast |

**Default model**: Qwen3.5-27B 4-bit (~17GB). Fits comfortably on 36GB with ~19GB headroom for inference KV cache and OS. 262K token context window. 32-language OCR.

### Other Key Models

- **ReaderLM-v2**: 1.5B params, 512K context. Outperforms GPT-4o on HTML→markdown (ROUGE-L 0.84). Feed raw HTML, get clean markdown. MLX 4-bit at `mlx-community/jinaai-ReaderLM-v2` (869MB).
- **SmolDocling-256M**: Ultra-lightweight document VLM from IBM+HuggingFace. 15-20ms/page. Purpose-built for document→markdown. Only ~400MB.
- **Parakeet v3**: Already integrated. 0.6B default, 1.1B for higher accuracy. Handles chunked long audio internally.

## Enhanced pdf2md — Hybrid Extraction

The current pdf2md uses pymupdf4llm for text-layer extraction (instant, 0.1s/page). Enhance it with VLM fallback for scanned/image pages:

```
PDF input
  ├─ pymupdf4llm extracts text layer (0.1s/page, no GPU)
  │   ├─ Page has >50 chars? → Use text extraction (fast path)
  │   └─ Page has <50 chars? → Scanned/image page (VLM path)
  │       └─ Render page as image → Qwen3.5-27B via mlx-vlm → markdown
  └─ Output: markdown with frontmatter
```

**Speed comparison**:
| Method | Speed | When to Use |
|--------|-------|-------------|
| pymupdf4llm (current) | 0.1s/page | Born-digital PDFs with text layer |
| Qwen3.5-9B VLM | ~2-3s/page | Scanned pages (lighter model) |
| Qwen3.5-27B VLM | ~5-10s/page | Complex layouts, tables, equations |
| SmolDocling-256M | 15-20ms/page | Batch processing, speed-critical |
| MinerU (MLX backend) | 1-3s/page | Full pipeline alternative (109 languages) |

**VLM prompt for document extraction**:
```
Extract all text from this document page as clean markdown.
- Preserve tables as markdown tables
- Convert equations to LaTeX ($...$ inline, $$...$$ block)
- Use proper heading levels (#, ##, ###)
- Preserve code blocks with language tags
- Do NOT add text not present in the original
Output ONLY the markdown.
```

### Alternative: MinerU

MinerU (`pip install mineru`) is a complete turnkey PDF→markdown pipeline with MLX backend (`vlm-mlx-engine`). It auto-detects scanned vs text PDFs, handles tables/equations/images, and supports 109 languages. Use it if building a custom hybrid pipeline is overkill.

## New Converters

### Priority 1: web2md.py — Web Pages to Markdown

**Pipeline**: URL → fetch HTML (httpx) → ReaderLM-v2 (mlx-lm) → markdown with frontmatter

- Fetch page HTML with proper headers
- Run through ReaderLM-v2 locally to extract clean article content
- Generate frontmatter: title, author, date, sitename, url, description, fetched_at
- Fall back to `trafilatura` for metadata extraction if ReaderLM doesn't capture it
- Support: single URL, list of URLs from file, stdin pipe

**Why ReaderLM-v2 over trafilatura alone**: ReaderLM handles malformed HTML, complex layouts, nested tables, and code blocks better than rule-based extractors. 1.5B model, <1GB at 4-bit, 512K context.

### Priority 2: doc2md.py — Office Documents to Markdown

**Pipeline**: DOCX/PPTX/XLSX/EPUB → `markitdown` extraction → markdown with frontmatter

- Use Microsoft's `markitdown` library (`pip install markitdown[all]`)
- Auto-detect format from extension
- DOCX: headings, lists, tables, images preserved
- PPTX: slide-per-section layout with speaker notes
- XLSX: sheets as markdown tables
- EPUB: chapter structure preserved
- Generate frontmatter from document properties: title, author, created, modified, subject, format, pages/slides/sheets

### Priority 3: img2md.py — Images to Markdown

**Pipeline**: Image → Qwen3.5 VLM (mlx-vlm) → markdown with frontmatter

- OCR text extraction from photos of documents, whiteboards, screenshots
- Diagram/chart description and data extraction
- Slide photo → structured markdown
- Handwriting recognition
- Generate frontmatter: source, dimensions, format, model_used, fetched_at
- Support batch processing (directory of images)
- Model selection: `--model qwen3.5-27b` (default, high quality) or `--model qwen3.5-9b` (faster) or `--model smoldocling` (ultra-fast)

### Priority 4: html2md.py — Local HTML Files to Markdown

**Pipeline**: HTML file → ReaderLM-v2 (mlx-lm) → markdown with frontmatter

- For local `.html` files (saved pages, exports, scraped archives)
- Same ReaderLM-v2 engine as web2md, but reads from file instead of fetching
- Batch mode: process a directory of HTML files
- Frontmatter from `<meta>` tags and `<title>`

### Priority 5: Enhanced pdf2md — VLM Fallback

Upgrade existing pdf2md.py with the hybrid approach described above. Add `--ocr` flag to force VLM on all pages, or auto-detect thin pages (already flagged in current code).

### Future Ideas (Lower Priority)

| Tool | Source | Library | Notes |
|------|--------|---------|-------|
| `email2md.py` | EML/MBOX files | `email` stdlib + ReaderLM-v2 for HTML body | Underserved niche. Frontmatter: from, to, subject, date, attachments |
| `rss2md.py` | RSS/Atom feeds | `feedparser` + ReaderLM-v2 per article | Podcast feed → episode list with show notes |
| `csv2md.py` | CSV/TSV files | `pytablewriter` or pandas | Data tables with column type detection |
| `slide2md.py` | PPTX with VLM | `mlx-vlm` + Qwen3.5 | VLM-powered slide understanding (vs pure text extraction in doc2md) |
| `repo2md.py` | Git repositories | Tree walking + ast-grep | Codebase structure, README, key files as single markdown |

## Architecture

### Shared Module: `md_common.py`

Extract shared code from yt2md.py into a common module:

```
md_common.py
├── build_frontmatter(metadata: dict) -> str     # Already exists in yt2md
├── write_output(content: str, path: str) -> str  # Common file writer
├── detect_format(path: str) -> str               # File type detection
├── setup_logging(verbose: bool) -> Logger        # Common logging setup
└── load_vlm(model: str) -> tuple                 # Shared VLM loader (mlx-vlm)
```

### CLI Pattern

Every tool follows the same typer pattern:
```bash
python <tool>.py <input> [OPTIONS]
  -o, --output-dir PATH     # Output directory (default: cwd)
  -f, --format [md|txt]     # Output format (default: md)
  -m, --model NAME          # Model override (where applicable)
  -v, --verbose             # DEBUG logging
```

### Model Management

Models are downloaded on first use via HuggingFace Hub. Shared `download_models.py` pre-fetches all models:

```bash
python download_models.py              # Download all default models
python download_models.py --stt        # STT models only (Parakeet)
python download_models.py --vlm        # Vision models only (Qwen3.5-27B)
python download_models.py --reader     # ReaderLM-v2 only
python download_models.py --docling    # SmolDocling-256M only
```

## Memory Budget (36GB MacBook)

| Model | 4-bit Size | Use Case | Loaded When |
|-------|-----------|----------|-------------|
| Parakeet v3 0.6B | ~0.5 GB | Audio transcription | yt2md |
| ReaderLM-v2 1.5B | ~0.9 GB | HTML→markdown | web2md, html2md |
| SmolDocling 256M | ~0.4 GB | Fast document OCR | pdf2md (batch), img2md (fast) |
| **Qwen3.5-27B** | **~17 GB** | **Image/document understanding** | **img2md, pdf2md (OCR)** |

- Models are loaded on-demand, one at a time (not all at once)
- Qwen3.5-27B 4-bit (17GB) fits on 36GB with ~19GB headroom for KV cache + OS
- For 128GB machines: can run Qwen3.5-27B 8-bit or multiple models simultaneously

## Non-Goals

- No cloud API dependencies (no OpenAI, no Jina API, no Google)
- No GUI — CLI only
- No real-time/streaming — batch processing only
- No translation — output matches source language
- Not a general-purpose LLM chat tool — focused on conversion to markdown
