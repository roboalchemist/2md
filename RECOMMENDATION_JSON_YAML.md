# Recommendation: JSON/YAML to Markdown for 2md

## TL;DR

**Implement a multi-strategy converter with NO new dependencies:**

1. **Default**: Fenced code block (always works, good for LLM context)
2. **If file < 100 KB & schema is simple**: Structured extraction (headings + key-value lists)
3. **If array of objects with consistent schema**: Markdown table
4. **If known format (OpenAPI, package.json)**: Special rendering
5. **If JSONL**: Stream-process line by line

## Why This Approach

### For Your Use Case (LLM Context)
- Fenced code blocks are **actually excellent** for LLM consumption (exact structure preserved)
- Structured markdown is nice for **human preview**, but not required for LLMs
- **No new dependencies needed** — use stdlib `json` + optional `PyYAML` (likely already present)

### Dependencies
- `PyYAML` — Only if you want YAML support. Ubiquitous (~99% of Python envs have it)
- **Avoid**: `yaml-to-markdown` (unmaintained), `jsonschema2md` (too specific)

### Existing Tools Don't Fit
- **MarkItDown** (Microsoft) — Great for DOCX/PDF/HTML, not JSON/YAML
- **json2md** — JavaScript only
- **jsonschema2md** — Only for JSON Schema → docs, not generic JSON

---

## Decision Logic

```
1. Is this a .jsonl file?
   → Use JSONL streaming (process line-by-line, limit preview to 100 items)

2. Is file > 1 MB?
   → Fenced code block only (with file size warning)

3. Does data look like OpenAPI / package.json / GeoJSON?
   → Use special renderer (if you implement schema detection)

4. Is it an array of objects with consistent schema?
   → Try markdown table (if < 100 rows, < 10 columns)

5. Is it a flat dict with < 50 keys?
   → Structured extraction (headings + key-value lists)

6. Otherwise?
   → Fenced code block (safe fallback)
```

---

## What to Add (In Order of Priority)

### Priority 1: Fenced Code Block (Boring but Necessary)
```python
def json_to_fenced(data: dict | list) -> str:
    """Wrap JSON in fenced code block."""
    content = json.dumps(data, indent=2)
    return f"```json\n{content}\n```"

def yaml_to_fenced(yaml_string: str) -> str:
    """Wrap YAML in fenced code block."""
    return f"```yaml\n{yaml_string}\n```"
```

**Why**: Always works. 80% of your use cases solved.

---

### Priority 2: Frontmatter Generation
```python
def build_data_frontmatter(filepath: str, data: dict | list, file_size: int) -> dict:
    """Extract metadata for YAML frontmatter."""
    return {
        "title": Path(filepath).stem.replace("_", " ").title(),
        "source_file": filepath,
        "source_type": "json" if filepath.endswith(".json") else "yaml",
        "root_type": "object" if isinstance(data, dict) else "array",
        "key_count": len(data.keys()) if isinstance(data, dict) else len(data),
        "fetched_at": datetime.now().isoformat(),
        "file_size_kb": file_size / 1024,
    }
```

**Why**: Makes output consistent with yt2md.py and pdf2md.py (uses same `build_frontmatter` pattern)

---

### Priority 3: Structured Extraction (Optional but Nice)
```python
def dict_to_markdown(data: dict, level: int = 2, max_depth: int = 5) -> str:
    """Convert dict to headings + key-value lists, respecting depth limit."""
    # (See full implementation in research doc)
    # Renders as:
    # ## Key 1
    # - **subkey**: value
    # ## Key 2
    # - etc
```

**Why**: Makes config files + metadata readable. Small code size.

---

### Priority 4: Table Rendering (Optional)
```python
def array_to_markdown_table(items: list[dict], max_rows: int = 100) -> str | None:
    """Convert array of dicts to markdown table, or None if schema too loose."""
    # (See full implementation in research doc)
    # Validates schema consistency, escapes pipes, truncates wide columns
```

**Why**: Makes CSV-like data scannable. Important for datasets.

---

### Priority 5: JSONL Streaming (Later Phase)
```python
def jsonl_to_markdown(filepath: str, max_items: int = 100) -> str:
    """Process .jsonl without loading entire file into memory."""
    # (See full implementation in research doc)
```

**Why**: Essential if you want to support log files, streaming APIs, 1GB+ datasets.

---

## Integration Points

### Where to Add This Code
1. **New file**: `json2md.py` (parallel to pdf2md.py, yt2md.py)
   - Or: Create `data2md.py` as parent module for both JSON and YAML

2. **API**: Unified entry point
   ```python
   def data_to_markdown(
       filepath: str,
       format: Literal["json", "yaml"] = "json",
       output_dir: str = ".",
       fancy: bool = True  # Use tables + structured extraction
   ) -> str:
       """Convert JSON/YAML to markdown."""
       # Auto-detect type, decide strategy, return markdown string
   ```

3. **CLI**: Follow yt2md/pdf2md pattern
   ```bash
   python data2md.py config.json -f json -o output.md
   python data2md.py data.yaml -f yaml -o output.md
   ```

### Reuse from Existing Code
- Use `build_frontmatter()` from yt2md.py (or adapt for data files)
- Use `OutputFormat` enum pattern (md, txt)
- Use typer CLI structure
- Use tqdm for progress on large files

---

## Key Design Decisions

### 1. No New Hard Dependencies
- Use `PyYAML` only if user wants YAML support
- Graceful fallback if PyYAML not installed (just treat YAML as text)

### 2. Size Limits Are Smart, Not Aggressive
- **Fenced code**: Switch at > 100 KB
- **Structured extraction**: Cap at depth 5
- **Table rows**: Preview first 100
- **Array items**: Show first 100 in structured output

### 3. Frontmatter for All Output
- Consistent with your existing pattern (yt2md, pdf2md)
- Include file size, type, row count, nesting depth
- Helps downstream processors (e.g., "large file, rendered as code block")

### 4. Streaming for JSONL
- Don't load entire file into memory
- Process line-by-line, render each as separate section or row
- Include metadata: "Showing first 100 of 50,000 lines"

### 5. Schema Detection is Nice-to-Have, Not Required
- Start without it (Priorities 1–4 don't need it)
- Add later if users ask for OpenAPI/package.json special handling
- Use simple heuristics (regex on keys, not full ML parsing)

---

## Edge Cases to Handle

```python
# Empty structures
{} → "# (empty object)"
[] → "# (empty array)"

# Null/None values
{"key": null} → "- **key**: null" or "- **key**: (null)"

# Special characters
{"key": "value|with|pipes"} → Escape pipes in tables
{"key": "multi\nline"} → Use inline code or truncate

# Unicode/emoji
{"name": "🚀 Rocket"} → Preserve as-is

# Very large strings
{"description": "1MB of text"} → Truncate in tables, show full in fenced

# Circular references
(Not possible in JSON, but check for deeply nested structures)

# Mixed types in arrays
[1, "string", {"obj": "ect"}] → Can't make table, render as fenced code
```

---

## Testing Strategy

### Unit Tests
```python
# test_data2md.py
def test_json_to_fenced():
    data = {"name": "Alice", "age": 30}
    result = json_to_fenced(data)
    assert "```json" in result
    assert "Alice" in result

def test_dict_to_markdown_flat():
    data = {"title": "My Config", "debug": True}
    result = dict_to_markdown(data)
    assert "# My Config" in result or "title" in result

def test_array_to_table():
    data = [
        {"name": "Alice", "role": "admin"},
        {"name": "Bob", "role": "user"}
    ]
    result = array_to_markdown_table(data)
    assert "Alice" in result
    assert "|" in result  # Markdown table

def test_frontmatter_generation():
    data = {"key": "value"}
    fm = build_data_frontmatter("test.json", data, 1024)
    assert fm["source_type"] == "json"
    assert fm["fetched_at"]
```

### Integration Tests
```python
# Convert real-world files
- OpenAPI spec (3000 lines)
- package.json
- Terraform vars file (YAML)
- Large JSONL (10MB)
```

---

## Performance Expectations

| File Size | Strategy | Time | Memory |
|-----------|----------|------|--------|
| < 1 KB | Any | <1ms | <1MB |
| 1–100 KB | Structured | ~10ms | ~5MB |
| 100 KB–1 MB | Fenced code | ~50ms | ~10MB |
| 1–100 MB | Fenced + preview | ~100ms | ~20MB |
| 100MB+ | JSONL streaming | ~500ms (first 100 items) | <50MB |

All approaches should stay **well under 1 second** for files up to 10MB.

---

## Summary: Three Lines to Implement

1. **Fenced code** (5 lines of code) — Done, covers 80% of use cases
2. **Structured extraction** (30 lines) — Makes config files readable
3. **Table rendering** (40 lines) — Makes datasets scannable

**Total**: ~75 lines of code, zero new dependencies, integrates with existing yt2md/pdf2md patterns.
