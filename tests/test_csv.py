#!/usr/bin/env python3
"""
test_csv.py - Unit tests for any2md/csv.py

Tests cover:
- detect_delimiter: CSV vs TSV vs semicolon-separated sniffing
- parse_csv: header/row splitting, empty input
- sanitize_cell: pipe escaping, newline collapsing, truncation
- prepare_table: row truncation, column padding/trimming
- extract_csv_metadata: field presence and types
- table_to_markdown: pipe table format, separator row, truncation notice
- table_to_plain_text: aligned columns, no pipes
- rows_to_full_markdown: frontmatter assembly
- process_csv_file: file I/O (md and txt), empty file, output path
- CLI: help, single file, directory batch, missing file
"""

import tempfile
import unittest
from pathlib import Path

from any2md.csv import (
    detect_delimiter,
    parse_csv,
    sanitize_cell,
    prepare_table,
    extract_csv_metadata,
    table_to_markdown,
    table_to_plain_text,
    rows_to_full_markdown,
    process_csv_file,
    DEFAULT_MAX_ROWS,
    DEFAULT_MAX_COL_WIDTH,
)


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_CSV = "name,age,city\nAlice,30,New York\nBob,25,London\nCarol,35,Paris\n"
SAMPLE_TSV = "name\tage\tcity\nAlice\t30\tNew York\nBob\t25\tLondon\n"
SAMPLE_SEMICOLON = "name;age;city\nAlice;30;Berlin\n"
PIPE_CSV = 'a,b,c\n"val|ue",plain,"multi\nline"\n'
EMPTY_CSV = ""
HEADER_ONLY_CSV = "col1,col2,col3\n"


# ---------------------------------------------------------------------------
# detect_delimiter
# ---------------------------------------------------------------------------

class TestDetectDelimiter(unittest.TestCase):
    def test_detects_comma(self):
        self.assertEqual(detect_delimiter(SAMPLE_CSV), ',')

    def test_detects_tab(self):
        self.assertEqual(detect_delimiter(SAMPLE_TSV), '\t')

    def test_detects_semicolon(self):
        self.assertEqual(detect_delimiter(SAMPLE_SEMICOLON), ';')

    def test_fallback_to_comma_on_single_column(self):
        # Single-column file has no delimiter to sniff
        result = detect_delimiter("just_a_header\nvalue1\nvalue2\n")
        # Must return a string (comma fallback or any valid delimiter)
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 1)

    def test_tsv_file_content(self):
        tsv = "col1\tcol2\tcol3\n1\t2\t3\n4\t5\t6\n"
        self.assertEqual(detect_delimiter(tsv), '\t')


# ---------------------------------------------------------------------------
# parse_csv
# ---------------------------------------------------------------------------

class TestParseCsv(unittest.TestCase):
    def test_csv_headers_and_rows(self):
        headers, rows = parse_csv(SAMPLE_CSV, ',')
        self.assertEqual(headers, ['name', 'age', 'city'])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0], ['Alice', '30', 'New York'])

    def test_tsv_headers_and_rows(self):
        headers, rows = parse_csv(SAMPLE_TSV, '\t')
        self.assertEqual(headers, ['name', 'age', 'city'])
        self.assertEqual(len(rows), 2)

    def test_empty_content_returns_empty(self):
        headers, rows = parse_csv('', ',')
        self.assertEqual(headers, [])
        self.assertEqual(rows, [])

    def test_header_only_returns_no_rows(self):
        headers, rows = parse_csv(HEADER_ONLY_CSV, ',')
        self.assertEqual(headers, ['col1', 'col2', 'col3'])
        self.assertEqual(rows, [])

    def test_quoted_fields_with_commas(self):
        content = 'a,b\n"hello, world",42\n'
        headers, rows = parse_csv(content, ',')
        self.assertEqual(rows[0][0], 'hello, world')


# ---------------------------------------------------------------------------
# sanitize_cell
# ---------------------------------------------------------------------------

class TestSanitizeCell(unittest.TestCase):
    def test_pipe_escaped(self):
        result = sanitize_cell('val|ue', 80)
        self.assertEqual(result, r'val\|ue')

    def test_newline_replaced_with_space(self):
        result = sanitize_cell('multi\nline', 80)
        self.assertNotIn('\n', result)
        self.assertIn(' ', result)

    def test_crlf_replaced_with_space(self):
        result = sanitize_cell('line1\r\nline2', 80)
        self.assertNotIn('\r', result)
        self.assertNotIn('\n', result)

    def test_truncation_at_max_width(self):
        long_val = 'x' * 100
        result = sanitize_cell(long_val, 20)
        self.assertEqual(len(result), 20)
        self.assertTrue(result.endswith('\u2026'))

    def test_no_truncation_within_limit(self):
        val = 'short'
        result = sanitize_cell(val, 80)
        self.assertEqual(result, 'short')

    def test_empty_cell(self):
        result = sanitize_cell('', 80)
        self.assertEqual(result, '')

    def test_multiple_pipes(self):
        result = sanitize_cell('a|b|c', 80)
        self.assertEqual(result, r'a\|b\|c')


# ---------------------------------------------------------------------------
# prepare_table
# ---------------------------------------------------------------------------

class TestPrepareTable(unittest.TestCase):
    def _headers(self):
        return ['name', 'age', 'city']

    def _rows(self, n=5):
        return [[f'name{i}', str(i), f'city{i}'] for i in range(n)]

    def test_no_truncation_when_under_limit(self):
        _, san_rows, truncated = prepare_table(self._headers(), self._rows(3), max_rows=10, max_col_width=80)
        self.assertFalse(truncated)
        self.assertEqual(len(san_rows), 3)

    def test_truncation_when_over_limit(self):
        _, san_rows, truncated = prepare_table(self._headers(), self._rows(10), max_rows=5, max_col_width=80)
        self.assertTrue(truncated)
        self.assertEqual(len(san_rows), 5)

    def test_short_rows_padded(self):
        headers = ['a', 'b', 'c']
        rows = [['only_one']]
        _, san_rows, _ = prepare_table(headers, rows, max_rows=10, max_col_width=80)
        self.assertEqual(len(san_rows[0]), 3)
        self.assertEqual(san_rows[0][1], '')

    def test_long_rows_trimmed(self):
        headers = ['a', 'b']
        rows = [['1', '2', '3', '4']]
        _, san_rows, _ = prepare_table(headers, rows, max_rows=10, max_col_width=80)
        self.assertEqual(len(san_rows[0]), 2)

    def test_cells_sanitized(self):
        headers = ['col']
        rows = [['pipe|here']]
        _, san_rows, _ = prepare_table(headers, rows, max_rows=10, max_col_width=80)
        self.assertIn(r'\|', san_rows[0][0])


# ---------------------------------------------------------------------------
# extract_csv_metadata
# ---------------------------------------------------------------------------

class TestExtractCsvMetadata(unittest.TestCase):
    def _make_file(self, content: str) -> Path:
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
            f.write(content)
            return Path(f.name)

    def test_metadata_fields_present(self):
        path = self._make_file(SAMPLE_CSV)
        try:
            headers, rows = parse_csv(SAMPLE_CSV, ',')
            meta = extract_csv_metadata(path, headers, rows, ',')
            for field in ('rows', 'columns', 'column_names', 'delimiter', 'file_size', 'source', 'fetched_at'):
                self.assertIn(field, meta)
        finally:
            path.unlink(missing_ok=True)

    def test_row_count_correct(self):
        path = self._make_file(SAMPLE_CSV)
        try:
            headers, rows = parse_csv(SAMPLE_CSV, ',')
            meta = extract_csv_metadata(path, headers, rows, ',')
            self.assertEqual(meta['rows'], 3)
        finally:
            path.unlink(missing_ok=True)

    def test_column_count_correct(self):
        path = self._make_file(SAMPLE_CSV)
        try:
            headers, rows = parse_csv(SAMPLE_CSV, ',')
            meta = extract_csv_metadata(path, headers, rows, ',')
            self.assertEqual(meta['columns'], 3)
        finally:
            path.unlink(missing_ok=True)

    def test_delimiter_name_comma(self):
        path = self._make_file(SAMPLE_CSV)
        try:
            headers, rows = parse_csv(SAMPLE_CSV, ',')
            meta = extract_csv_metadata(path, headers, rows, ',')
            self.assertEqual(meta['delimiter'], 'comma')
        finally:
            path.unlink(missing_ok=True)

    def test_delimiter_name_tab(self):
        path = self._make_file(SAMPLE_TSV)
        try:
            headers, rows = parse_csv(SAMPLE_TSV, '\t')
            meta = extract_csv_metadata(path, headers, rows, '\t')
            self.assertEqual(meta['delimiter'], 'tab')
        finally:
            path.unlink(missing_ok=True)

    def test_column_names_list(self):
        path = self._make_file(SAMPLE_CSV)
        try:
            headers, rows = parse_csv(SAMPLE_CSV, ',')
            meta = extract_csv_metadata(path, headers, rows, ',')
            self.assertEqual(meta['column_names'], ['name', 'age', 'city'])
        finally:
            path.unlink(missing_ok=True)

    def test_source_is_absolute(self):
        path = self._make_file(SAMPLE_CSV)
        try:
            headers, rows = parse_csv(SAMPLE_CSV, ',')
            meta = extract_csv_metadata(path, headers, rows, ',')
            self.assertTrue(Path(meta['source']).is_absolute())
        finally:
            path.unlink(missing_ok=True)

    def test_fetched_at_iso8601(self):
        path = self._make_file(SAMPLE_CSV)
        try:
            from datetime import datetime
            headers, rows = parse_csv(SAMPLE_CSV, ',')
            meta = extract_csv_metadata(path, headers, rows, ',')
            datetime.strptime(meta['fetched_at'], '%Y-%m-%dT%H:%M:%SZ')
        finally:
            path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# table_to_markdown
# ---------------------------------------------------------------------------

class TestTableToMarkdown(unittest.TestCase):
    def test_pipe_table_structure(self):
        headers = ['Name', 'Age']
        rows = [['Alice', '30'], ['Bob', '25']]
        result = table_to_markdown(headers, rows)
        lines = result.split('\n')
        # Header row
        self.assertTrue(lines[0].startswith('|'))
        self.assertTrue(lines[0].endswith('|'))
        # Separator row
        self.assertIn('---', lines[1])
        # Data rows
        self.assertTrue(lines[2].startswith('|'))

    def test_header_appears_in_output(self):
        headers = ['col1', 'col2']
        rows = [['a', 'b']]
        result = table_to_markdown(headers, rows)
        self.assertIn('col1', result)
        self.assertIn('col2', result)

    def test_data_appears_in_output(self):
        headers = ['x']
        rows = [['hello']]
        result = table_to_markdown(headers, rows)
        self.assertIn('hello', result)

    def test_truncation_notice_included(self):
        headers = ['a']
        rows = [['1']]
        result = table_to_markdown(headers, rows, truncated=True, total_rows=500)
        self.assertIn('truncated', result.lower())
        self.assertIn('500', result)

    def test_no_truncation_notice_when_not_truncated(self):
        headers = ['a']
        rows = [['1']]
        result = table_to_markdown(headers, rows, truncated=False)
        self.assertNotIn('truncated', result.lower())

    def test_empty_headers_returns_empty_string(self):
        result = table_to_markdown([], [])
        self.assertEqual(result, '')

    def test_pipe_escaped_in_cell(self):
        headers = ['val']
        rows = [[r'has\|pipe']]
        result = table_to_markdown(headers, rows)
        self.assertIn(r'has\|pipe', result)


# ---------------------------------------------------------------------------
# table_to_plain_text
# ---------------------------------------------------------------------------

class TestTableToPlainText(unittest.TestCase):
    def test_no_pipe_chars_in_output(self):
        headers = ['Name', 'Age']
        rows = [['Alice', '30']]
        result = table_to_plain_text(headers, rows)
        # Plain text format should not have leading pipe
        self.assertFalse(result.startswith('|'))

    def test_header_appears(self):
        headers = ['col1', 'col2']
        rows = [['a', 'b']]
        result = table_to_plain_text(headers, rows)
        self.assertIn('col1', result)

    def test_separator_line_present(self):
        headers = ['Name']
        rows = [['Alice']]
        result = table_to_plain_text(headers, rows)
        lines = result.split('\n')
        # Second line should be dashes
        self.assertRegex(lines[1], r'^-+')

    def test_truncation_notice_included(self):
        headers = ['a']
        rows = [['1']]
        result = table_to_plain_text(headers, rows, truncated=True, total_rows=1000)
        self.assertIn('truncated', result.lower())

    def test_empty_headers_returns_empty_string(self):
        result = table_to_plain_text([], [])
        self.assertEqual(result, '')


# ---------------------------------------------------------------------------
# rows_to_full_markdown
# ---------------------------------------------------------------------------

class TestRowsToFullMarkdown(unittest.TestCase):
    def test_includes_frontmatter_when_metadata_given(self):
        table_md = '| a | b |\n| --- | --- |\n| 1 | 2 |'
        meta = {'rows': 1, 'columns': 2, 'source': '/tmp/test.csv',
                 'fetched_at': '2026-03-18T00:00:00Z', 'delimiter': 'comma',
                 'file_size': 42, 'column_names': ['a', 'b']}
        result = rows_to_full_markdown(table_md, metadata=meta)
        self.assertIn('---', result)
        self.assertIn('rows:', result)
        self.assertIn('| a |', result)

    def test_no_frontmatter_when_no_metadata(self):
        table_md = '| a |\n| --- |\n| 1 |'
        result = rows_to_full_markdown(table_md, metadata=None)
        # YAML frontmatter block starts with '---\n' on its own line; table separators
        # like '| --- |' are not YAML delimiters. Verify no standalone --- line at top.
        self.assertFalse(result.startswith('---'), "Result should not start with YAML frontmatter delimiter")
        self.assertIn('| a |', result)


# ---------------------------------------------------------------------------
# process_csv_file (integration)
# ---------------------------------------------------------------------------

class TestProcessCsvFile(unittest.TestCase):
    def test_creates_md_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            csv_path = tmpdir_path / 'data.csv'
            csv_path.write_text(SAMPLE_CSV, encoding='utf-8')
            out_dir = tmpdir_path / 'out'

            out_path = process_csv_file(csv_path, out_dir, 'md')

            self.assertTrue(out_path.exists())
            self.assertEqual(out_path.suffix, '.md')
            self.assertEqual(out_path.stem, 'data')

    def test_md_output_has_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            csv_path = tmpdir_path / 'data.csv'
            csv_path.write_text(SAMPLE_CSV, encoding='utf-8')

            out_path = process_csv_file(csv_path, tmpdir_path / 'out', 'md')
            content = out_path.read_text(encoding='utf-8')

            self.assertIn('---', content)
            self.assertIn('fetched_at:', content)
            self.assertIn('rows:', content)

    def test_txt_format_no_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            csv_path = tmpdir_path / 'data.csv'
            csv_path.write_text(SAMPLE_CSV, encoding='utf-8')

            out_path = process_csv_file(csv_path, tmpdir_path / 'out', 'txt')
            self.assertEqual(out_path.suffix, '.txt')
            content = out_path.read_text(encoding='utf-8')
            self.assertNotIn('fetched_at:', content)

    def test_empty_file_produces_empty_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            csv_path = tmpdir_path / 'empty.csv'
            csv_path.write_text('', encoding='utf-8')

            out_path = process_csv_file(csv_path, tmpdir_path / 'out', 'md')
            self.assertTrue(out_path.exists())
            self.assertEqual(out_path.read_text(encoding='utf-8'), '')

    def test_max_rows_truncation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            csv_path = tmpdir_path / 'big.csv'
            lines = ['col1,col2'] + [f'row{i},val{i}' for i in range(20)]
            csv_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

            out_path = process_csv_file(csv_path, tmpdir_path / 'out', 'md', max_rows=5)
            content = out_path.read_text(encoding='utf-8')

            self.assertIn('truncated', content.lower())

    def test_output_dir_created_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / 'data.csv'
            csv_path.write_text(SAMPLE_CSV, encoding='utf-8')
            new_dir = Path(tmpdir) / 'deep' / 'nested' / 'dir'

            out_path = process_csv_file(csv_path, new_dir, 'md')
            self.assertTrue(out_path.exists())

    def test_tsv_file_processed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tsv_path = tmpdir_path / 'data.tsv'
            tsv_path.write_text(SAMPLE_TSV, encoding='utf-8')

            out_path = process_csv_file(tsv_path, tmpdir_path / 'out', 'md')
            content = out_path.read_text(encoding='utf-8')
            self.assertIn('tab', content)  # delimiter in frontmatter


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    def test_help_exits_cleanly(self):
        from typer.testing import CliRunner
        from any2md.csv import app

        runner = CliRunner()
        result = runner.invoke(app, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('csv', result.output.lower())

    def test_single_file_end_to_end(self):
        from typer.testing import CliRunner
        from any2md.csv import app

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            csv_path = tmpdir_path / 'sample.csv'
            csv_path.write_text(SAMPLE_CSV, encoding='utf-8')
            out_dir = tmpdir_path / 'out'

            runner = CliRunner()
            result = runner.invoke(app, [str(csv_path), '-o', str(out_dir)])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertTrue((out_dir / 'sample.md').exists())

    def test_batch_directory_mode(self):
        from typer.testing import CliRunner
        from any2md.csv import app

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / 'a.csv').write_text(SAMPLE_CSV, encoding='utf-8')
            (tmpdir_path / 'b.tsv').write_text(SAMPLE_TSV, encoding='utf-8')
            out_dir = tmpdir_path / 'out'

            runner = CliRunner()
            result = runner.invoke(app, [str(tmpdir_path), '-o', str(out_dir)])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertTrue((out_dir / 'a.md').exists())
            self.assertTrue((out_dir / 'b.md').exists())

    def test_missing_file_exits_with_error(self):
        from typer.testing import CliRunner
        from any2md.csv import app

        runner = CliRunner()
        result = runner.invoke(app, ['/nonexistent/path/data.csv'])
        self.assertNotEqual(result.exit_code, 0)

    def test_empty_directory_exits_with_error(self):
        from typer.testing import CliRunner
        from any2md.csv import app

        with tempfile.TemporaryDirectory() as tmpdir:
            runner = CliRunner()
            result = runner.invoke(app, [tmpdir])
            self.assertNotEqual(result.exit_code, 0)

    def test_txt_format_flag(self):
        from typer.testing import CliRunner
        from any2md.csv import app

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            csv_path = tmpdir_path / 'data.csv'
            csv_path.write_text(SAMPLE_CSV, encoding='utf-8')
            out_dir = tmpdir_path / 'out'

            runner = CliRunner()
            result = runner.invoke(app, [str(csv_path), '-o', str(out_dir), '-f', 'txt'])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            out_file = out_dir / 'data.txt'
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding='utf-8')
            self.assertNotIn('fetched_at:', content)

    def test_max_rows_option(self):
        from typer.testing import CliRunner
        from any2md.csv import app

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            csv_path = tmpdir_path / 'big.csv'
            lines = ['col1,col2'] + [f'r{i},v{i}' for i in range(50)]
            csv_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            out_dir = tmpdir_path / 'out'

            runner = CliRunner()
            result = runner.invoke(app, [str(csv_path), '-o', str(out_dir), '--max-rows', '10'])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            content = (out_dir / 'big.md').read_text(encoding='utf-8')
            self.assertIn('truncated', content.lower())


if __name__ == '__main__':
    unittest.main()
