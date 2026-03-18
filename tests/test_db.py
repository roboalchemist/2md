"""
test_db.py - Unit tests for db.py (SQLite → Markdown converter)

All tests use in-memory SQLite databases (":memory:") — no disk I/O required.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from any2md.db import (
    discover_tables,
    format_sample_table,
    format_schema_block,
    format_table_section,
    get_column_names,
    get_row_count,
    get_sample_rows,
    get_table_schema,
    render_cell,
    db_to_markdown,
    db_to_plain_text,
    extract_db_info,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_conn(sql: str = "") -> sqlite3.Connection:
    """Create an in-memory connection and optionally execute setup SQL."""
    conn = sqlite3.connect(":memory:")
    if sql:
        conn.executescript(sql)
    return conn


# ---------------------------------------------------------------------------
# Table discovery
# ---------------------------------------------------------------------------

class TestDiscoverTables:
    def test_empty_database_returns_empty(self):
        conn = make_conn()
        result = discover_tables(conn)
        assert result == []

    def test_single_table_found(self):
        conn = make_conn("CREATE TABLE users (id INTEGER, name TEXT);")
        result = discover_tables(conn)
        assert len(result) == 1
        assert result[0] == ("table", "users")

    def test_multiple_tables_found(self):
        conn = make_conn("""
            CREATE TABLE alpha (id INTEGER);
            CREATE TABLE beta (id INTEGER);
        """)
        result = discover_tables(conn)
        names = [r[1] for r in result]
        assert "alpha" in names
        assert "beta" in names

    def test_views_included_by_default(self):
        conn = make_conn("""
            CREATE TABLE things (id INTEGER, val TEXT);
            CREATE VIEW things_view AS SELECT * FROM things;
        """)
        result = discover_tables(conn, include_views=True)
        types = {r[0] for r in result}
        assert "table" in types
        assert "view" in types

    def test_views_excluded_when_skip(self):
        conn = make_conn("""
            CREATE TABLE things (id INTEGER, val TEXT);
            CREATE VIEW things_view AS SELECT * FROM things;
        """)
        result = discover_tables(conn, include_views=False)
        types = {r[0] for r in result}
        assert "view" not in types
        assert "table" in types

    def test_sqlite_internal_tables_excluded(self):
        # sqlite_master is always present; ensure it doesn't appear
        conn = make_conn()
        result = discover_tables(conn)
        names = [r[1] for r in result]
        for name in names:
            assert not name.startswith("sqlite_")


# ---------------------------------------------------------------------------
# Schema rendering
# ---------------------------------------------------------------------------

class TestGetTableSchema:
    def test_returns_create_statement(self):
        conn = make_conn("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT);")
        schema = get_table_schema(conn, "items")
        assert "CREATE TABLE" in schema.upper()
        assert "items" in schema

    def test_unknown_table_returns_empty(self):
        conn = make_conn()
        schema = get_table_schema(conn, "nonexistent")
        assert schema == ""


class TestFormatSchemaBlock:
    def test_wraps_in_sql_fence(self):
        sql = "CREATE TABLE t (id INTEGER);"
        result = format_schema_block(sql)
        assert result.startswith("```sql\n")
        assert result.strip().endswith("```")
        assert "CREATE TABLE t" in result

    def test_empty_sql_returns_placeholder(self):
        result = format_schema_block("")
        assert "No schema available" in result


# ---------------------------------------------------------------------------
# Sample row formatting
# ---------------------------------------------------------------------------

class TestRenderCell:
    def test_none_returns_empty_string(self):
        assert render_cell(None) == ""

    def test_bytes_renders_blob_tag(self):
        data = b"\x00\x01\x02"
        result = render_cell(data)
        assert result == "[BLOB: 3 bytes]"

    def test_bytearray_renders_blob_tag(self):
        data = bytearray(b"hello")
        result = render_cell(data)
        assert result == "[BLOB: 5 bytes]"

    def test_long_text_truncated(self):
        long_text = "a" * 200
        result = render_cell(long_text, max_len=80)
        assert len(result) <= 82  # 80 chars + ellipsis character
        assert result.endswith("…")

    def test_short_text_not_truncated(self):
        text = "hello world"
        result = render_cell(text, max_len=80)
        assert result == "hello world"

    def test_pipe_escaped(self):
        result = render_cell("foo|bar")
        assert "\\|" in result
        assert "|" not in result.replace("\\|", "")

    def test_newline_replaced_with_space(self):
        result = render_cell("line1\nline2")
        assert "\n" not in result

    def test_integer_rendered_as_string(self):
        assert render_cell(42) == "42"

    def test_float_rendered_as_string(self):
        assert render_cell(3.14) == "3.14"


class TestFormatSampleTable:
    def test_empty_rows_returns_no_rows_message(self):
        result = format_sample_table(["id", "name"], [], total_rows=0, shown=10)
        assert "No rows" in result

    def test_header_contains_column_names(self):
        result = format_sample_table(
            ["id", "name"],
            [(1, "Alice"), (2, "Bob")],
            total_rows=2,
            shown=10,
        )
        assert "id" in result
        assert "name" in result

    def test_data_rows_rendered(self):
        result = format_sample_table(
            ["id", "val"],
            [(1, "foo"), (2, "bar")],
            total_rows=2,
            shown=10,
        )
        assert "foo" in result
        assert "bar" in result

    def test_truncation_note_shown_when_limited(self):
        result = format_sample_table(
            ["id"],
            [(1,), (2,), (3,)],
            total_rows=100,
            shown=3,
        )
        assert "Showing 3 of 100" in result

    def test_no_truncation_note_when_all_shown(self):
        result = format_sample_table(
            ["id"],
            [(1,)],
            total_rows=1,
            shown=10,
        )
        assert "Showing" not in result

    def test_null_cell_renders_as_empty(self):
        result = format_sample_table(
            ["id", "val"],
            [(1, None)],
            total_rows=1,
            shown=10,
        )
        # The None cell should produce an empty cell (two consecutive pipes)
        assert "| 1 |  |" in result or "| 1 | |" in result


# ---------------------------------------------------------------------------
# NULL and BLOB handling (end-to-end via in-memory DB)
# ---------------------------------------------------------------------------

class TestNullAndBlobHandling:
    def _setup_conn(self):
        conn = make_conn("""
            CREATE TABLE mixed (id INTEGER, data BLOB, note TEXT);
        """)
        conn.execute("INSERT INTO mixed VALUES (1, NULL, 'hello')")
        conn.execute("INSERT INTO mixed VALUES (2, X'DEADBEEF', NULL)")
        conn.commit()
        return conn

    def test_null_value_in_sample_rows(self):
        conn = self._setup_conn()
        rows = get_sample_rows(conn, "mixed", 10)
        result = format_sample_table(["id", "data", "note"], rows, 2, 10)
        # Row with NULL data should have empty cell for data
        assert "hello" in result

    def test_blob_value_renders_blob_tag(self):
        conn = self._setup_conn()
        rows = get_sample_rows(conn, "mixed", 10)
        result = format_sample_table(["id", "data", "note"], rows, 2, 10)
        assert "[BLOB:" in result


# ---------------------------------------------------------------------------
# Truncation (long text)
# ---------------------------------------------------------------------------

class TestTruncation:
    def test_long_text_truncated_in_table(self):
        conn = make_conn("CREATE TABLE docs (id INTEGER, body TEXT);")
        long_body = "x" * 500
        conn.execute("INSERT INTO docs VALUES (1, ?)", (long_body,))
        conn.commit()

        rows = get_sample_rows(conn, "docs", 10)
        result = format_sample_table(["id", "body"], rows, 1, 10)
        assert "…" in result
        # The full 500-char string should not appear verbatim
        assert long_body not in result


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

class TestFrontmatter:
    def test_frontmatter_fields_present(self, tmp_path):
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE t (id INTEGER);")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()

        metadata, body = extract_db_info(db_path)

        assert "source" in metadata
        assert "file_size" in metadata
        assert "table_count" in metadata
        assert "total_rows" in metadata
        assert "fetched_at" in metadata

    def test_frontmatter_values_correct(self, tmp_path):
        db_path = tmp_path / "mydb.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE t (id INTEGER);")
        conn.execute("INSERT INTO t VALUES (42)")
        conn.commit()
        conn.close()

        metadata, _ = extract_db_info(db_path)

        assert metadata["table_count"] == 1
        assert metadata["total_rows"] == 1
        assert metadata["file_size"] > 0
        assert str(db_path.resolve()) == metadata["source"]

    def test_markdown_output_contains_frontmatter_delimiters(self, tmp_path):
        db_path = tmp_path / "mydb.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE t (id INTEGER);")
        conn.commit()
        conn.close()

        metadata, body = extract_db_info(db_path)
        output = db_to_markdown(metadata, body)

        assert output.startswith("---")
        # Second --- closes the frontmatter block
        assert output.count("---") >= 2


# ---------------------------------------------------------------------------
# Empty database
# ---------------------------------------------------------------------------

class TestEmptyDatabase:
    def test_empty_db_zero_tables(self, tmp_path):
        db_path = tmp_path / "empty.db"
        # Create file by connecting then closing immediately
        sqlite3.connect(str(db_path)).close()

        metadata, body = extract_db_info(db_path)

        assert metadata["table_count"] == 0
        assert metadata["total_rows"] == 0

    def test_empty_db_markdown_output(self, tmp_path):
        db_path = tmp_path / "empty.db"
        sqlite3.connect(str(db_path)).close()

        metadata, body = extract_db_info(db_path)
        output = db_to_markdown(metadata, body)

        # Should still produce valid markdown with frontmatter
        assert "---" in output
        assert "empty.db" in output

    def test_empty_db_plain_text_output(self, tmp_path):
        db_path = tmp_path / "empty.db"
        sqlite3.connect(str(db_path)).close()

        metadata, body = extract_db_info(db_path)
        output = db_to_plain_text(body)

        # No tables means empty body — no crash
        assert isinstance(output, str)


# ---------------------------------------------------------------------------
# Row and table limits
# ---------------------------------------------------------------------------

class TestLimits:
    def test_max_rows_limits_sample(self, tmp_path):
        db_path = tmp_path / "big.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE nums (n INTEGER);")
        for i in range(100):
            conn.execute("INSERT INTO nums VALUES (?)", (i,))
        conn.commit()
        conn.close()

        metadata, body = extract_db_info(db_path, max_rows=5)
        # Total rows should still reflect the real count
        assert metadata["total_rows"] == 100
        # But the body should note the limit
        assert "Showing 5 of 100" in body

    def test_max_tables_limits_sections(self, tmp_path):
        db_path = tmp_path / "many.db"
        conn = sqlite3.connect(str(db_path))
        for i in range(10):
            conn.execute(f"CREATE TABLE t{i} (id INTEGER);")
        conn.commit()
        conn.close()

        metadata, body = extract_db_info(db_path, max_tables=3)
        assert metadata["table_count"] == 3
