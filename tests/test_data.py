#!/usr/bin/env python3
"""
test_data.py - Unit tests for data.py (JSON/YAML/JSONL → Markdown converter)

Tests cover:
- JSON array of objects → markdown table
- Flat JSON dict → key-value bullet list
- Nested JSON → fenced code block
- JSONL handling (line-by-line parsing)
- Large file truncation via max_items
- Frontmatter metadata fields
- Strategy selection logic
- Plain text output mode
- CLI interface
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from any2md.data import (
    choose_strategy,
    data_to_markdown,
    data_to_plain_text,
    detect_format,
    extract_data_metadata,
    parse_jsonl,
    process_data_file,
    render_key_value,
    render_table,
    render_code_block,
    _is_array_of_consistent_objects,
    _is_small_flat_dict,
    _nesting_depth,
)


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

ARRAY_OF_OBJECTS = [
    {"name": "Alice", "age": 30, "city": "New York"},
    {"name": "Bob",   "age": 25, "city": "London"},
    {"name": "Carol", "age": 35, "city": "Tokyo"},
]

FLAT_DICT = {
    "title": "My Config",
    "version": "1.0",
    "debug": False,
    "port": 8080,
}

NESTED_DICT = {
    "server": {
        "host": "localhost",
        "port": 8080,
        "tls": {"cert": "/etc/cert.pem", "key": "/etc/key.pem"},
    },
    "database": {"url": "postgres://...", "pool": {"min": 2, "max": 10}},
}

JSONL_LINES = '\n'.join([
    json.dumps({"id": 1, "value": "alpha"}),
    json.dumps({"id": 2, "value": "beta"}),
    json.dumps({"id": 3, "value": "gamma"}),
])

INCONSISTENT_ARRAY = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "score": 99},   # different keys
]


# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------

class TestDetectFormat(unittest.TestCase):
    def test_json(self):
        self.assertEqual(detect_format(Path("data.json")), "json")

    def test_jsonl(self):
        self.assertEqual(detect_format(Path("records.jsonl")), "jsonl")

    def test_yaml(self):
        self.assertEqual(detect_format(Path("config.yaml")), "yaml")

    def test_yml(self):
        self.assertEqual(detect_format(Path("config.yml")), "yaml")

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            detect_format(Path("data.csv"))

    def test_case_insensitive(self):
        self.assertEqual(detect_format(Path("DATA.JSON")), "json")


# ---------------------------------------------------------------------------
# parse_jsonl
# ---------------------------------------------------------------------------

class TestParseJsonl(unittest.TestCase):
    def test_parses_valid_jsonl(self):
        result = parse_jsonl(JSONL_LINES)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], {"id": 1, "value": "alpha"})
        self.assertEqual(result[2]["value"], "gamma")

    def test_skips_blank_lines(self):
        text = json.dumps({"a": 1}) + "\n\n" + json.dumps({"b": 2}) + "\n"
        result = parse_jsonl(text)
        self.assertEqual(len(result), 2)

    def test_invalid_jsonl_raises(self):
        with self.assertRaises(ValueError):
            parse_jsonl('{"ok": true}\nnot valid json\n{"also": true}')

    def test_empty_file_returns_empty_list(self):
        self.assertEqual(parse_jsonl(""), [])
        self.assertEqual(parse_jsonl("   \n\n  \n"), [])


# ---------------------------------------------------------------------------
# Strategy predicates
# ---------------------------------------------------------------------------

class TestStrategyPredicates(unittest.TestCase):
    def test_array_of_consistent_objects_true(self):
        self.assertTrue(_is_array_of_consistent_objects(ARRAY_OF_OBJECTS, 100))

    def test_array_of_consistent_objects_false_for_dict(self):
        self.assertFalse(_is_array_of_consistent_objects(FLAT_DICT, 100))

    def test_array_of_consistent_objects_false_for_empty(self):
        self.assertFalse(_is_array_of_consistent_objects([], 100))

    def test_array_of_consistent_objects_false_for_inconsistent(self):
        self.assertFalse(_is_array_of_consistent_objects(INCONSISTENT_ARRAY, 100))

    def test_array_of_consistent_objects_false_for_scalars(self):
        self.assertFalse(_is_array_of_consistent_objects([1, 2, 3], 100))

    def test_small_flat_dict_true(self):
        self.assertTrue(_is_small_flat_dict(FLAT_DICT))

    def test_small_flat_dict_false_nested(self):
        self.assertFalse(_is_small_flat_dict(NESTED_DICT))

    def test_small_flat_dict_false_for_list(self):
        self.assertFalse(_is_small_flat_dict(ARRAY_OF_OBJECTS))

    def test_small_flat_dict_false_for_large_dict(self):
        large = {str(i): i for i in range(25)}
        self.assertFalse(_is_small_flat_dict(large))


# ---------------------------------------------------------------------------
# choose_strategy
# ---------------------------------------------------------------------------

class TestChooseStrategy(unittest.TestCase):
    def test_array_of_objects_gives_table(self):
        self.assertEqual(choose_strategy(ARRAY_OF_OBJECTS, 100), 'table')

    def test_flat_dict_gives_key_value(self):
        self.assertEqual(choose_strategy(FLAT_DICT, 100), 'key_value')

    def test_nested_dict_gives_code_block(self):
        self.assertEqual(choose_strategy(NESTED_DICT, 100), 'code_block')

    def test_scalar_gives_code_block(self):
        self.assertEqual(choose_strategy(42, 100), 'code_block')
        self.assertEqual(choose_strategy("hello", 100), 'code_block')

    def test_inconsistent_array_gives_code_block(self):
        self.assertEqual(choose_strategy(INCONSISTENT_ARRAY, 100), 'code_block')


# ---------------------------------------------------------------------------
# render_table
# ---------------------------------------------------------------------------

class TestRenderTable(unittest.TestCase):
    def test_produces_table_headers(self):
        result = render_table(ARRAY_OF_OBJECTS, 100)
        self.assertIn('| name |', result)
        self.assertIn('| age |', result)
        self.assertIn('| city |', result)

    def test_produces_separator_row(self):
        result = render_table(ARRAY_OF_OBJECTS, 100)
        self.assertIn('| --- |', result)

    def test_contains_data(self):
        result = render_table(ARRAY_OF_OBJECTS, 100)
        self.assertIn('Alice', result)
        self.assertIn('Tokyo', result)

    def test_truncation_message_shown(self):
        result = render_table(ARRAY_OF_OBJECTS, max_items=2)
        self.assertIn('Showing 2 of 3', result)

    def test_no_truncation_message_when_under_limit(self):
        result = render_table(ARRAY_OF_OBJECTS, max_items=10)
        self.assertNotIn('Showing', result)

    def test_pipe_in_cell_value_escaped(self):
        data = [{"col": "a|b"}, {"col": "c"}]
        result = render_table(data, 100)
        self.assertIn('a\\|b', result)


# ---------------------------------------------------------------------------
# render_key_value
# ---------------------------------------------------------------------------

class TestRenderKeyValue(unittest.TestCase):
    def test_bullet_list_format(self):
        result = render_key_value(FLAT_DICT)
        self.assertIn('- **title**: My Config', result)
        self.assertIn('- **port**: 8080', result)

    def test_all_keys_present(self):
        result = render_key_value(FLAT_DICT)
        for key in FLAT_DICT:
            self.assertIn(f'**{key}**', result)


# ---------------------------------------------------------------------------
# render_code_block
# ---------------------------------------------------------------------------

class TestRenderCodeBlock(unittest.TestCase):
    def test_json_fence_for_json(self):
        result = render_code_block(NESTED_DICT, 'json')
        self.assertTrue(result.startswith('```json'))
        self.assertTrue(result.strip().endswith('```'))

    def test_contains_serialized_data(self):
        result = render_code_block(NESTED_DICT, 'json')
        self.assertIn('localhost', result)
        self.assertIn('postgres', result)

    def test_yaml_fence_for_yaml_format(self):
        # Only check for yaml fence if PyYAML is available
        try:
            import yaml  # noqa: F401
            result = render_code_block(FLAT_DICT, 'yaml')
            self.assertTrue(result.startswith('```yaml'))
        except ImportError:
            # Falls back to JSON rendering — just verify it works
            result = render_code_block(FLAT_DICT, 'yaml')
            self.assertIn('```', result)


# ---------------------------------------------------------------------------
# JSON array of objects → table (integration)
# ---------------------------------------------------------------------------

class TestJsonArrayToTable(unittest.TestCase):
    def _write_and_process(self, data, max_items=100, output_fmt='md'):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src = tmpdir_path / "data.json"
            src.write_text(json.dumps(data), encoding='utf-8')
            out_dir = tmpdir_path / "out"
            out_path = process_data_file(src, out_dir, output_fmt, max_items)
            return out_path.read_text(encoding='utf-8')

    def test_array_produces_table(self):
        content = self._write_and_process(ARRAY_OF_OBJECTS)
        self.assertIn('| name |', content)
        self.assertIn('Alice', content)

    def test_frontmatter_present(self):
        content = self._write_and_process(ARRAY_OF_OBJECTS)
        self.assertIn('---', content)
        self.assertIn('format: json', content)

    def test_top_level_type_array(self):
        content = self._write_and_process(ARRAY_OF_OBJECTS)
        self.assertIn('top_level_type: array', content)

    def test_item_count_in_frontmatter(self):
        content = self._write_and_process(ARRAY_OF_OBJECTS)
        self.assertIn('item_count: 3', content)


# ---------------------------------------------------------------------------
# Flat JSON dict → key-value list (integration)
# ---------------------------------------------------------------------------

class TestFlatDictToKeyValue(unittest.TestCase):
    def _process(self, data):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "cfg.json"
            src.write_text(json.dumps(data), encoding='utf-8')
            out_dir = Path(tmpdir) / "out"
            out_path = process_data_file(src, out_dir, 'md', 100)
            return out_path.read_text(encoding='utf-8')

    def test_flat_dict_produces_key_value(self):
        content = self._process(FLAT_DICT)
        self.assertIn('**title**', content)
        self.assertIn('My Config', content)
        # Should NOT be a table
        self.assertNotIn('| title |', content)

    def test_top_level_type_object(self):
        content = self._process(FLAT_DICT)
        self.assertIn('top_level_type: object', content)

    def test_key_count_in_frontmatter(self):
        content = self._process(FLAT_DICT)
        self.assertIn(f'key_count: {len(FLAT_DICT)}', content)


# ---------------------------------------------------------------------------
# Nested JSON → fenced code block (integration)
# ---------------------------------------------------------------------------

class TestNestedJsonToCodeBlock(unittest.TestCase):
    def _process(self, data):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "nested.json"
            src.write_text(json.dumps(data), encoding='utf-8')
            out_dir = Path(tmpdir) / "out"
            out_path = process_data_file(src, out_dir, 'md', 100)
            return out_path.read_text(encoding='utf-8')

    def test_nested_dict_produces_code_block(self):
        content = self._process(NESTED_DICT)
        self.assertIn('```json', content)
        self.assertIn('localhost', content)

    def test_nesting_depth_in_frontmatter(self):
        content = self._process(NESTED_DICT)
        # NESTED_DICT has depth 3 (root → server/database → tls → cert)
        self.assertIn('nesting_depth:', content)


# ---------------------------------------------------------------------------
# JSONL handling
# ---------------------------------------------------------------------------

class TestJsonlHandling(unittest.TestCase):
    def _process_jsonl(self, text, max_items=100):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "records.jsonl"
            src.write_text(text, encoding='utf-8')
            out_dir = Path(tmpdir) / "out"
            out_path = process_data_file(src, out_dir, 'md', max_items)
            return out_path.read_text(encoding='utf-8')

    def test_jsonl_format_in_frontmatter(self):
        content = self._process_jsonl(JSONL_LINES)
        self.assertIn('format: jsonl', content)

    def test_jsonl_parsed_as_array(self):
        content = self._process_jsonl(JSONL_LINES)
        # Consistent objects → table
        self.assertIn('| id |', content)
        self.assertIn('alpha', content)

    def test_jsonl_item_count(self):
        content = self._process_jsonl(JSONL_LINES)
        self.assertIn('item_count: 3', content)

    def test_jsonl_output_file_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "records.jsonl"
            src.write_text(JSONL_LINES, encoding='utf-8')
            out_dir = Path(tmpdir) / "out"
            out_path = process_data_file(src, out_dir, 'md', 100)
            self.assertEqual(out_path.name, 'records.md')


# ---------------------------------------------------------------------------
# Large file truncation
# ---------------------------------------------------------------------------

class TestTruncation(unittest.TestCase):
    def _make_large_array(self, n: int):
        return [{"id": i, "name": f"item_{i}"} for i in range(n)]

    def test_truncation_message_in_table(self):
        data = self._make_large_array(200)
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "big.json"
            src.write_text(json.dumps(data), encoding='utf-8')
            out_dir = Path(tmpdir) / "out"
            out_path = process_data_file(src, out_dir, 'md', max_items=50)
            content = out_path.read_text(encoding='utf-8')
        self.assertIn('Showing 50 of 200', content)

    def test_no_truncation_when_under_limit(self):
        data = self._make_large_array(10)
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "small.json"
            src.write_text(json.dumps(data), encoding='utf-8')
            out_dir = Path(tmpdir) / "out"
            out_path = process_data_file(src, out_dir, 'md', max_items=100)
            content = out_path.read_text(encoding='utf-8')
        self.assertNotIn('Showing', content)

    def test_default_max_items_100(self):
        """Default max_items is 100 — 150-item array should be truncated."""
        data = self._make_large_array(150)
        result = render_table(data, max_items=100)
        self.assertIn('Showing 100 of 150', result)


# ---------------------------------------------------------------------------
# Frontmatter fields
# ---------------------------------------------------------------------------

class TestFrontmatter(unittest.TestCase):
    def _meta(self, data, fmt='json'):
        raw = json.dumps(data)
        with tempfile.NamedTemporaryFile(suffix=f'.{fmt}', delete=False) as f:
            path = Path(f.name)
        try:
            path.write_text(raw, encoding='utf-8')
            return extract_data_metadata(path, data, raw, fmt)
        finally:
            path.unlink(missing_ok=True)

    def test_fetched_at_present_and_parseable(self):
        from datetime import datetime
        meta = self._meta(FLAT_DICT)
        self.assertIn('fetched_at', meta)
        datetime.strptime(meta['fetched_at'], '%Y-%m-%dT%H:%M:%SZ')

    def test_source_is_absolute(self):
        meta = self._meta(FLAT_DICT)
        self.assertTrue(Path(meta['source']).is_absolute())

    def test_format_field(self):
        meta = self._meta(ARRAY_OF_OBJECTS, fmt='json')
        self.assertEqual(meta['format'], 'json')

    def test_file_size_positive(self):
        meta = self._meta(FLAT_DICT)
        self.assertGreater(meta['file_size'], 0)

    def test_top_level_type_object(self):
        meta = self._meta(FLAT_DICT)
        self.assertEqual(meta['top_level_type'], 'object')
        self.assertIn('key_count', meta)
        self.assertNotIn('item_count', meta)

    def test_top_level_type_array(self):
        meta = self._meta(ARRAY_OF_OBJECTS)
        self.assertEqual(meta['top_level_type'], 'array')
        self.assertIn('item_count', meta)
        self.assertNotIn('key_count', meta)

    def test_nesting_depth_flat(self):
        meta = self._meta(FLAT_DICT)
        self.assertEqual(meta['nesting_depth'], 1)

    def test_nesting_depth_nested(self):
        meta = self._meta(NESTED_DICT)
        self.assertGreaterEqual(meta['nesting_depth'], 3)


# ---------------------------------------------------------------------------
# _nesting_depth
# ---------------------------------------------------------------------------

class TestNestingDepth(unittest.TestCase):
    def test_scalar(self):
        self.assertEqual(_nesting_depth(42), 0)

    def test_flat_dict(self):
        self.assertEqual(_nesting_depth({"a": 1, "b": 2}), 1)

    def test_flat_list(self):
        self.assertEqual(_nesting_depth([1, 2, 3]), 1)

    def test_nested_two_levels(self):
        self.assertEqual(_nesting_depth({"a": {"b": 1}}), 2)

    def test_nested_three_levels(self):
        self.assertEqual(_nesting_depth({"a": {"b": {"c": 1}}}), 3)


# ---------------------------------------------------------------------------
# Plain text output
# ---------------------------------------------------------------------------

class TestPlainTextOutput(unittest.TestCase):
    def test_table_data_becomes_tsv(self):
        result = data_to_plain_text(ARRAY_OF_OBJECTS, 'json', 100)
        self.assertIn('\t', result)
        self.assertIn('name', result)
        self.assertNotIn('|', result)

    def test_flat_dict_becomes_key_colon_value(self):
        result = data_to_plain_text(FLAT_DICT, 'json', 100)
        self.assertIn('title: My Config', result)
        self.assertNotIn('**', result)

    def test_nested_dict_becomes_json_text(self):
        result = data_to_plain_text(NESTED_DICT, 'json', 100)
        self.assertIn('localhost', result)
        self.assertNotIn('```', result)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    def test_help_exits_cleanly(self):
        from typer.testing import CliRunner
        from any2md.data import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("json", result.output.lower())

    def test_missing_file_exits_with_error(self):
        from typer.testing import CliRunner
        from any2md.data import app

        runner = CliRunner()
        result = runner.invoke(app, ["/nonexistent/data.json"])
        self.assertNotEqual(result.exit_code, 0)

    def test_single_json_file_end_to_end(self):
        from typer.testing import CliRunner
        from any2md.data import app

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src = tmpdir_path / "data.json"
            src.write_text(json.dumps(ARRAY_OF_OBJECTS), encoding='utf-8')
            out_dir = tmpdir_path / "out"

            runner = CliRunner()
            result = runner.invoke(app, [str(src), "-o", str(out_dir)])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            out_file = out_dir / "data.md"
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding='utf-8')
            self.assertIn('---', content)
            self.assertIn('Alice', content)

    def test_txt_format_flag(self):
        from typer.testing import CliRunner
        from any2md.data import app

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src = tmpdir_path / "data.json"
            src.write_text(json.dumps(FLAT_DICT), encoding='utf-8')
            out_dir = tmpdir_path / "out"

            runner = CliRunner()
            result = runner.invoke(app, [str(src), "-o", str(out_dir), "-f", "txt"])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            out_file = out_dir / "data.txt"
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding='utf-8')
            self.assertNotIn('fetched_at:', content)
            self.assertIn('title', content)

    def test_max_items_flag(self):
        from typer.testing import CliRunner
        from any2md.data import app

        data = [{"id": i, "val": f"v{i}"} for i in range(200)]
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src = tmpdir_path / "big.json"
            src.write_text(json.dumps(data), encoding='utf-8')
            out_dir = tmpdir_path / "out"

            runner = CliRunner()
            result = runner.invoke(app, [str(src), "-o", str(out_dir), "--max-items", "25"])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            content = (out_dir / "big.md").read_text(encoding='utf-8')
            self.assertIn('Showing 25 of 200', content)

    def test_directory_input_exits_with_error(self):
        from typer.testing import CliRunner
        from any2md.data import app

        with tempfile.TemporaryDirectory() as tmpdir:
            runner = CliRunner()
            result = runner.invoke(app, [tmpdir])
            self.assertNotEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
