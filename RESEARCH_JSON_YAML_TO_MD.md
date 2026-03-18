# Research: JSON & YAML to Markdown Conversion in Python

**Date**: 2026-03-18
**Scope**: Evaluate approaches for converting JSON/YAML to markdown for 2md toolkit + LLM context generation

## Executive Summary

**Recommendation**: Implement a **multi-strategy approach** tailored to data type:

1. **Fenced code blocks** (default fallback) — for LLM context, always valid
2. **Structured extraction** — for objects with <50 keys, convert to heading + key-value lists
3. **Table rendering** — for arrays of objects (3+ items, consistent schema)
4. **Schema detection** — special handling for known formats (OpenAPI, package.json, GeoJSON)
5. **JSONL streaming** — process line-by-line without loading into memory

**No new dependencies needed** — use stdlib `json` + optional `PyYAML` (likely already present). Avoid `yaml-to-markdown` lib (unmaintained, limited).

---

## Evaluation: Five Approaches

### 1. Fenced Code Block (Trivial but Effective)

**Implementation**:
```python
def json_to_fenced(data: dict | list, language: str = "json") -> str:
    content = json.dumps(data, indent=2)
    return f"```{language}\n{content}\n```"

def yaml_to_fenced(content: str) -> str:
    return f"```yaml\n{content}\n```"
```

**Pros**:
- Zero dependencies
- Always valid markdown
- Excellent for LLM context (preserves exact structure)
- Fast for large files
- Works with any structure (deep nesting, special chars)

**Cons**:
- Not "structured" — pure text block
- No extraction or searchability
- Large files create unwieldy code blocks

**When to use**: Default fallback, large files (>50KB), complex nesting, JSONL streams

**Cost**: O(1) — just serialize and wrap

---

### 2. Structured Extraction → Headings + Key-Value Lists

**Implementation**:
```python
def dict_to_markdown(data: dict, level: int = 2) -> str:
    lines = []
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            lines.append(f"{'#' * level} {key}")
            if isinstance(value, dict):
                lines.extend(dict_to_markdown(value, level + 1))
            elif isinstance(value, list):
                lines.extend(list_to_markdown(value, level + 1))
        else:
            lines.append(f"- **{key}**: {value}")
    return "\n".join(lines)

def list_to_markdown(items: list, level: int = 2) -> str:
    if not items:
        return "- (empty list)"

    # Heuristic: if all items are primitives, render as bullet list
    if all(not isinstance(x, (dict, list)) for x in items):
        return "\n".join(f"- {x}" for x in items)

    # If all items are dicts with same keys → table (see section 3)
    # Otherwise: iterate and extract each dict
    lines = []
    for i, item in enumerate(items[:10]):  # Limit to first 10
        if isinstance(item, dict):
            lines.append(f"{'#' * level} Item {i+1}")
            lines.extend(dict_to_markdown(item, level + 1))
    if len(items) > 10:
        lines.append(f"... ({len(items) - 10} more items)")
    return "\n".join(lines)
```

**Pros**:
- Human-readable structure
- Searchable headings
- Works with nested objects
- Good for metadata / config files

**Cons**:
- Deep nesting → excessive heading levels
- Not ideal for large homogeneous arrays
- Requires heuristics for mixed types

**When to use**: Config files, metadata, shallow objects (<5 levels), mixed-type data

**Cost**: O(n) recursive traversal; limit recursion depth to avoid runaway output

---

### 3. Table Rendering for Arrays

**Implementation**:
```python
def array_to_markdown_table(items: list[dict]) -> str:
    if not items or not isinstance(items[0], dict):
        return None  # Fall back to fenced code

    # Detect schema: all items have same keys?
    all_keys = set()
    for item in items:
        if isinstance(item, dict):
            all_keys.update(item.keys())

    # If too heterogeneous, bail out
    common_keys = set(items[0].keys())
    for item in items[1:]:
        if isinstance(item, dict):
            common_keys &= set(item.keys())

    if not common_keys or len(common_keys) > 10:
        return None  # Schema too loose or wide

    # Build table
    keys = list(common_keys)
    header = "| " + " | ".join(keys) + " |"
    separator = "|" + "|".join([" --- "] * len(keys)) + "|"

    rows = []
    for item in items[:100]:  # Limit to 100 rows
        values = [str(item.get(k, "")).replace("|", "\\|")[:50] for k in keys]
        rows.append("| " + " | ".join(values) + " |")

    md = header + "\n" + separator + "\n" + "\n".join(rows)
    if len(items) > 100:
        md += f"\n\n*(... {len(items) - 100} more rows)*"
    return md
```

**Pros**:
- Most readable for tabular data
- Excellent for LLM context (compact, scannable)
- Works in markdown viewers, wikis, GitHub
- Natural for CSVish data

**Cons**:
- Requires consistent schema
- Wide columns get truncated
- Limited to ~100 rows before becoming unwieldy
- Escape issues (pipes, special chars)

**When to use**: Array of objects with 3+ items, consistent schema, <10 keys, <100 rows

**Cost**: O(n * m) for n rows, m columns; truncate large values

---

### 4. Schema Detection → Special Rendering

Common formats in LLM workflows:

**OpenAPI / Swagger**:
- Detect `components`, `paths`, `info` → render as API spec excerpt
- Example: list all endpoints with methods + summary

**package.json / pyproject.toml** (when as JSON):
- Detect `dependencies`, `scripts`, `metadata` → extract and list
- Show only critical fields (version, description, maintainer)

**GeoJSON**:
- Detect `features` array with `geometry` → render as location list with coordinates

**Configuration files** (app config, environment):
- Detect key patterns (`enabled`, `timeout`, `url`) → render as config table

**Implementation**:
```python
def detect_and_render(data: dict) -> str | None:
    # Check for schema signatures
    if "openapi" in data or "swagger" in data:
        return render_openapi(data)
    if "components" in data and "paths" in data:
        return render_openapi(data)
    if "name" in data and "version" in data and ("scripts" in data or "dependencies" in data):
        return render_package_json(data)
    if "type" == "FeatureCollection" or "features" in data:
        return render_geojson(data)

    return None  # No special handling

def render_openapi(spec: dict) -> str:
    lines = ["# API Specification"]
    if "info" in spec:
        info = spec["info"]
        lines.append(f"- **Title**: {info.get('title', 'N/A')}")
        lines.append(f"- **Version**: {info.get('version', 'N/A')}")

    if "paths" in spec:
        lines.append("## Endpoints")
        for path, methods in list(spec["paths"].items())[:20]:
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    summary = details.get("summary", "")
                    lines.append(f"- `{method.upper()} {path}`: {summary}")

    return "\n".join(lines)
```

**Pros**:
- Highly relevant context for LLMs
- Reduces noise from boilerplate structure
- Can extract actionable info (endpoints, dependencies, config)

**Cons**:
- Requires regex/heuristics → false positives
- Hard to keep list of schemas updated
- Not generalizable (each format is custom)

**When to use**: When you know the data type (from file extension, explicit flag, or ML detection)

**Cost**: Detection O(1); rendering O(n) depending on schema

---

### 5. JSONL Streaming (No Loading Into Memory)

**Implementation**:
```python
def jsonl_to_markdown(filepath: str, max_items: int = 100) -> str:
    """Process JSONL without loading entire file into memory."""
    lines = ["# JSON Lines Data Stream"]
    count = 0

    try:
        with open(filepath, "r") as f:
            for line_num, raw_line in enumerate(f, 1):
                if count >= max_items:
                    lines.append(f"\n*(Preview: {max_items} items, {line_num} total lines)*")
                    break

                try:
                    item = json.loads(raw_line.strip())
                    # Render each item as a separate section
                    lines.append(f"## Item {line_num}")
                    if isinstance(item, dict):
                        lines.extend(dict_to_markdown(item, level=3))
                    else:
                        lines.append(f"```json\n{json.dumps(item, indent=2)}\n```")
                    count += 1
                except json.JSONDecodeError as e:
                    lines.append(f"*(Line {line_num}: Invalid JSON — {e})*")

    except FileNotFoundError:
        lines.append(f"Error: File not found")

    return "\n".join(lines)
```

**Pros**:
- Handles massive files (1GB+) efficiently
- No memory spike
- Streaming semantics preserved
- Good for logs, event streams, datasets

**Cons**:
- Requires understanding of JSONL semantics
- Output still accumulates in memory (need streaming writer for true streaming)
- Each line rendered independently

**When to use**: `.jsonl` files, streaming APIs, large datasets, logs

**Cost**: O(1) memory, O(n * m) time for n lines; limit preview to first N items

---

## Dependency Analysis

### Current State (from requirements.txt)

```
typer>=0.9.0
yt-dlp>=2023.11.14
pymupdf4llm>=0.2.0
ffmpeg (system)
```

### What's Already Available?

- **PyYAML**: NOT in 2md yet, but likely in system Python (universal pip install)
- **json**: Stdlib ✅
- **pandas**: Could use `pd.DataFrame.to_markdown()`, but adds 100MB+ dep

### Recommended Additions

**Minimal path** (no new deps):
```
# Just use stdlib json + manual YAML parsing if needed
```

**Slightly nicer** (lightweight):
```
PyYAML>=6.0  # Already ubiquitous; ~2 packages recommend it
```

**Avoid**:
- `yaml-to-markdown` — last updated 2021, limited scope
- `jsonschema2md` — for JSON Schema → docs, not generic JSON
- `json2md` — JavaScript lib, not Python
- `pandas` — overkill for simple table rendering

---

## Frontmatter Strategy

### Goal
Generate useful summary frontmatter for JSON/YAML → markdown files.

### Approach

```python
def build_json_frontmatter(filepath: str, data: dict | list, file_size: int) -> dict:
    """Extract metadata suitable for YAML frontmatter."""

    # Basic file info
    frontmatter = {
        "title": Path(filepath).stem.replace("_", " ").title(),
        "source_file": filepath,
        "source_type": "json" if filepath.endswith(".json") else "yaml",
        "fetched_at": datetime.now().isoformat(),
    }

    # Structure metadata
    if isinstance(data, dict):
        frontmatter["root_type"] = "object"
        frontmatter["top_level_keys"] = list(data.keys())[:20]  # First 20 keys
        frontmatter["key_count"] = len(data.keys())
        frontmatter["nesting_depth"] = _detect_depth(data)
    elif isinstance(data, list):
        frontmatter["root_type"] = "array"
        frontmatter["item_count"] = len(data)
        if data and isinstance(data[0], dict):
            frontmatter["item_schema"] = list(data[0].keys())[:10]
        frontmatter["nesting_depth"] = _detect_depth(data)

    # File size info
    frontmatter["file_size_kb"] = file_size / 1024
    if file_size > 1_000_000:
        frontmatter["warning"] = "Large file — may render as fenced code block"

    # Detect format hints
    if _looks_like_config(data):
        frontmatter["format_hint"] = "configuration"
    elif _looks_like_api_spec(data):
        frontmatter["format_hint"] = "openapi"
    elif _looks_like_dataset(data):
        frontmatter["format_hint"] = "tabular_data"

    return frontmatter

def _detect_depth(obj, current=0, max_depth=0):
    """Recursively compute max nesting depth."""
    if isinstance(obj, dict):
        if not obj:
            return current
        return max(_detect_depth(v, current + 1, max_depth) for v in obj.values())
    elif isinstance(obj, list):
        if not obj:
            return current
        return max(_detect_depth(item, current + 1, max_depth) for item in obj[:10])
    else:
        return current
```

### Decision Tree

```
File Size:
- < 5 KB      → All strategies OK, prefer structured extraction
- 5-100 KB    → Prefer table or structured extraction
- 100 KB-1 MB → Prefer fenced code block (with truncation)
- > 1 MB      → Fenced code block only, preview first N items

Type:
- Array of objects with consistent schema → Table
- Flat dict (config, metadata)              → Key-value list
- Deeply nested object                      → Fenced code or limit depth
- JSONL file                                → Streaming preview (first N items)
- Known format (OpenAPI, package.json)     → Special rendering

Truncation:
- Keys: Show first 20
- Array items: Show first 100 (or 10 for preview)
- String values: Truncate to 50 chars
- Nesting: Stop at depth 5
```

---

## Large File Handling

### Strategy: Chunking + Progressive Disclosure

```python
def json_to_markdown_smart(
    filepath: str,
    max_size_kb: int = 100,
    max_items: int = 100,
    max_depth: int = 5
) -> str:
    """Intelligently convert JSON/YAML to markdown, respecting size limits."""

    file_size = os.path.getsize(filepath)

    # 1. Load and parse
    data = load_json_or_yaml(filepath)

    # 2. Check file size
    if file_size > max_size_kb * 1024:
        # Too large: return fenced code block
        return f"""# {Path(filepath).stem}

**Note**: File is {file_size / 1024:.1f} KB (truncated for readability)

## Preview

{fenced_code_preview(data, lines=50)}

## Metadata

- **Type**: {type(data).__name__}
- **Size**: {file_size / 1024 / 1024:.1f} MB
- **Truncated**: Yes
"""

    # 3. Check structure complexity
    depth = _detect_depth(data)
    if depth > max_depth:
        # Too deep: switch to fenced code
        return f"""# {Path(filepath).stem}

**Note**: Data is deeply nested (depth {depth}), showing as code block.

{json_to_fenced(data)}
"""

    # 4. Try structured extraction
    if isinstance(data, dict) and len(data) < 50:
        return f"""# {Path(filepath).stem}

{dict_to_markdown(data)}
"""

    elif isinstance(data, list) and len(data) > 2:
        # Try table rendering
        table = array_to_markdown_table(data[:max_items])
        if table:
            return f"""# {Path(filepath).stem}

{table}
"""

    # 5. Fallback: fenced code
    return json_to_fenced(data)
```

---

## Implementation Roadmap for 2md

### Phase 1: Foundation (No deps change)
- [ ] Add `json2md.py` module with:
  - `json_to_fenced()` — always works
  - `dict_to_markdown()` — heading + k-v lists
  - `array_to_markdown_table()` — for tabular data
  - `build_json_frontmatter()` — metadata extraction
  - `json_to_markdown_smart()` — selector logic

### Phase 2: YAML Support (Add PyYAML if needed)
- [ ] `yaml_to_markdown()` wrappers
- [ ] YAML frontmatter detection
- [ ] Unified entry point: `data2md.py` or update `yt2md.py`

### Phase 3: Schema Detection (Optional)
- [ ] `detect_format()` heuristics
- [ ] Special renderers for OpenAPI, package.json, GeoJSON
- [ ] Config file detection

### Phase 4: JSONL Support
- [ ] `jsonl_to_markdown_stream()` for `.jsonl` files
- [ ] Integration with existing streaming pipeline

### Phase 5: Testing
- [ ] Unit tests for each renderer
- [ ] Edge cases: empty arrays, null values, special chars, unicode
- [ ] Large file tests (>100MB)

---

## Comparison Matrix

| Approach | No Deps | Speed | Readability | LLM-Friendly | Max Size |
|----------|---------|-------|-------------|--------------|----------|
| Fenced code | ✅ | ⚡⚡⚡ | ⭐⭐ | ⭐⭐⭐ | 1GB+ |
| Structured (k-v) | ✅ | ⚡⚡ | ⭐⭐⭐ | ⭐⭐ | 100KB |
| Table | ✅ | ⚡⚡ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 100 rows |
| Schema detection | ✅ | ⚡ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 1MB |
| JSONL streaming | ✅ | ⚡⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 1GB+ |

---

## References & Sources

### Libraries Evaluated
- **PyYAML** (https://pypi.org/project/PyYAML/) — De facto standard, widely available
- **ruamel.yaml** — Alternative, more features, same cost
- **yaml-to-markdown** (https://pypi.org/project/yaml-to-markdown/) — Unmaintained (last update 2021), limited
- **jsonschema2md** (https://pypi.org/project/jsonschema2md/) — JSON Schema only, not generic JSON
- **MarkItDown** (Microsoft, 2025) — For documents (DOCX, PDF), not JSON/YAML
- **pandas.DataFrame.to_markdown()** — Works but heavy dependency

### Standards & Formats
- **JSON Lines** (https://jsonlines.org/) — Streaming JSON format
- **YAML Front Matter** — Common in Jekyll, Obsidian, etc.
- **Markdown tables** — GitHub-Flavored Markdown (GFM)

### Use Cases Researched
- LLM context generation (what this toolkit needs)
- Configuration file documentation
- API specification rendering (OpenAPI)
- Data pipeline previews (Pandas + JSONL)
- Documentation migration (MarkItDown use case)

### Decision Sources
- Real Python: YAML in Python
- Stack Overflow: JSON to Markdown patterns
- GitHub: JSONL libraries + streaming patterns
- FastAPI docs: JSONL streaming in APIs
