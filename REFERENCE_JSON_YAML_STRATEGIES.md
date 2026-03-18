# Quick Reference: JSON/YAML to Markdown Strategies

## When to Use Each Strategy

### Fenced Code Block (`\`\`\`json ... \`\`\``)
✅ **Use when**:
- File > 100 KB
- Deeply nested (>5 levels)
- You want to preserve exact structure for LLMs
- Mixed types in arrays
- Special characters that markdown doesn't handle well

❌ **Don't use when**:
- You want human-readable structure
- Searching/grepping through output

**Code**:
```python
def json_to_fenced(data: dict | list, lang: str = "json") -> str:
    content = json.dumps(data, indent=2)
    return f"```{lang}\n{content}\n```"
```

---

### Structured Extraction (Headings + Key-Value Lists)
✅ **Use when**:
- File < 100 KB
- Mostly flat objects (depth 2-3)
- Config files, metadata, settings
- Want searchable headings

❌ **Don't use when**:
- Array of homogeneous objects (use table instead)
- More than 50 keys at root level

**Rendering**:
```
# Config.json

## Database
- **host**: localhost
- **port**: 5432
- **user**: postgres

## API
- **timeout**: 30
- **retries**: 3
```

**Code**:
```python
def dict_to_markdown(data: dict, level: int = 2) -> str:
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{'#' * level} {key}")
            lines.extend(dict_to_markdown(value, level + 1))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            # Handle nested array
            continue
        else:
            lines.append(f"- **{key}**: {value}")
    return "\n".join(lines)
```

---

### Markdown Table (Array of Objects)
✅ **Use when**:
- Array of objects
- All objects have same keys (or mostly)
- < 100 rows
- < 10 columns
- Values are simple (strings, numbers, booleans)

❌ **Don't use when**:
- Heterogeneous schema (objects have different keys)
- > 100 rows (gets unwieldy)
- Nested objects (render as fenced instead)
- Wide values (> 50 chars)

**Rendering**:
```
| Name | Role | Active |
| --- | --- | --- |
| Alice | Admin | true |
| Bob | User | false |
```

**Code**:
```python
def array_to_markdown_table(items: list[dict], max_rows: int = 100) -> str | None:
    if not items or not isinstance(items[0], dict):
        return None

    # Check schema consistency
    keys = list(items[0].keys())
    if any(set(item.keys()) != set(keys) for item in items[1:]):
        return None  # Inconsistent schema

    # Build table
    header = "| " + " | ".join(keys) + " |"
    separator = "|" + "|".join([" --- "] * len(keys)) + "|"

    rows = []
    for item in items[:max_rows]:
        values = [str(item.get(k, "")).replace("|", "\\|")[:50] for k in keys]
        rows.append("| " + " | ".join(values) + " |")

    md = header + "\n" + separator + "\n" + "\n".join(rows)
    if len(items) > max_rows:
        md += f"\n\n*(... {len(items) - max_rows} more rows)*"
    return md
```

---

### Schema Detection (Special Rendering for Known Formats)
✅ **Use when**:
- File is OpenAPI / Swagger spec
- File is package.json / pyproject.toml
- File is GeoJSON
- File follows known structure (app config, k8s manifest)

**Example: OpenAPI**
```python
def render_openapi(spec: dict) -> str:
    lines = ["# API Specification"]

    if "info" in spec:
        info = spec["info"]
        lines.append(f"**{info.get('title')}** v{info.get('version')}")

    if "paths" in spec:
        lines.append("\n## Endpoints\n")
        for path, methods in spec["paths"].items():
            for method in ["get", "post", "put", "delete", "patch"]:
                if method in methods:
                    details = methods[method]
                    summary = details.get("summary", "")
                    lines.append(f"- `{method.upper()} {path}`: {summary}")

    return "\n".join(lines)
```

**Benefits**:
- Extract actionable info (endpoints, dependencies, etc)
- Much smaller output than full spec
- Great for LLM context

---

### JSONL Streaming (Line-by-Line Processing)
✅ **Use when**:
- File is `.jsonl` (JSON Lines)
- File is > 100 MB
- Data is streaming (log file, event stream)
- Can't load entire file into memory

❌ **Don't use when**:
- File is regular `.json` (not newline-delimited)
- You need the full dataset in one view

**Code**:
```python
def jsonl_to_markdown(filepath: str, max_items: int = 100) -> str:
    lines = ["# JSON Lines Preview"]
    count = 0

    with open(filepath, "r") as f:
        for line_num, raw_line in enumerate(f, 1):
            if count >= max_items:
                lines.append(f"\n*(Showing first {max_items} of ~{line_num} items)*")
                break

            try:
                item = json.loads(raw_line.strip())
                lines.append(f"## Item {line_num}")
                if isinstance(item, dict):
                    for k, v in item.items():
                        lines.append(f"- **{k}**: {str(v)[:80]}")
                count += 1
            except json.JSONDecodeError:
                pass  # Skip invalid lines

    return "\n".join(lines)
```

---

## Decision Tree Pseudocode

```python
def json_to_markdown_smart(filepath: str, data: dict | list) -> str:
    file_size = os.path.getsize(filepath)

    # 1. Is this JSONL?
    if filepath.endswith(".jsonl"):
        return jsonl_to_markdown(filepath)

    # 2. Is file too large?
    if file_size > 1_000_000:  # 1 MB
        return json_to_fenced(data)

    # 3. Is data too deep?
    if _depth(data) > 5:
        return json_to_fenced(data)

    # 4. Is this a known format?
    if _looks_like_openapi(data):
        return render_openapi(data)
    if _looks_like_package_json(data):
        return render_package_json(data)

    # 5. Is this an array of consistent objects?
    if isinstance(data, list) and len(data) > 2:
        table = array_to_markdown_table(data)
        if table:
            return table

    # 6. Is this a flat object?
    if isinstance(data, dict) and len(data) < 50 and _depth(data) < 3:
        return dict_to_markdown(data)

    # 7. Fallback: fenced code
    return json_to_fenced(data)
```

---

## Frontmatter (Metadata)

Always include YAML frontmatter at top of markdown output, like yt2md.py:

```yaml
---
title: Configuration
source_file: config.json
source_type: json
root_type: object
key_count: 25
nesting_depth: 3
file_size_kb: 12.5
fetched_at: 2026-03-18T10:30:00
---
```

**Python code**:
```python
def build_data_frontmatter(filepath: str, data: dict | list, file_size: int) -> dict:
    return {
        "title": Path(filepath).stem.replace("_", " ").title(),
        "source_file": filepath,
        "source_type": "json" if filepath.endswith(".json") else "yaml",
        "root_type": "object" if isinstance(data, dict) else "array",
        "key_count": len(data.keys()) if isinstance(data, dict) else len(data),
        "nesting_depth": _detect_depth(data),
        "file_size_kb": file_size / 1024,
        "fetched_at": datetime.now().isoformat(),
    }
```

---

## Truncation Rules

### File Size
- < 5 KB: Use any strategy
- 5–100 KB: Structured extraction preferred
- 100 KB–1 MB: Fenced code block
- > 1 MB: Fenced code block + preview first N items

### Array Items
- Table: Show first 100 rows max
- Structured list: Show first 50 items
- JSONL preview: Show first 100 lines

### Object Keys
- Root object: Show all (or first 50 if huge)
- Nested objects: Show all
- Top-level keys in frontmatter: Show first 20

### String Values
- In tables: Truncate to 50 chars, add `…`
- In key-value lists: Show full (or 200 chars)
- In fenced code: No truncation (exact JSON)

### Nesting Depth
- Structured extraction: Stop at depth 5
- Fenced code: No limit (raw JSON)
- Tables: No nested objects/arrays (show `[object]` or `[array]`)

---

## Dependencies

### Required
- `json` (stdlib) ✅
- Nothing else

### Optional
- `PyYAML` (for YAML support)
  - Often already installed (~99% of Python envs)
  - If not: `pip install PyYAML`

### Don't Use
- `yaml-to-markdown` — unmaintained, limited
- `pandas` — overkill for simple tables
- `jsonschema2md` — JSON Schema only, not generic JSON

---

## Edge Cases

| Case | Strategy |
|------|----------|
| Empty dict `{}` | Show as `# (empty object)` |
| Empty array `[]` | Show as `# (empty array)` |
| `null` value | Show as `- **key**: null` |
| Very large string | Truncate in table, full in fenced |
| Mixed array types | Use fenced code block |
| Circular ref (N/A in JSON) | Not possible |
| Unicode/emoji | Preserve as-is |
| Pipes in strings | Escape as `\|` in tables |
| Newlines in strings | Show as `…` in tables, full in fenced |
| NaN / Infinity | Convert to string, show in fenced code |

---

## Template: Basic Implementation

```python
# data2md.py
import json
import typer
from pathlib import Path
from datetime import datetime

def json_to_fenced(data):
    content = json.dumps(data, indent=2)
    return f"```json\n{content}\n```"

def build_frontmatter(filepath, data, file_size):
    return {
        "title": Path(filepath).stem.title(),
        "source_file": filepath,
        "source_type": "json",
        "file_size_kb": file_size / 1024,
        "fetched_at": datetime.now().isoformat(),
    }

def markdown_to_file(output_path, frontmatter, content):
    fm_lines = ["---"]
    fm_lines.extend(f"{k}: {v}" for k, v in frontmatter.items())
    fm_lines.append("---")

    with open(output_path, "w") as f:
        f.write("\n".join(fm_lines))
        f.write("\n\n")
        f.write(content)

app = typer.Typer()

@app.command()
def convert(
    input_file: str = typer.Argument(..., help="JSON file to convert"),
    output_dir: str = typer.Option(".", help="Output directory"),
):
    with open(input_file) as f:
        data = json.load(f)

    file_size = Path(input_file).stat().st_size
    frontmatter = build_frontmatter(input_file, data, file_size)
    content = json_to_fenced(data)

    output_path = Path(output_dir) / f"{Path(input_file).stem}.md"
    markdown_to_file(output_path, frontmatter, content)

    print(f"✓ Converted to {output_path}")

if __name__ == "__main__":
    app()
```

---

## Performance Targets

All operations should complete in < 1 second for files up to 10 MB:

- Fenced code: O(n) — just serialize JSON
- Structured extraction: O(n log n) — traverse tree, build headings
- Table: O(m × n) — m rows, n columns
- JSONL preview: O(p) — process first p lines only

Use `tqdm` for progress on large files (>100 MB).

---

## Summary Table

| Input | Size | Output | Strategy |
|-------|------|--------|----------|
| `config.json` | 10 KB | Readable config | Structured |
| `data.jsonl` | 100 MB | Preview + count | JSONL stream |
| API response | 50 KB | Endpoints + schema | OpenAPI detection |
| Dataset | 500 KB | Sample table | Table rendering |
| Complex obj | 200 KB | Code block | Fenced |

**Always include frontmatter** with: title, source, type, size, fetched_at, key_count.
