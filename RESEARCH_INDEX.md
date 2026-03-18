# 2md Research Index

**Purpose**: Central index of all research documents. Useful for navigating complex topics.

## Recent Research

### 1. JSON & YAML to Markdown Conversion (2026-03-18)

**Why this research**: Planning to add `json2md.py` / `data2md.py` to toolkit. Need to decide how to convert structured data to markdown for LLM context.

**Files**:
- **[RESEARCH_JSON_YAML_TO_MD.md](RESEARCH_JSON_YAML_TO_MD.md)** (17 KB, 542 lines)
  - Comprehensive evaluation of 5 approaches
  - Dependency analysis (PyYAML, ruamel.yaml, libraries to avoid)
  - Frontmatter strategy + large file handling
  - 20+ sources consulted
  - **Best for**: Understanding tradeoffs, detailed rationale

- **[RECOMMENDATION_JSON_YAML.md](RECOMMENDATION_JSON_YAML.md)** (8.4 KB, 284 lines)
  - Executive TL;DR with priorities
  - Decision logic & implementation roadmap
  - Code snippets for each strategy
  - Testing strategy + integration with existing code
  - **Best for**: Implementing the solution, quick reference

- **[REFERENCE_JSON_YAML_STRATEGIES.md](REFERENCE_JSON_YAML_STRATEGIES.md)** (11 KB, 411 lines)
  - When to use each strategy (decision tree)
  - Copy-paste code snippets
  - Edge cases + truncation rules
  - Performance targets + template implementation
  - **Best for**: Quick lookup during coding, copy-paste reference

**Key Finding**: Use **multi-strategy approach** with NO new dependencies:
1. Fenced code blocks (fallback, works for LLMs)
2. Structured extraction (config files, metadata)
3. Table rendering (arrays of objects)
4. Schema detection (OpenAPI, package.json)
5. JSONL streaming (large files)

**Next Steps**:
- [ ] Implement Phase 1: fenced code + frontmatter
- [ ] Add to yt2md.py or create data2md.py
- [ ] Write tests (see RECOMMENDATION doc)

---

### 2. EPUB Conversion (2026-03-18)

**Why this research**: Evaluate if EPUB → markdown is feasible for 2md toolkit.

**File**:
- **[RESEARCH_EPUB_CONVERSION.md](RESEARCH_EPUB_CONVERSION.md)** (18 KB, 505 lines)
  - Evaluated 6 libraries (ebooklib, calibre, pandoc, etc)
  - Tradeoffs for each approach
  - Dependency analysis
  - LLM context implications
  - 15+ sources

**Key Finding**: EPUB support is **complex and deferred**. Calibre + pandoc pipeline works but adds system dependencies. Better to focus on pdf2md improvements first.

---

## How to Use This Index

### I Want to Implement JSON→Markdown Support
→ Read **RECOMMENDATION_JSON_YAML.md** (start here)
→ Use **REFERENCE_JSON_YAML_STRATEGIES.md** while coding
→ Check **RESEARCH_JSON_YAML_TO_MD.md** if you hit edge cases

### I Need to Understand the Full Context
→ Read **RESEARCH_JSON_YAML_TO_MD.md** (comprehensive)
→ Reference the decision matrix at the top
→ Check sources for deeper dives

### I'm Implementing a Specific Feature
→ Use **REFERENCE_JSON_YAML_STRATEGIES.md** as a lookup table
→ Copy code snippets directly
→ Check edge cases section

### I Want to Evaluate EPUB Support
→ Read **RESEARCH_EPUB_CONVERSION.md**
→ See the "Recommendation" section (likely deferred)

---

## Document Overview

| Document | Purpose | Audience | Best For |
|----------|---------|----------|----------|
| RESEARCH_JSON_YAML_TO_MD.md | Deep analysis | Decision makers | Understanding tradeoffs |
| RECOMMENDATION_JSON_YAML.md | Actionable plan | Implementers | Deciding what to build |
| REFERENCE_JSON_YAML_STRATEGIES.md | Lookup guide | Developers | Copy-paste during coding |
| RESEARCH_EPUB_CONVERSION.md | Feasibility study | Project leads | Evaluating future work |

---

## Quick Decisions Made

### JSON/YAML Conversion

✅ **Approved**:
- Use stdlib `json` only (required)
- Optional `PyYAML` if needed (likely already installed)
- Multi-strategy approach (no single "best" method)
- Start with Phase 1: fenced code + frontmatter

❌ **Rejected**:
- New dependencies: `yaml-to-markdown`, `jsonschema2md`, `pandas`
- Single unified strategy
- Trying to handle all edge cases in Phase 1

### EPUB Conversion

⏸️ **Deferred**:
- EPUB support is complex (6 different viable approaches)
- Would require significant dependencies (calibre, pandoc, or ebooklib)
- Focus on improving pdf2md.py first
- Revisit in next planning cycle

---

## Upcoming Research (Not Started)

Potential future topics for the toolkit:

- **HTML → Markdown** (URLs via ReaderLM)
- **Images → Markdown** (OCR + VLM via Qwen3.5)
- **DOCX/PPTX → Markdown** (markitdown library)
- **Database queries → Markdown** (SQL result formatting)
- **Performance optimization** (benchmark Parakeet v2 vs v3)
- **Speaker diarization** (detect multiple speakers in audio)

---

## How to Add New Research

1. **Create file**: `RESEARCH_<TOPIC>.md`
2. **Follow pattern**:
   - Executive summary (1 paragraph)
   - Approaches evaluated (with tradeoffs)
   - Key findings + recommendations
   - References/sources (with URLs)
   - Implementation roadmap (if applicable)

3. **Add to this index**: Update section above

4. **Optional**: Create `RECOMMENDATION_<TOPIC>.md` if actionable

---

## References & Sources

All research documents include full source citations. Key repositories consulted:
- PyPI (library evaluations)
- GitHub (working implementations)
- Official docs (Real Python, FastAPI, pandas, etc)
- Stack Overflow (practical patterns)
- Academic papers (standards: JSON, YAML, etc)

---

## File Management

All research files are committed to git. Naming convention:
- `RESEARCH_*.md` — Primary research documents
- `RECOMMENDATION_*.md` — Actionable recommendations
- `REFERENCE_*.md` — Lookup/reference guides
- `RESEARCH_INDEX.md` — This file (central hub)

**Size**: ~50 KB total for all research (reasonable for VCS)

**Archival**: Old research files are kept for historical context. Never delete.
