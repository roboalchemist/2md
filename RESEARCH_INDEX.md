# 2md Research Index

**Purpose**: Central hub for research documents. Navigate complex topics efficiently.

**Last Updated**: 2026-03-18

---

## Research Categories

### 1. JSON & YAML to Markdown Conversion (CURRENT)

**Status**: Complete (2026-03-18)
**Purpose**: Plan for adding `json2md.py` / `data2md.py` to toolkit

**Documents**:
- **[RESEARCH_JSON_YAML_TO_MD.md](RESEARCH_JSON_YAML_TO_MD.md)** (17 KB, 542 lines)
  - Full analysis of 5 strategies
  - Dependency review (20+ libraries)
  - Edge cases + frontmatter strategy
  - **Read when**: You want complete understanding

- **[RECOMMENDATION_JSON_YAML.md](RECOMMENDATION_JSON_YAML.md)** (8.4 KB, 284 lines)
  - TL;DR + decision flowchart
  - Implementation roadmap (4 phases)
  - Code snippets + testing strategy
  - **Read when**: You're ready to implement

- **[REFERENCE_JSON_YAML_STRATEGIES.md](REFERENCE_JSON_YAML_STRATEGIES.md)** (11 KB, 411 lines)
  - Decision tree + when to use each
  - Copy-paste templates
  - Truncation rules + edge cases
  - **Read when**: Coding implementation

**Key Finding**: Multi-strategy with NO new dependencies. Use stdlib `json` only.

**Implementation Effort**: ~2-3 hours (Phase 1 + tests)

**Next Steps**:
- [ ] Implement Phase 1 (fenced code + frontmatter)
- [ ] Add tests
- [ ] Create CLI wrapper (json2md.py)

---

### 2. EPUB Conversion (COMPLETED EARLIER)

**Status**: Complete (research deferred implementation)
**Purpose**: Evaluate if EPUB → markdown feasible for 2md

**Key Finding**: EPUB support is already in project via `markitdown`. Current implementation sufficient. Enhancements optional (add ebooklib if users request metadata extraction).

---

## Quick Navigation

### I want to implement JSON/YAML support
1. Read: **RECOMMENDATION_JSON_YAML.md** (overview + priorities)
2. Reference: **REFERENCE_JSON_YAML_STRATEGIES.md** (while coding)
3. Dig deeper: **RESEARCH_JSON_YAML_TO_MD.md** (if stuck)

### I want to understand all the options
1. Start: **RESEARCH_JSON_YAML_TO_MD.md** (comprehensive)
2. Decision matrix at top of file

### I need copy-paste code
1. Go to: **REFERENCE_JSON_YAML_STRATEGIES.md** (organized by use case)

### I want to see the recommendation
1. Read: **RECOMMENDATION_JSON_YAML.md** (5-10 min read)

---

## Document Overview

| Document | Type | Purpose | Audience | Read Time |
|----------|------|---------|----------|-----------|
| RESEARCH_JSON_YAML_TO_MD.md | Analysis | Deep evaluation | Architects | 30 min |
| RECOMMENDATION_JSON_YAML.md | Summary | Action plan | Implementers | 10 min |
| REFERENCE_JSON_YAML_STRATEGIES.md | Reference | Lookup guide | Developers | 5 min + coding |

---

## Key Decisions Made

### JSON/YAML Conversion

**✅ Approved**:
- Multi-strategy approach (no single "best" method)
- Zero new dependencies (use stdlib `json`)
- Start with Phase 1: fenced code + frontmatter
- Add optional strategies if time permits

**❌ Rejected**:
- New hard dependencies (yaml-to-markdown, jsonschema2md, pandas)
- Single unified strategy
- Trying to handle all edge cases in Phase 1

---

## Implementation Status

### Phase 1 (Required)
- [ ] `json_to_fenced()` — fenced code wrapper
- [ ] `build_data_frontmatter()` — metadata extraction
- [ ] `json_to_markdown_smart()` — decision logic
- [ ] Unit tests

### Phase 2 (Optional)
- [ ] `dict_to_markdown()` — structured extraction
- [ ] `array_to_markdown_table()` — table rendering

### Phase 3 (Advanced)
- [ ] Schema detection (OpenAPI, package.json)

### Phase 4 (Later)
- [ ] CLI wrapper & integration

---

## Related Project Files

```
2md/
├── RESEARCH_JSON_YAML_TO_MD.md     ← Comprehensive analysis
├── RECOMMENDATION_JSON_YAML.md     ← What to build
├── REFERENCE_JSON_YAML_STRATEGIES.md ← How to build
├── RESEARCH_INDEX.md               ← This file
├── yt2md.py                        ← Existing pattern to follow
├── pdf2md.py                       ← Existing pattern to follow
├── GOALS.md                        ← Project roadmap
└── requirements.txt                ← Dependencies
```

---

## How to Use This Index

**5-minute reader**: Jump to RECOMMENDATION section, look at decision matrix

**30-minute reader**: Read RESEARCH doc sections 1-4, Decision Tree

**Developer ready to code**: Open REFERENCE doc, start with Phase 1 code snippets

**Architect/Decision maker**: Read RECOMMENDATION doc fully

---

## Adding New Research

To add new research to this index:

1. Create `RESEARCH_<TOPIC>.md` (comprehensive)
2. Optionally create `RECOMMENDATION_<TOPIC>.md` (actionable)
3. Optionally create `REFERENCE_<TOPIC>.md` (lookup)
4. Update this index with new section

**Naming convention**:
- `RESEARCH_*.md` — Comprehensive analysis
- `RECOMMENDATION_*.md` — Action plan
- `REFERENCE_*.md` — Lookup/code snippets
- `RESEARCH_INDEX.md` — This file

---

## Files Summary

| File | Size | Lines | Created | Status |
|------|------|-------|---------|--------|
| RESEARCH_JSON_YAML_TO_MD.md | 17 KB | 542 | 2026-03-18 | Complete |
| RECOMMENDATION_JSON_YAML.md | 8.4 KB | 284 | 2026-03-18 | Complete |
| REFERENCE_JSON_YAML_STRATEGIES.md | 11 KB | 411 | 2026-03-18 | Complete |
| RESEARCH_INDEX.md | This file | — | 2026-03-18 | Complete |

**Total research**: ~50 KB, committed to git

---

## References & Sources

All documents include full citations. Key resources consulted:
- PyPI package evaluations
- GitHub project examples
- Official documentation (Real Python, FastAPI, pandas)
- Stack Overflow patterns
- Industry standards (JSON Lines, YAML, Markdown)

---

## Notes

- All research files are committed to git (not deleted, good for history)
- This is a living index — update as new research is added
- Keep document sizes reasonable (<20 KB each for readability)
- Link to external repos/docs when comprehensive
