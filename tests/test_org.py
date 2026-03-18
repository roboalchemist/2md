#!/usr/bin/env python3
"""
test_org.py - Unit tests for any2md/org.py

Tests cover:
- Heading conversion (various depths)
- TODO/DONE → checkboxes
- Code blocks (#+BEGIN_SRC / #+END_SRC)
- Quote blocks (#+BEGIN_QUOTE / #+END_QUOTE)
- Link conversion ([[url][text]] and [[url]])
- Emphasis conversion (*bold*, /italic/, _underline_, +strikethrough+, ~code~, =verbatim=)
- Export keyword extraction (#+TITLE: etc.)
- Tag extraction and stripping from headings
- Table passthrough with separator insertion
- Property drawer stripping
- Comment stripping
- Frontmatter assembly
- Plain-text output
- process_org_file file I/O
- CLI batch mode, missing file, help
"""

import tempfile
import unittest
from pathlib import Path

from any2md.org import (
    org_to_markdown_lines,
    org_to_markdown_text,
    org_to_full_markdown,
    org_to_plain_text,
    extract_org_metadata,
    process_org_file,
    _convert_links,
    _convert_emphasis,
    _process_table,
)


# ---------------------------------------------------------------------------
# Sample Org-mode content
# ---------------------------------------------------------------------------

SAMPLE_ORG = """\
#+TITLE: My Project
#+AUTHOR: Jane Doe
#+DATE: 2026-03-01
#+LANGUAGE: en

* Introduction

This is a paragraph with *bold* and /italic/ text.

** Sub-heading

Some more content.

* TODO Write unit tests

* DONE Ship the feature
"""

MINIMAL_ORG = "Just some plain text with no metadata.\n"


# ---------------------------------------------------------------------------
# _convert_links
# ---------------------------------------------------------------------------

class TestConvertLinks(unittest.TestCase):
    def test_named_link(self):
        result = _convert_links("[[https://example.com][Example Site]]")
        self.assertEqual(result, "[Example Site](https://example.com)")

    def test_bare_link(self):
        result = _convert_links("[[https://example.com]]")
        self.assertEqual(result, "<https://example.com>")

    def test_file_link(self):
        result = _convert_links("[[file:notes.org][My Notes]]")
        self.assertEqual(result, "[My Notes](file:notes.org)")

    def test_no_links_unchanged(self):
        text = "plain text with no links"
        self.assertEqual(_convert_links(text), text)

    def test_multiple_links_in_line(self):
        result = _convert_links("See [[https://a.com][A]] and [[https://b.com][B]]")
        self.assertIn("[A](https://a.com)", result)
        self.assertIn("[B](https://b.com)", result)


# ---------------------------------------------------------------------------
# _convert_emphasis
# ---------------------------------------------------------------------------

class TestConvertEmphasis(unittest.TestCase):
    def test_bold(self):
        result = _convert_emphasis("*bold text*")
        self.assertIn("**bold text**", result)

    def test_italic(self):
        result = _convert_emphasis("/italic text/")
        self.assertIn("*italic text*", result)

    def test_underline(self):
        result = _convert_emphasis("_underline text_")
        self.assertIn("*underline text*", result)

    def test_strikethrough(self):
        result = _convert_emphasis("+strikethrough+")
        self.assertIn("~~strikethrough~~", result)

    def test_code_tilde(self):
        result = _convert_emphasis("~some code~")
        self.assertIn("`some code`", result)

    def test_verbatim_equals(self):
        result = _convert_emphasis("=verbatim text=")
        self.assertIn("`verbatim text`", result)

    def test_no_emphasis_unchanged(self):
        text = "plain text"
        self.assertEqual(_convert_emphasis(text), text)

    def test_emphasis_not_applied_to_partial(self):
        # snake_case should not trigger _underline_
        text = "foo_bar_baz"
        result = _convert_emphasis(text)
        self.assertNotIn("*bar*", result)


# ---------------------------------------------------------------------------
# Heading conversion
# ---------------------------------------------------------------------------

class TestHeadingConversion(unittest.TestCase):
    def _lines(self, content: str) -> list:
        lines, _ = org_to_markdown_lines(content)
        return lines

    def test_level1_heading(self):
        lines = self._lines("* Top Level\n")
        self.assertIn("# Top Level", lines)

    def test_level2_heading(self):
        lines = self._lines("** Sub Level\n")
        self.assertIn("## Sub Level", lines)

    def test_level3_heading(self):
        lines = self._lines("*** Deep Level\n")
        self.assertIn("### Deep Level", lines)

    def test_level4_heading(self):
        lines = self._lines("**** Very Deep\n")
        self.assertIn("#### Very Deep", lines)

    def test_level6_capped(self):
        # Org allows arbitrarily deep headings; we cap at h6
        lines = self._lines("******* Seven Stars\n")
        self.assertIn("###### Seven Stars", lines)

    def test_heading_content_preserved(self):
        lines = self._lines("* Hello World\n")
        self.assertTrue(any("Hello World" in l for l in lines))


# ---------------------------------------------------------------------------
# TODO / DONE → checkboxes
# ---------------------------------------------------------------------------

class TestTodoCheckboxes(unittest.TestCase):
    def _lines(self, content: str) -> list:
        lines, _ = org_to_markdown_lines(content)
        return lines

    def test_todo_becomes_unchecked(self):
        lines = self._lines("* TODO Write tests\n")
        self.assertIn("- [ ] Write tests", lines)

    def test_done_becomes_checked(self):
        lines = self._lines("* DONE Ship feature\n")
        self.assertIn("- [x] Ship feature", lines)

    def test_todo_case_insensitive(self):
        lines = self._lines("* todo lowercase\n")
        self.assertTrue(any("- [ ]" in l for l in lines))

    def test_todo_nested(self):
        lines = self._lines("** TODO Nested task\n")
        # Nested TODO heading becomes a checkbox (heading level ignored for TODO)
        self.assertTrue(any("- [ ] Nested task" in l for l in lines))

    def test_regular_heading_not_checkbox(self):
        lines = self._lines("* Normal Heading\n")
        self.assertFalse(any("- [ ]" in l or "- [x]" in l for l in lines))


# ---------------------------------------------------------------------------
# Code blocks
# ---------------------------------------------------------------------------

class TestCodeBlocks(unittest.TestCase):
    def _text(self, content: str) -> str:
        return org_to_markdown_text(content)

    def test_src_block_with_lang(self):
        org = "#+BEGIN_SRC python\nprint('hello')\n#+END_SRC\n"
        text = self._text(org)
        self.assertIn("```python", text)
        self.assertIn("print('hello')", text)
        self.assertIn("```", text)

    def test_src_block_without_lang(self):
        org = "#+BEGIN_SRC\nsome code\n#+END_SRC\n"
        text = self._text(org)
        self.assertIn("```", text)
        self.assertIn("some code", text)

    def test_src_block_case_insensitive(self):
        org = "#+begin_src python\nx = 1\n#+end_src\n"
        text = self._text(org)
        self.assertIn("```python", text)
        self.assertIn("x = 1", text)

    def test_example_block_becomes_code_fence(self):
        org = "#+BEGIN_EXAMPLE\nraw text\n#+END_EXAMPLE\n"
        text = self._text(org)
        self.assertIn("```", text)
        self.assertIn("raw text", text)

    def test_code_block_content_not_emphasis_converted(self):
        # Content inside #+BEGIN_SRC should NOT have *bold* converted
        org = "#+BEGIN_SRC\n*not bold*\n#+END_SRC\n"
        text = self._text(org)
        self.assertIn("*not bold*", text)
        self.assertNotIn("**not bold**", text)


# ---------------------------------------------------------------------------
# Quote blocks
# ---------------------------------------------------------------------------

class TestQuoteBlocks(unittest.TestCase):
    def _text(self, content: str) -> str:
        return org_to_markdown_text(content)

    def test_quote_block_prefixed(self):
        org = "#+BEGIN_QUOTE\nThis is a quote.\n#+END_QUOTE\n"
        text = self._text(org)
        self.assertIn("> This is a quote.", text)

    def test_multiline_quote(self):
        org = "#+BEGIN_QUOTE\nLine one.\nLine two.\n#+END_QUOTE\n"
        text = self._text(org)
        self.assertIn("> Line one.", text)
        self.assertIn("> Line two.", text)

    def test_quote_markers_not_in_output(self):
        org = "#+BEGIN_QUOTE\nQuoted.\n#+END_QUOTE\n"
        text = self._text(org)
        self.assertNotIn("#+BEGIN_QUOTE", text)
        self.assertNotIn("#+END_QUOTE", text)


# ---------------------------------------------------------------------------
# Export keyword extraction
# ---------------------------------------------------------------------------

class TestExportKeywords(unittest.TestCase):
    def _meta(self, content: str) -> dict:
        with tempfile.NamedTemporaryFile(suffix=".org", delete=False) as f:
            path = Path(f.name)
        try:
            path.write_text(content, encoding='utf-8')
            return extract_org_metadata(content, path)
        finally:
            path.unlink(missing_ok=True)

    def test_title_extracted(self):
        meta = self._meta("#+TITLE: My Doc\n\nContent.\n")
        self.assertEqual(meta.get('title'), "My Doc")

    def test_author_extracted(self):
        meta = self._meta("#+AUTHOR: Jane Doe\n")
        self.assertEqual(meta.get('author'), "Jane Doe")

    def test_date_extracted(self):
        meta = self._meta("#+DATE: 2026-03-01\n")
        self.assertEqual(meta.get('date'), "2026-03-01")

    def test_language_extracted(self):
        meta = self._meta("#+LANGUAGE: en\n")
        self.assertEqual(meta.get('language'), "en")

    def test_unknown_keyword_not_in_meta(self):
        meta = self._meta("#+OPTIONS: toc:nil\n")
        self.assertNotIn('options', meta)

    def test_keywords_stripped_from_body(self):
        text = org_to_markdown_text("#+TITLE: My Doc\n\nBody text.\n")
        self.assertNotIn("#+TITLE:", text)
        self.assertIn("Body text.", text)

    def test_fetched_at_always_present(self):
        meta = self._meta(MINIMAL_ORG)
        self.assertIn('fetched_at', meta)

    def test_source_is_absolute(self):
        meta = self._meta(MINIMAL_ORG)
        self.assertTrue(Path(meta['source']).is_absolute())


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

class TestTags(unittest.TestCase):
    def _meta_and_text(self, content: str):
        lines, meta = org_to_markdown_lines(content)
        return '\n'.join(lines), meta

    def test_tags_extracted_to_metadata(self):
        _, meta = org_to_markdown_lines("* Heading :tag1:tag2:\n")
        self.assertIn('tags', meta)
        self.assertIn('tag1', meta['tags'])
        self.assertIn('tag2', meta['tags'])

    def test_tags_stripped_from_heading(self):
        text, _ = self._meta_and_text("* Heading :mytag:\n")
        self.assertNotIn(":mytag:", text)
        self.assertTrue(any("Heading" in l for l in text.splitlines()))

    def test_tags_deduplicated(self):
        _, meta = org_to_markdown_lines("* A :tag1:\n* B :tag1:tag2:\n")
        self.assertEqual(meta['tags'].count('tag1'), 1)

    def test_no_tags_no_tags_key(self):
        _, meta = org_to_markdown_lines("* Plain Heading\n")
        self.assertNotIn('tags', meta)


# ---------------------------------------------------------------------------
# Property drawers
# ---------------------------------------------------------------------------

class TestPropertyDrawers(unittest.TestCase):
    def _text(self, content: str) -> str:
        return org_to_markdown_text(content)

    def test_properties_stripped(self):
        org = "* Heading\n:PROPERTIES:\n:ID: abc123\n:CREATED: 2026-01-01\n:END:\n\nBody.\n"
        text = self._text(org)
        self.assertNotIn(":PROPERTIES:", text)
        self.assertNotIn(":ID:", text)
        self.assertNotIn(":END:", text)
        self.assertIn("Body.", text)


# ---------------------------------------------------------------------------
# Comment stripping
# ---------------------------------------------------------------------------

class TestComments(unittest.TestCase):
    def _text(self, content: str) -> str:
        return org_to_markdown_text(content)

    def test_comment_lines_stripped(self):
        org = "# This is a comment\nReal content.\n"
        text = self._text(org)
        self.assertNotIn("# This is a comment", text)
        self.assertIn("Real content.", text)

    def test_export_keywords_not_stripped_as_comments(self):
        # #+TITLE: should be treated as a keyword, not a comment
        org = "#+TITLE: My Title\nContent.\n"
        text = self._text(org)
        self.assertIn("Content.", text)
        # The keyword itself should be consumed (not appear in body)
        self.assertNotIn("#+TITLE:", text)


# ---------------------------------------------------------------------------
# Table passthrough
# ---------------------------------------------------------------------------

class TestTablePassthrough(unittest.TestCase):
    def _text(self, content: str) -> str:
        return org_to_markdown_text(content)

    def test_table_with_separator_passes_through(self):
        org = "| Name  | Age |\n|-------+-----|\n| Alice |  30 |\n"
        text = self._text(org)
        self.assertIn("| Name", text)
        self.assertIn("| Alice", text)

    def test_table_without_separator_gets_one_inserted(self):
        org = "| Name | Age |\n| Alice | 30 |\n"
        text = self._text(org)
        lines = text.splitlines()
        # There should be a separator line after the header
        header_idx = next(i for i, l in enumerate(lines) if "Name" in l and "|" in l)
        if header_idx + 1 < len(lines):
            sep_line = lines[header_idx + 1]
            self.assertIn("---", sep_line)

    def test_table_pipe_characters_preserved(self):
        org = "| Col1 | Col2 |\n|------+------|\n| A    | B    |\n"
        text = self._text(org)
        self.assertIn("|", text)


# ---------------------------------------------------------------------------
# Full markdown output (with frontmatter)
# ---------------------------------------------------------------------------

class TestOrgToFullMarkdown(unittest.TestCase):
    def test_includes_frontmatter_delimiters(self):
        meta = {'title': 'Test', 'fetched_at': '2026-03-01T00:00:00Z'}
        result = org_to_full_markdown("Body text.", metadata=meta)
        self.assertIn('---', result)
        self.assertIn('title:', result)
        self.assertIn('Body text.', result)

    def test_no_metadata_no_frontmatter(self):
        result = org_to_full_markdown("Body text.", metadata=None)
        self.assertNotIn('---', result)
        self.assertIn('Body text.', result)

    def test_full_sample_contains_title_in_frontmatter(self):
        lines, meta = org_to_markdown_lines(SAMPLE_ORG)
        body = '\n'.join(lines)
        result = org_to_full_markdown(body, metadata=meta)
        self.assertIn('title: My Project', result)


# ---------------------------------------------------------------------------
# Plain-text output
# ---------------------------------------------------------------------------

class TestOrgToPlainText(unittest.TestCase):
    def test_removes_heading_markers(self):
        md = "# Top\n\n## Sub\n\nContent."
        result = org_to_plain_text(md)
        self.assertNotIn('#', result)
        self.assertIn('Top', result)
        self.assertIn('Content.', result)

    def test_removes_bold_markers(self):
        md = "Some **bold** text."
        result = org_to_plain_text(md)
        self.assertNotIn('**', result)
        self.assertIn('bold', result)

    def test_removes_code_fences(self):
        md = "```python\nx = 1\n```"
        result = org_to_plain_text(md)
        self.assertNotIn('```', result)
        self.assertIn('x = 1', result)

    def test_removes_strikethrough(self):
        md = "~~deleted~~"
        result = org_to_plain_text(md)
        self.assertNotIn('~~', result)
        self.assertIn('deleted', result)


# ---------------------------------------------------------------------------
# process_org_file (file I/O)
# ---------------------------------------------------------------------------

class TestProcessOrgFile(unittest.TestCase):
    def test_creates_md_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            org_path = tmpdir_path / "test.org"
            org_path.write_text(SAMPLE_ORG, encoding='utf-8')
            out_dir = tmpdir_path / "out"

            out_path = process_org_file(org_path, out_dir, 'md')

            self.assertTrue(out_path.exists())
            self.assertEqual(out_path.suffix, '.md')
            self.assertEqual(out_path.stem, 'test')

    def test_frontmatter_in_md_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            org_path = tmpdir_path / "doc.org"
            org_path.write_text(SAMPLE_ORG, encoding='utf-8')

            out_path = process_org_file(org_path, tmpdir_path / "out", 'md')
            content = out_path.read_text(encoding='utf-8')

            self.assertIn('---', content)
            self.assertIn('fetched_at:', content)
            self.assertIn('title:', content)

    def test_txt_format_produces_txt_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            org_path = tmpdir_path / "doc.org"
            org_path.write_text(MINIMAL_ORG, encoding='utf-8')

            out_path = process_org_file(org_path, tmpdir_path / "out", 'txt')
            self.assertEqual(out_path.suffix, '.txt')
            content = out_path.read_text(encoding='utf-8')
            self.assertNotIn('fetched_at:', content)

    def test_output_dir_created_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            org_path = Path(tmpdir) / "doc.org"
            org_path.write_text(SAMPLE_ORG, encoding='utf-8')
            new_dir = Path(tmpdir) / "deeply" / "nested" / "dir"

            out_path = process_org_file(org_path, new_dir, 'md')
            self.assertTrue(out_path.exists())


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    def _runner(self):
        from typer.testing import CliRunner
        return CliRunner()

    def test_help_exits_cleanly(self):
        from any2md.org import app
        result = self._runner().invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("org", result.output.lower())

    def test_single_file_end_to_end(self):
        from any2md.org import app
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            org_path = tmpdir_path / "readme.org"
            org_path.write_text(SAMPLE_ORG, encoding='utf-8')
            out_dir = tmpdir_path / "out"

            result = self._runner().invoke(app, [str(org_path), "-o", str(out_dir)])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            out_file = out_dir / "readme.md"
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding='utf-8')
            self.assertIn('---', content)
            self.assertIn('Introduction', content)

    def test_batch_directory_mode(self):
        from any2md.org import app
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "a.org").write_text(SAMPLE_ORG, encoding='utf-8')
            (tmpdir_path / "b.org").write_text(MINIMAL_ORG, encoding='utf-8')
            out_dir = tmpdir_path / "out"

            result = self._runner().invoke(app, [str(tmpdir_path), "-o", str(out_dir)])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertTrue((out_dir / "a.md").exists())
            self.assertTrue((out_dir / "b.md").exists())

    def test_empty_directory_exits_with_error(self):
        from any2md.org import app
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._runner().invoke(app, [tmpdir])
            self.assertNotEqual(result.exit_code, 0)

    def test_missing_file_exits_with_error(self):
        from any2md.org import app
        result = self._runner().invoke(app, ["/nonexistent/path/file.org"])
        self.assertNotEqual(result.exit_code, 0)

    def test_txt_format_flag(self):
        from any2md.org import app
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            org_path = tmpdir_path / "doc.org"
            org_path.write_text(SAMPLE_ORG, encoding='utf-8')
            out_dir = tmpdir_path / "out"

            result = self._runner().invoke(app, [str(org_path), "-o", str(out_dir), "-f", "txt"])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            out_file = out_dir / "doc.txt"
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding='utf-8')
            self.assertNotIn('fetched_at:', content)


if __name__ == "__main__":
    unittest.main()
