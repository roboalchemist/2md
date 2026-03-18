"""
Unit tests for any2md.nb — Jupyter Notebook to Markdown converter.

All tests use hand-crafted dicts / the sample.ipynb fixture so they run
without an actual Jupyter installation (no nbformat, no nbconvert).
"""

import json
from pathlib import Path
import unittest

from any2md.nb import (
    _source_text,
    _render_outputs,
    notebook_to_markdown,
    extract_nb_metadata,
    nb_to_full_markdown,
    nb_to_plain_text,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_nb(cells, metadata=None):
    """Build a minimal notebook dict."""
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": metadata or {
            "kernelspec": {"language": "python", "display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "cells": cells,
    }


def _md_cell(source):
    return {"cell_type": "markdown", "source": source, "metadata": {}, "id": "md-1"}


def _code_cell(source, outputs=None):
    return {
        "cell_type": "code",
        "source": source,
        "outputs": outputs or [],
        "execution_count": None,
        "metadata": {},
        "id": "code-1",
    }


# ---------------------------------------------------------------------------
# Tests: _source_text
# ---------------------------------------------------------------------------

class TestSourceText(unittest.TestCase):
    def test_string_passthrough(self):
        self.assertEqual(_source_text("hello"), "hello")

    def test_list_joined(self):
        self.assertEqual(_source_text(["line1\n", "line2"]), "line1\nline2")

    def test_empty_string(self):
        self.assertEqual(_source_text(""), "")

    def test_empty_list(self):
        self.assertEqual(_source_text([]), "")

    def test_none_returns_empty(self):
        self.assertEqual(_source_text(None), "")


# ---------------------------------------------------------------------------
# Tests: markdown cell passthrough
# ---------------------------------------------------------------------------

class TestMarkdownCell(unittest.TestCase):
    def test_markdown_cell_passes_through(self):
        nb = _make_nb([_md_cell("# Hello\n\nWorld")])
        result = notebook_to_markdown(nb)
        self.assertIn("# Hello", result)
        self.assertIn("World", result)

    def test_markdown_cell_source_as_list(self):
        nb = _make_nb([_md_cell(["# Title\n", "paragraph text"])])
        result = notebook_to_markdown(nb)
        self.assertIn("# Title", result)
        self.assertIn("paragraph text", result)

    def test_empty_markdown_cell_skipped(self):
        nb = _make_nb([_md_cell(""), _md_cell("real content")])
        result = notebook_to_markdown(nb)
        self.assertEqual(result, "real content")


# ---------------------------------------------------------------------------
# Tests: code cell → fenced block
# ---------------------------------------------------------------------------

class TestCodeCell(unittest.TestCase):
    def test_code_cell_fenced_with_language(self):
        nb = _make_nb([_code_cell("x = 1")])
        result = notebook_to_markdown(nb, kernel_language="python")
        self.assertIn("```python", result)
        self.assertIn("x = 1", result)
        self.assertIn("```", result)

    def test_code_cell_source_as_list(self):
        nb = _make_nb([_code_cell(["x = 1\n", "print(x)"])])
        result = notebook_to_markdown(nb, kernel_language="python")
        self.assertIn("x = 1", result)
        self.assertIn("print(x)", result)

    def test_code_cell_kernel_language_tag(self):
        nb = _make_nb([_code_cell("cat file.txt")])
        result = notebook_to_markdown(nb, kernel_language="bash")
        self.assertIn("```bash", result)

    def test_empty_code_cell_skipped(self):
        nb = _make_nb([_code_cell("")])
        result = notebook_to_markdown(nb)
        # Empty code cell should produce no output
        self.assertEqual(result.strip(), "")


# ---------------------------------------------------------------------------
# Tests: output cell rendering
# ---------------------------------------------------------------------------

class TestOutputRendering(unittest.TestCase):
    def test_stream_output(self):
        outputs = [{"output_type": "stream", "name": "stdout", "text": "hello\n"}]
        result = _render_outputs(outputs)
        self.assertIn("```output", result)
        self.assertIn("hello", result)

    def test_execute_result_text_plain(self):
        outputs = [{
            "output_type": "execute_result",
            "execution_count": 1,
            "metadata": {},
            "data": {"text/plain": "42"},
        }]
        result = _render_outputs(outputs)
        self.assertIn("```result", result)
        self.assertIn("42", result)

    def test_image_output_omitted(self):
        outputs = [{
            "output_type": "display_data",
            "metadata": {},
            "data": {
                "image/png": "iVBORw0KGgo=",
                "text/plain": "<Figure>",
            },
        }]
        result = _render_outputs(outputs)
        self.assertIn("[image output omitted]", result)
        self.assertNotIn("iVBORw0KGgo=", result)

    def test_error_output(self):
        outputs = [{
            "output_type": "error",
            "ename": "NameError",
            "evalue": "name 'x' is not defined",
            "traceback": ["NameError: name 'x' is not defined"],
        }]
        result = _render_outputs(outputs)
        self.assertIn("```output", result)
        self.assertIn("NameError", result)

    def test_stream_output_via_notebook(self):
        outputs = [{"output_type": "stream", "name": "stdout", "text": "2\n"}]
        nb = _make_nb([_code_cell("print(2)", outputs=outputs)])
        result = notebook_to_markdown(nb)
        self.assertIn("```output", result)
        self.assertIn("2", result)


# ---------------------------------------------------------------------------
# Tests: --no-outputs
# ---------------------------------------------------------------------------

class TestNoOutputs(unittest.TestCase):
    def test_no_outputs_skips_stream(self):
        outputs = [{"output_type": "stream", "name": "stdout", "text": "stream_sentinel_xyz\n"}]
        nb = _make_nb([_code_cell("print('hello')", outputs=outputs)])
        result = notebook_to_markdown(nb, include_outputs=False)
        self.assertNotIn("```output", result)
        self.assertNotIn("stream_sentinel_xyz", result)
        # But the code itself should still appear
        self.assertIn("print('hello')", result)

    def test_no_outputs_skips_execute_result(self):
        outputs = [{
            "output_type": "execute_result",
            "execution_count": 1,
            "metadata": {},
            "data": {"text/plain": "99"},
        }]
        nb = _make_nb([_code_cell("99", outputs=outputs)])
        result = notebook_to_markdown(nb, include_outputs=False)
        self.assertNotIn("```result", result)
        self.assertNotIn("99", result.split("```")[0] if "```" in result else result)


# ---------------------------------------------------------------------------
# Tests: frontmatter extraction
# ---------------------------------------------------------------------------

class TestFrontmatterExtraction(unittest.TestCase):
    def test_title_from_first_h1(self):
        nb = _make_nb([
            _md_cell("# My Notebook\n\nIntro"),
            _code_cell("x = 1"),
        ])
        meta = extract_nb_metadata(nb, Path("my_notebook.ipynb"))
        self.assertEqual(meta["title"], "My Notebook")

    def test_title_fallback_to_stem(self):
        nb = _make_nb([_code_cell("x = 1")])
        meta = extract_nb_metadata(nb, Path("my_file.ipynb"))
        self.assertEqual(meta["title"], "my_file")

    def test_kernel_language_from_kernelspec(self):
        nb = _make_nb([], metadata={"kernelspec": {"language": "julia"}})
        meta = extract_nb_metadata(nb, Path("nb.ipynb"))
        self.assertEqual(meta["kernel_language"], "julia")

    def test_kernel_language_fallback_to_language_info(self):
        nb = _make_nb([], metadata={"language_info": {"name": "r"}})
        meta = extract_nb_metadata(nb, Path("nb.ipynb"))
        self.assertEqual(meta["kernel_language"], "r")

    def test_cell_counts(self):
        nb = _make_nb([
            _md_cell("# Title"),
            _md_cell("Some text"),
            _code_cell("x = 1"),
            _code_cell("y = 2"),
        ])
        meta = extract_nb_metadata(nb, Path("nb.ipynb"))
        self.assertEqual(meta["cell_count"], 4)
        self.assertEqual(meta["code_cell_count"], 2)
        self.assertEqual(meta["markdown_cell_count"], 2)

    def test_fetched_at_present(self):
        nb = _make_nb([])
        meta = extract_nb_metadata(nb, Path("nb.ipynb"))
        self.assertIn("fetched_at", meta)
        self.assertTrue(meta["fetched_at"].endswith("Z"))

    def test_source_is_absolute(self):
        nb = _make_nb([])
        path = Path("relative/nb.ipynb")
        meta = extract_nb_metadata(nb, path)
        self.assertTrue(Path(meta["source"]).is_absolute())


# ---------------------------------------------------------------------------
# Tests: full markdown output assembly
# ---------------------------------------------------------------------------

class TestFullMarkdown(unittest.TestCase):
    def test_frontmatter_in_output(self):
        nb = _make_nb([_md_cell("# Hello")])
        meta = extract_nb_metadata(nb, Path("hello.ipynb"))
        md = notebook_to_markdown(nb)
        output = nb_to_full_markdown(md, metadata=meta)
        self.assertTrue(output.startswith("---"))
        self.assertIn("kernel_language:", output)
        self.assertIn("# Hello", output)

    def test_no_frontmatter_when_none(self):
        md = "# Hello"
        output = nb_to_full_markdown(md, metadata=None)
        self.assertFalse(output.startswith("---"))
        self.assertIn("# Hello", output)


# ---------------------------------------------------------------------------
# Tests: plain text output
# ---------------------------------------------------------------------------

class TestPlainText(unittest.TestCase):
    def test_headings_stripped(self):
        md = "# Title\n\nSome text"
        result = nb_to_plain_text(md)
        self.assertNotIn("#", result)
        self.assertIn("Title", result)

    def test_code_fences_stripped(self):
        md = "```python\nx = 1\n```"
        result = nb_to_plain_text(md)
        self.assertNotIn("```", result)
        self.assertIn("x = 1", result)


# ---------------------------------------------------------------------------
# Tests: empty notebook
# ---------------------------------------------------------------------------

class TestEmptyNotebook(unittest.TestCase):
    def test_empty_notebook_produces_empty_content(self):
        nb = _make_nb([])
        result = notebook_to_markdown(nb)
        self.assertEqual(result.strip(), "")

    def test_empty_notebook_metadata(self):
        nb = _make_nb([])
        meta = extract_nb_metadata(nb, Path("empty.ipynb"))
        self.assertEqual(meta["cell_count"], 0)
        self.assertEqual(meta["code_cell_count"], 0)
        self.assertEqual(meta["markdown_cell_count"], 0)


# ---------------------------------------------------------------------------
# Tests: fixture file
# ---------------------------------------------------------------------------

class TestFixture(unittest.TestCase):
    def test_sample_ipynb_loads_and_converts(self):
        fixture = FIXTURES / "sample.ipynb"
        nb = json.loads(fixture.read_text())
        meta = extract_nb_metadata(nb, fixture)
        self.assertEqual(meta["title"], "Sample Notebook")
        self.assertEqual(meta["kernel_language"], "python")
        self.assertEqual(meta["code_cell_count"], 2)
        self.assertEqual(meta["markdown_cell_count"], 2)

        md = notebook_to_markdown(nb, kernel_language="python")
        self.assertIn("```python", md)
        self.assertIn("x = 1 + 1", md)
        self.assertIn("# Sample Notebook", md)
        # Image output should be omitted
        self.assertIn("[image output omitted]", md)
        # Stream output should be rendered
        self.assertIn("```output", md)

    def test_sample_ipynb_no_outputs(self):
        fixture = FIXTURES / "sample.ipynb"
        nb = json.loads(fixture.read_text())
        md = notebook_to_markdown(nb, kernel_language="python", include_outputs=False)
        self.assertNotIn("```output", md)
        self.assertNotIn("```result", md)
        self.assertNotIn("[image output omitted]", md)
        # Code still present
        self.assertIn("```python", md)


if __name__ == "__main__":
    unittest.main()
