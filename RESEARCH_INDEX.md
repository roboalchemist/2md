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

## Quick Navigation

### I want to implement JSON/YAML support
1. Read: **RECOMMENDATION_JSON_YAML.md** (overview + priorities)
2. Reference: **REFERENCE_JSON_YAML_STRATEGIES.md** (while coding)
3. Dig deeper: **RESEARCH_JSON_YAML_TO_MD.md** (if stuck)

### I want to understand all the options
1. Start: **RESEARCH_JSON_YAML_TO_MD.md** (comprehensive)

### I need copy-paste code
1. Go to: **REFERENCE_JSON_YAML_STRATEGIES.md** (organized by use case)

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

---

## Document Overview

| Document | Type | Purpose | Read Time |
|----------|------|---------|-----------|
| RESEARCH_JSON_YAML_TO_MD.md | Analysis | Deep evaluation | 30 min |
| RECOMMENDATION_JSON_YAML.md | Summary | Action plan | 10 min |
| REFERENCE_JSON_YAML_STRATEGIES.md | Reference | Lookup guide | 5 min + coding |

---

## Implementation Roadmap

Phase 1 (Required): ~2-3 hours
- [ ] `json_to_fenced()` — fenced code wrapper
- [ ] `build_data_frontmatter()` — metadata extraction
- [ ] `json_to_markdown_smart()` — decision logic
- [ ] Unit tests

Phase 2 (Optional): ~2 hours
- [ ] `dict_to_markdown()` — structured extraction
- [ ] `array_to_markdown_table()` — table rendering

---

## Files Summary

| File | Size | Lines |
|------|------|-------|
| RESEARCH_JSON_YAML_TO_MD.md | 17 KB | 542 |
| RECOMMENDATION_JSON_YAML.md | 8.4 KB | 284 |
| REFERENCE_JSON_YAML_STRATEGIES.md | 11 KB | 411 |

**Total research**: ~50 KB, committed to git
