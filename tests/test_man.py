#!/usr/bin/env python3
"""
test_man.py - Unit tests for man.py (Unix man page → markdown converter)

Tests cover:
- extract_man_metadata / _parse_th: .TH macro → frontmatter fields
- man_to_markdown_regex: troff macro parsing (SH, SS, B, I, BR, TP, PP, nf/fi)
- _expand_font_escapes: \\fB/\\fI/\\fR inline font escape expansion
- _html_to_markdown: HTML→markdown stripping helper
- man_to_full_markdown / man_to_plain_text: output formatters
- process_man_file: file I/O, frontmatter in output, txt mode
- CLI: help, single file, batch directory, missing file
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from any2md.man import (
    man_to_markdown_regex,
    extract_man_metadata,
    man_to_full_markdown,
    man_to_plain_text,
    process_man_file,
    _expand_font_escapes,
    _html_to_markdown,
    _strip_tags,
)


# ---------------------------------------------------------------------------
# Minimal man page fixture
# ---------------------------------------------------------------------------

SAMPLE_MAN = r""".TH TESTCMD 1 "2026-01-15" "Test Suite 1.0" "Test Manual"
.\"
.\" This is a comment line — should be ignored
.\"
.SH NAME
testcmd \- a test command for unit testing
.SH SYNOPSIS
.B testcmd
[\fB\-v\fR]
[\fB\-o\fR \fIoutfile\fR]
\fIinput\fR
.SH DESCRIPTION
The
.B testcmd
utility processes input files.
It supports multiple options.
.PP
A second paragraph starts here.
.SS Sub-section Header
Content in the subsection.
.SH OPTIONS
.TP
.B \-v
Enable verbose output.
.TP
.B \-o \fIoutfile\fR
Write output to
.I outfile
instead of stdout.
.SH FILES
.nf
/etc/testcmd.conf
/var/log/testcmd.log
.fi
.SH "SEE ALSO"
.BR ls (1),
.BR cat (1)
.SH AUTHOR
Jane Doe <jane@example.com>
"""

MINIMAL_MAN = r""".TH MINI 3 "2025-06-01"
.SH NAME
mini \- minimal man page
.SH DESCRIPTION
Minimal content only.
"""

NO_TH_MAN = r""".SH NAME
noheader \- page without TH
.SH DESCRIPTION
No header macro present.
"""


# ---------------------------------------------------------------------------
# _expand_font_escapes
# ---------------------------------------------------------------------------

class TestExpandFontEscapes(unittest.TestCase):
    def test_bold_escape(self):
        result = _expand_font_escapes(r'\fBhello\fR')
        self.assertEqual(result, '**hello**')

    def test_bold_escape_fp(self):
        result = _expand_font_escapes(r'\fBhello\fP')
        self.assertEqual(result, '**hello**')

    def test_italic_escape(self):
        result = _expand_font_escapes(r'\fIworld\fR')
        self.assertEqual(result, '*world*')

    def test_mixed_bold_italic(self):
        text = r'\fBbold\fR and \fIitalic\fR'
        result = _expand_font_escapes(text)
        self.assertIn('**bold**', result)
        self.assertIn('*italic*', result)

    def test_hyphen_escape(self):
        result = _expand_font_escapes(r'foo\-bar')
        self.assertEqual(result, 'foo-bar')

    def test_copyright_escape(self):
        result = _expand_font_escapes(r'\(co 2026')
        self.assertIn('©', result)

    def test_no_escapes(self):
        result = _expand_font_escapes('plain text')
        self.assertEqual(result, 'plain text')

    def test_word_joiner_removed(self):
        result = _expand_font_escapes(r'foo\&bar')
        self.assertEqual(result, 'foobar')


# ---------------------------------------------------------------------------
# man_to_markdown_regex — .TH macro
# ---------------------------------------------------------------------------

class TestTHParsing(unittest.TestCase):
    def _parse(self, content: str):
        _, metadata = man_to_markdown_regex(content)
        return metadata

    def test_th_name(self):
        meta = self._parse(SAMPLE_MAN)
        self.assertEqual(meta.get('name'), 'TESTCMD')

    def test_th_section(self):
        meta = self._parse(SAMPLE_MAN)
        self.assertEqual(meta.get('section'), '1')

    def test_th_date(self):
        meta = self._parse(SAMPLE_MAN)
        self.assertEqual(meta.get('date'), '2026-01-15')

    def test_th_source(self):
        meta = self._parse(SAMPLE_MAN)
        self.assertEqual(meta.get('source'), 'Test Suite 1.0')

    def test_th_manual(self):
        meta = self._parse(SAMPLE_MAN)
        self.assertEqual(meta.get('manual'), 'Test Manual')

    def test_minimal_th_no_source_manual(self):
        meta = self._parse(MINIMAL_MAN)
        self.assertEqual(meta.get('name'), 'MINI')
        self.assertEqual(meta.get('section'), '3')
        # source and manual not present in MINIMAL_MAN
        self.assertNotIn('source', meta)
        self.assertNotIn('manual', meta)

    def test_no_th_macro(self):
        meta = self._parse(NO_TH_MAN)
        # No .TH → no th fields in metadata
        self.assertNotIn('name', meta)
        self.assertNotIn('section', meta)


# ---------------------------------------------------------------------------
# man_to_markdown_regex — .SH headings
# ---------------------------------------------------------------------------

class TestSHHeadings(unittest.TestCase):
    def _md(self, content: str) -> str:
        md, _ = man_to_markdown_regex(content)
        return md

    def test_sh_becomes_h2(self):
        md = self._md('.SH NAME\ntest\n')
        self.assertIn('## NAME', md)

    def test_ss_becomes_h3(self):
        md = self._md('.SH TOP\n.SS Sub\ncontent\n')
        self.assertIn('### Sub', md)

    def test_multiple_sections(self):
        md = self._md('.SH DESCRIPTION\nbody\n.SH OPTIONS\nopts\n')
        self.assertIn('## DESCRIPTION', md)
        self.assertIn('## OPTIONS', md)

    def test_quoted_sh(self):
        md = self._md('.SH "SEE ALSO"\nreferences\n')
        self.assertIn('## SEE ALSO', md)

    def test_full_sample_has_sections(self):
        md = self._md(SAMPLE_MAN)
        self.assertIn('## NAME', md)
        self.assertIn('## DESCRIPTION', md)
        self.assertIn('## OPTIONS', md)


# ---------------------------------------------------------------------------
# man_to_markdown_regex — .B/.I bold/italic
# ---------------------------------------------------------------------------

class TestBoldItalic(unittest.TestCase):
    def _md(self, content: str) -> str:
        md, _ = man_to_markdown_regex(content)
        return md

    def test_dot_b_bold(self):
        md = self._md('.B bold text\n')
        self.assertIn('**bold text**', md)

    def test_dot_i_italic(self):
        md = self._md('.I italic text\n')
        self.assertIn('*italic text*', md)

    def test_dot_br_bold(self):
        md = self._md('.BR ls (1)\n')
        self.assertIn('**', md)
        self.assertIn('ls', md)

    def test_inline_fB_bold(self):
        md = self._md(r'This is \fBbold\fR text.' + '\n')
        self.assertIn('**bold**', md)

    def test_inline_fI_italic(self):
        md = self._md(r'This is \fIitalic\fR text.' + '\n')
        self.assertIn('*italic*', md)


# ---------------------------------------------------------------------------
# man_to_markdown_regex — .TP definition list
# ---------------------------------------------------------------------------

class TestTPDefinitionList(unittest.TestCase):
    def _md(self, content: str) -> str:
        md, _ = man_to_markdown_regex(content)
        return md

    def test_tp_term_present(self):
        content = '.SH OPTIONS\n.TP\n.B \\-v\nEnable verbose.\n'
        md = self._md(content)
        self.assertIn('**-v**', md)

    def test_tp_definition_present(self):
        content = '.SH OPTIONS\n.TP\n.B \\-v\nEnable verbose mode.\n'
        md = self._md(content)
        self.assertIn('Enable verbose mode', md)

    def test_tp_multiple_entries(self):
        content = (
            '.SH OPTIONS\n'
            '.TP\n.B \\-a\nFirst option.\n'
            '.TP\n.B \\-b\nSecond option.\n'
        )
        md = self._md(content)
        self.assertIn('**-a**', md)
        self.assertIn('**-b**', md)
        self.assertIn('First option', md)
        self.assertIn('Second option', md)

    def test_tp_in_full_sample(self):
        md = self._md(SAMPLE_MAN)
        # Sample has .TP entries for -v and -o
        self.assertIn('-v', md)
        self.assertIn('verbose', md.lower())


# ---------------------------------------------------------------------------
# man_to_markdown_regex — .nf/.fi preformatted block
# ---------------------------------------------------------------------------

class TestNfFiCodeBlock(unittest.TestCase):
    def _md(self, content: str) -> str:
        md, _ = man_to_markdown_regex(content)
        return md

    def test_nf_fi_produces_code_fence(self):
        content = '.SH FILES\n.nf\n/etc/myapp.conf\n/var/log/myapp.log\n.fi\n'
        md = self._md(content)
        self.assertIn('```', md)
        self.assertIn('/etc/myapp.conf', md)
        self.assertIn('/var/log/myapp.log', md)

    def test_preformatted_not_reformatted(self):
        content = '.nf\n    indented line\n    another line\n.fi\n'
        md = self._md(content)
        self.assertIn('```', md)
        self.assertIn('indented line', md)

    def test_full_sample_has_code_block(self):
        md = self._md(SAMPLE_MAN)
        self.assertIn('```', md)
        self.assertIn('/etc/testcmd.conf', md)


# ---------------------------------------------------------------------------
# man_to_markdown_regex — .PP paragraph break
# ---------------------------------------------------------------------------

class TestParagraphBreak(unittest.TestCase):
    def _md(self, content: str) -> str:
        md, _ = man_to_markdown_regex(content)
        return md

    def test_pp_creates_blank_line(self):
        content = 'First paragraph.\n.PP\nSecond paragraph.\n'
        md = self._md(content)
        self.assertIn('First paragraph', md)
        self.assertIn('Second paragraph', md)

    def test_p_macro_works_too(self):
        content = 'Para one.\n.P\nPara two.\n'
        md = self._md(content)
        self.assertIn('Para one', md)
        self.assertIn('Para two', md)


# ---------------------------------------------------------------------------
# _html_to_markdown helper
# ---------------------------------------------------------------------------

class TestHtmlToMarkdown(unittest.TestCase):
    def test_headings(self):
        html = '<h1>Title</h1><h2>Section</h2>'
        result = _html_to_markdown(html)
        self.assertIn('# Title', result)
        self.assertIn('## Section', result)

    def test_bold(self):
        html = '<p><b>bold</b> and <strong>strong</strong></p>'
        result = _html_to_markdown(html)
        self.assertIn('**bold**', result)
        self.assertIn('**strong**', result)

    def test_italic(self):
        html = '<p><i>italic</i> and <em>em</em></p>'
        result = _html_to_markdown(html)
        self.assertIn('*italic*', result)
        self.assertIn('*em*', result)

    def test_code_inline(self):
        html = '<p><code>ls -la</code></p>'
        result = _html_to_markdown(html)
        self.assertIn('`ls -la`', result)

    def test_pre_block(self):
        html = '<pre>/etc/hosts\n/etc/passwd</pre>'
        result = _html_to_markdown(html)
        self.assertIn('```', result)
        self.assertIn('/etc/hosts', result)

    def test_html_entities(self):
        html = '<p>a &amp; b &lt; c &gt; d</p>'
        result = _html_to_markdown(html)
        self.assertIn('a & b < c > d', result)

    def test_definition_list(self):
        html = '<dl><dt><b>-v</b></dt><dd>Enable verbose.</dd></dl>'
        result = _html_to_markdown(html)
        self.assertIn('-v', result)
        self.assertIn('Enable verbose', result)

    def test_strips_remaining_tags(self):
        html = '<div><span>plain</span></div>'
        result = _html_to_markdown(html)
        self.assertNotIn('<', result)
        self.assertIn('plain', result)


# ---------------------------------------------------------------------------
# extract_man_metadata
# ---------------------------------------------------------------------------

class TestExtractManMetadata(unittest.TestCase):
    def _meta(self, content: str) -> dict:
        with tempfile.NamedTemporaryFile(suffix='.1', delete=False, mode='w', encoding='utf-8') as f:
            f.write(content)
            path = Path(f.name)
        try:
            return extract_man_metadata(path)
        finally:
            path.unlink(missing_ok=True)

    def test_name_in_metadata(self):
        meta = self._meta(SAMPLE_MAN)
        self.assertEqual(meta.get('name'), 'TESTCMD')

    def test_section_in_metadata(self):
        meta = self._meta(SAMPLE_MAN)
        self.assertEqual(meta.get('section'), '1')

    def test_date_in_metadata(self):
        meta = self._meta(SAMPLE_MAN)
        self.assertEqual(meta.get('date'), '2026-01-15')

    def test_source_file_present(self):
        meta = self._meta(SAMPLE_MAN)
        self.assertIn('source_file', meta)
        self.assertTrue(Path(meta['source_file']).is_absolute())

    def test_fetched_at_present(self):
        meta = self._meta(SAMPLE_MAN)
        self.assertIn('fetched_at', meta)
        from datetime import datetime
        datetime.strptime(meta['fetched_at'], '%Y-%m-%dT%H:%M:%SZ')

    def test_no_th_minimal_metadata(self):
        meta = self._meta(NO_TH_MAN)
        # Should still have source_file and fetched_at
        self.assertIn('source_file', meta)
        self.assertIn('fetched_at', meta)
        # But no TH fields
        self.assertNotIn('name', meta)


# ---------------------------------------------------------------------------
# man_to_full_markdown / man_to_plain_text
# ---------------------------------------------------------------------------

class TestOutputFormatters(unittest.TestCase):
    def test_full_markdown_includes_frontmatter(self):
        meta = {'name': 'ls', 'section': '1', 'fetched_at': '2026-03-10T00:00:00Z'}
        result = man_to_full_markdown('## NAME\nls - list files', metadata=meta)
        self.assertIn('---', result)
        self.assertIn('name:', result)
        self.assertIn('## NAME', result)

    def test_full_markdown_no_metadata(self):
        result = man_to_full_markdown('## NAME\nls', metadata=None)
        self.assertNotIn('---', result)
        self.assertIn('## NAME', result)

    def test_plain_text_strips_headings(self):
        md = '## DESCRIPTION\n\nSome content.\n'
        result = man_to_plain_text(md)
        self.assertNotIn('#', result)
        self.assertIn('DESCRIPTION', result)
        self.assertIn('Some content', result)

    def test_plain_text_strips_bold(self):
        md = 'Use **-v** for verbose.\n'
        result = man_to_plain_text(md)
        self.assertNotIn('**', result)
        self.assertIn('-v', result)

    def test_plain_text_strips_code_fences(self):
        md = '```\n/etc/hosts\n```\n'
        result = man_to_plain_text(md)
        self.assertNotIn('```', result)
        self.assertIn('/etc/hosts', result)


# ---------------------------------------------------------------------------
# process_man_file (file I/O)
# ---------------------------------------------------------------------------

class TestProcessManFile(unittest.TestCase):
    def test_creates_md_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            man_path = tmpdir_path / 'testcmd.1'
            man_path.write_text(SAMPLE_MAN, encoding='utf-8')
            out_dir = tmpdir_path / 'out'

            out_path = process_man_file(man_path, out_dir, 'md')

            self.assertTrue(out_path.exists())
            self.assertEqual(out_path.suffix, '.md')
            self.assertEqual(out_path.stem, 'testcmd')

    def test_frontmatter_in_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            man_path = tmpdir_path / 'testcmd.1'
            man_path.write_text(SAMPLE_MAN, encoding='utf-8')

            out_path = process_man_file(man_path, tmpdir_path / 'out', 'md')
            content = out_path.read_text(encoding='utf-8')

            self.assertIn('---', content)
            self.assertIn('fetched_at:', content)

    def test_txt_format_no_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            man_path = tmpdir_path / 'mini.1'
            man_path.write_text(MINIMAL_MAN, encoding='utf-8')

            out_path = process_man_file(man_path, tmpdir_path / 'out', 'txt')
            self.assertEqual(out_path.suffix, '.txt')
            content = out_path.read_text(encoding='utf-8')
            self.assertNotIn('fetched_at:', content)

    def test_output_dir_created_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            man_path = Path(tmpdir) / 'test.1'
            man_path.write_text(MINIMAL_MAN, encoding='utf-8')
            new_dir = Path(tmpdir) / 'deeply' / 'nested' / 'dir'

            out_path = process_man_file(man_path, new_dir, 'md')
            self.assertTrue(out_path.exists())

    def test_name_in_output_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            man_path = tmpdir_path / 'testcmd.1'
            man_path.write_text(SAMPLE_MAN, encoding='utf-8')

            out_path = process_man_file(man_path, tmpdir_path / 'out', 'md')
            content = out_path.read_text(encoding='utf-8')
            self.assertIn('TESTCMD', content)


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    def test_help_exits_cleanly(self):
        from typer.testing import CliRunner
        from any2md.man import app

        runner = CliRunner()
        result = runner.invoke(app, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('man', result.output.lower())

    def test_single_file_end_to_end(self):
        from typer.testing import CliRunner
        from any2md.man import app

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            man_path = tmpdir_path / 'testcmd.1'
            man_path.write_text(SAMPLE_MAN, encoding='utf-8')
            out_dir = tmpdir_path / 'out'

            runner = CliRunner()
            result = runner.invoke(app, [str(man_path), '-o', str(out_dir)])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            out_file = out_dir / 'testcmd.md'
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding='utf-8')
            self.assertIn('---', content)

    def test_txt_format_flag(self):
        from typer.testing import CliRunner
        from any2md.man import app

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            man_path = tmpdir_path / 'mini.1'
            man_path.write_text(MINIMAL_MAN, encoding='utf-8')
            out_dir = tmpdir_path / 'out'

            runner = CliRunner()
            result = runner.invoke(app, [str(man_path), '-o', str(out_dir), '-f', 'txt'])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            out_file = out_dir / 'mini.txt'
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding='utf-8')
            self.assertNotIn('fetched_at:', content)

    def test_missing_file_exits_with_error(self):
        from typer.testing import CliRunner
        from any2md.man import app

        runner = CliRunner()
        result = runner.invoke(app, ['/nonexistent/path/file.1'])
        self.assertNotEqual(result.exit_code, 0)

    def test_batch_directory_mode(self):
        from typer.testing import CliRunner
        from any2md.man import app

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / 'a.1').write_text(SAMPLE_MAN, encoding='utf-8')
            (tmpdir_path / 'b.3').write_text(MINIMAL_MAN, encoding='utf-8')
            out_dir = tmpdir_path / 'out'

            runner = CliRunner()
            result = runner.invoke(app, [str(tmpdir_path), '-o', str(out_dir)])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertTrue((out_dir / 'a.md').exists())
            self.assertTrue((out_dir / 'b.md').exists())

    def test_empty_directory_exits_with_error(self):
        from typer.testing import CliRunner
        from any2md.man import app

        with tempfile.TemporaryDirectory() as tmpdir:
            runner = CliRunner()
            result = runner.invoke(app, [tmpdir])
            self.assertNotEqual(result.exit_code, 0)


if __name__ == '__main__':
    unittest.main()
