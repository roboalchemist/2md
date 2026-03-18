#!/usr/bin/env python3
"""
test_eml.py - Unit tests for eml.py

Tests cover:
- _decode_header_value: RFC 2047 encoded headers
- _parse_address: name + address formatting
- _parse_date: date parsing to ISO-8601
- _html_to_markdown: HTML-to-markdown conversion
- extract_email_metadata: header fields → metadata dict
- _extract_body_and_attachments: plain text, HTML, and multipart
- email_to_markdown: full markdown and plain-text output assembly
- process_eml_file: file I/O, frontmatter in output
- process_mbox_file: multiple messages, numbered output files
- CLI (main): single file, missing file, mbox, txt format
"""

import email
import email.policy
import mailbox
import tempfile
import unittest
from pathlib import Path

from any2md.eml import (
    _decode_header_value,
    _html_to_markdown,
    _parse_address,
    _parse_date,
    _strip_tags,
    email_to_markdown,
    extract_email_metadata,
    process_eml_file,
    process_mbox_file,
    _extract_body_and_attachments,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

SIMPLE_EML = """\
From: Alice Smith <alice@example.com>
To: Bob Jones <bob@example.com>
Cc: Carol <carol@example.com>
Subject: Test Subject Line
Date: Mon, 15 Jan 2024 10:30:00 +0000
Message-ID: <abc123@mail.example.com>
In-Reply-To: <prev456@mail.example.com>
Content-Type: text/plain; charset=utf-8

Hello Bob,

This is the body of the test email.
It has multiple lines.

Regards,
Alice
"""

HTML_EML = """\
From: Alice <alice@example.com>
To: Bob <bob@example.com>
Subject: HTML Email
Date: Tue, 16 Jan 2024 09:00:00 +0000
Content-Type: text/html; charset=utf-8

<html><body>
<p>Hello <strong>Bob</strong>,</p>
<p>Click <a href="https://example.com">here</a> for details.</p>
<ul><li>Item one</li><li>Item two</li></ul>
</body></html>
"""

MULTIPART_EML = """\
From: Alice <alice@example.com>
To: Bob <bob@example.com>
Subject: Multipart with Attachment
Date: Wed, 17 Jan 2024 08:00:00 +0000
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="boundary42"

--boundary42
Content-Type: text/plain; charset=utf-8

Plain text body here.

--boundary42
Content-Type: application/pdf
Content-Disposition: attachment; filename="report.pdf"

%PDF-1.4 fake binary content

--boundary42
Content-Type: image/jpeg
Content-Disposition: attachment; filename="photo.jpg"

JFIF fake binary content

--boundary42--
"""

MULTIPART_HTML_EML = """\
From: Sender <sender@example.com>
To: Recipient <recipient@example.com>
Subject: Multipart HTML with Plain Fallback
Date: Thu, 18 Jan 2024 12:00:00 +0000
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="alt_boundary"

--alt_boundary
Content-Type: text/plain; charset=utf-8

Plain text version.

--alt_boundary
Content-Type: text/html; charset=utf-8

<html><body><p>HTML version with <em>italic</em> text.</p></body></html>

--alt_boundary--
"""


def _parse_eml(raw: str) -> email.message.Message:
    """Helper: parse a raw RFC 822 string into a Message object."""
    return email.message_from_string(raw, policy=email.policy.compat32)


def _write_eml(raw: str, suffix: str = '.eml') -> Path:
    """Write raw EML text to a temp file and return its Path."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix=suffix, delete=False, encoding='utf-8'
    ) as f:
        f.write(raw)
        return Path(f.name)


# ---------------------------------------------------------------------------
# _decode_header_value
# ---------------------------------------------------------------------------

class TestDecodeHeaderValue(unittest.TestCase):
    def test_plain_ascii(self):
        self.assertEqual(_decode_header_value('Hello World'), 'Hello World')

    def test_none_returns_empty(self):
        self.assertEqual(_decode_header_value(None), '')

    def test_empty_string(self):
        self.assertEqual(_decode_header_value(''), '')

    def test_rfc2047_encoded(self):
        # UTF-8 encoded "Subject: Héllo"
        encoded = '=?utf-8?q?H=C3=A9llo?='
        result = _decode_header_value(encoded)
        self.assertEqual(result, 'Héllo')


# ---------------------------------------------------------------------------
# _parse_address
# ---------------------------------------------------------------------------

class TestParseAddress(unittest.TestCase):
    def test_name_and_addr(self):
        result = _parse_address('Alice Smith <alice@example.com>')
        self.assertIn('Alice Smith', result)
        self.assertIn('alice@example.com', result)

    def test_addr_only(self):
        result = _parse_address('alice@example.com')
        self.assertEqual(result, 'alice@example.com')

    def test_none_returns_empty(self):
        self.assertEqual(_parse_address(None), '')

    def test_empty_returns_empty(self):
        self.assertEqual(_parse_address(''), '')


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------

class TestParseDate(unittest.TestCase):
    def test_rfc2822_date(self):
        result = _parse_date('Mon, 15 Jan 2024 10:30:00 +0000')
        self.assertEqual(result, '2024-01-15T10:30:00Z')

    def test_date_with_timezone_offset(self):
        # +0530 should be converted to UTC
        result = _parse_date('Mon, 15 Jan 2024 16:00:00 +0530')
        self.assertEqual(result, '2024-01-15T10:30:00Z')

    def test_none_returns_empty(self):
        self.assertEqual(_parse_date(None), '')

    def test_invalid_date_returns_raw(self):
        result = _parse_date('not a date at all')
        self.assertEqual(result, 'not a date at all')


# ---------------------------------------------------------------------------
# _html_to_markdown
# ---------------------------------------------------------------------------

class TestHtmlToMarkdown(unittest.TestCase):
    def test_paragraph_to_text(self):
        result = _html_to_markdown('<p>Hello world.</p>')
        self.assertIn('Hello world.', result)
        self.assertNotIn('<p>', result)

    def test_bold_conversion(self):
        result = _html_to_markdown('<p><strong>bold</strong> and <b>also bold</b></p>')
        self.assertIn('**bold**', result)
        self.assertIn('**also bold**', result)

    def test_italic_conversion(self):
        result = _html_to_markdown('<p><em>italic</em> and <i>also italic</i></p>')
        self.assertIn('*italic*', result)
        self.assertIn('*also italic*', result)

    def test_link_conversion(self):
        result = _html_to_markdown('<a href="https://example.com">Click here</a>')
        self.assertIn('[Click here](https://example.com)', result)

    def test_br_to_newline(self):
        result = _html_to_markdown('Line one<br>Line two')
        self.assertIn('\n', result)
        self.assertIn('Line one', result)
        self.assertIn('Line two', result)

    def test_list_items(self):
        result = _html_to_markdown('<ul><li>Item A</li><li>Item B</li></ul>')
        self.assertIn('- Item A', result)
        self.assertIn('- Item B', result)

    def test_headings(self):
        result = _html_to_markdown('<h1>Title</h1><h2>Subtitle</h2>')
        self.assertIn('# Title', result)
        self.assertIn('## Subtitle', result)

    def test_html_entities(self):
        result = _html_to_markdown('<p>a &amp; b &lt; c &gt; d &nbsp; e</p>')
        self.assertIn('a & b < c > d', result)

    def test_strips_unknown_tags(self):
        result = _html_to_markdown('<div><span>plain text</span></div>')
        self.assertNotIn('<div>', result)
        self.assertNotIn('<span>', result)
        self.assertIn('plain text', result)

    def test_body_extraction(self):
        full_html = '<html><head><title>X</title></head><body><p>Content</p></body></html>'
        result = _html_to_markdown(full_html)
        self.assertNotIn('<head>', result)
        self.assertIn('Content', result)


# ---------------------------------------------------------------------------
# extract_email_metadata
# ---------------------------------------------------------------------------

class TestExtractEmailMetadata(unittest.TestCase):
    def _meta(self, raw: str = SIMPLE_EML) -> dict:
        msg = _parse_eml(raw)
        path = Path('/tmp/test.eml')
        return extract_email_metadata(msg, path)

    def test_subject(self):
        meta = self._meta()
        self.assertEqual(meta.get('subject'), 'Test Subject Line')

    def test_from(self):
        meta = self._meta()
        self.assertIn('alice@example.com', meta.get('from', ''))

    def test_to(self):
        meta = self._meta()
        self.assertIn('bob@example.com', meta.get('to', ''))

    def test_cc(self):
        meta = self._meta()
        self.assertIn('carol@example.com', meta.get('cc', ''))

    def test_date_iso8601(self):
        meta = self._meta()
        self.assertEqual(meta.get('date'), '2024-01-15T10:30:00Z')

    def test_message_id(self):
        meta = self._meta()
        self.assertIn('abc123', meta.get('message_id', ''))

    def test_in_reply_to(self):
        meta = self._meta()
        self.assertIn('prev456', meta.get('in_reply_to', ''))

    def test_content_type(self):
        meta = self._meta()
        self.assertIn('text/plain', meta.get('content_type', ''))

    def test_source_present(self):
        meta = self._meta()
        self.assertIn('source', meta)

    def test_fetched_at_present(self):
        meta = self._meta()
        self.assertIn('fetched_at', meta)
        from datetime import datetime
        datetime.strptime(meta['fetched_at'], '%Y-%m-%dT%H:%M:%SZ')

    def test_missing_optional_fields_omitted(self):
        minimal = "From: a@b.com\nTo: c@d.com\nSubject: Hi\n\nBody\n"
        meta = self._meta(minimal)
        self.assertNotIn('cc', meta)
        self.assertNotIn('in_reply_to', meta)


# ---------------------------------------------------------------------------
# _extract_body_and_attachments
# ---------------------------------------------------------------------------

class TestExtractBodyAndAttachments(unittest.TestCase):
    def test_plain_text_body(self):
        msg = _parse_eml(SIMPLE_EML)
        body, attachments = _extract_body_and_attachments(msg)
        self.assertIn('Hello Bob', body)
        self.assertEqual(attachments, [])

    def test_html_body_converted(self):
        msg = _parse_eml(HTML_EML)
        body, attachments = _extract_body_and_attachments(msg)
        self.assertIn('**Bob**', body)
        self.assertIn('[here](https://example.com)', body)
        self.assertEqual(attachments, [])

    def test_attachment_listing(self):
        msg = _parse_eml(MULTIPART_EML)
        body, attachments = _extract_body_and_attachments(msg)
        self.assertIn('report.pdf', attachments)
        self.assertIn('photo.jpg', attachments)

    def test_multipart_prefers_html(self):
        msg = _parse_eml(MULTIPART_HTML_EML)
        body, attachments = _extract_body_and_attachments(msg)
        # HTML version should win; should have italic markdown
        self.assertIn('*italic*', body)

    def test_plain_text_body_in_multipart(self):
        msg = _parse_eml(MULTIPART_EML)
        body, _ = _extract_body_and_attachments(msg)
        self.assertIn('Plain text body here', body)


# ---------------------------------------------------------------------------
# email_to_markdown
# ---------------------------------------------------------------------------

class TestEmailToMarkdown(unittest.TestCase):
    def _convert(self, raw: str = SIMPLE_EML, fmt: str = 'md') -> str:
        msg = _parse_eml(raw)
        return email_to_markdown(msg, Path('/tmp/test.eml'), fmt)

    def test_frontmatter_present_in_md(self):
        result = self._convert(fmt='md')
        self.assertIn('---', result)
        self.assertIn('subject:', result)

    def test_subject_as_h1(self):
        result = self._convert(fmt='md')
        self.assertIn('# Test Subject Line', result)

    def test_body_in_output(self):
        result = self._convert(fmt='md')
        self.assertIn('Hello Bob', result)

    def test_txt_format_no_frontmatter(self):
        result = self._convert(fmt='txt')
        self.assertNotIn('---', result)
        self.assertNotIn('fetched_at:', result)
        self.assertIn('Hello Bob', result)

    def test_txt_format_has_subject(self):
        result = self._convert(fmt='txt')
        self.assertIn('Test Subject Line', result)

    def test_attachments_in_frontmatter(self):
        result = self._convert(MULTIPART_EML, fmt='md')
        self.assertIn('attachments:', result)
        self.assertIn('report.pdf', result)
        self.assertIn('photo.jpg', result)

    def test_html_body_converted_in_md(self):
        result = self._convert(HTML_EML, fmt='md')
        self.assertIn('**Bob**', result)


# ---------------------------------------------------------------------------
# process_eml_file
# ---------------------------------------------------------------------------

class TestProcessEmlFile(unittest.TestCase):
    def test_creates_md_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            eml_path = _write_eml(SIMPLE_EML, '.eml')
            out_dir = Path(tmpdir) / 'out'
            try:
                out = process_eml_file(eml_path, out_dir, 'md')
                self.assertTrue(out.exists())
                self.assertEqual(out.suffix, '.md')
            finally:
                eml_path.unlink(missing_ok=True)

    def test_creates_txt_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            eml_path = _write_eml(SIMPLE_EML, '.eml')
            out_dir = Path(tmpdir) / 'out'
            try:
                out = process_eml_file(eml_path, out_dir, 'txt')
                self.assertEqual(out.suffix, '.txt')
            finally:
                eml_path.unlink(missing_ok=True)

    def test_frontmatter_in_md_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            eml_path = _write_eml(SIMPLE_EML, '.eml')
            out_dir = Path(tmpdir) / 'out'
            try:
                out = process_eml_file(eml_path, out_dir, 'md')
                content = out.read_text(encoding='utf-8')
                self.assertIn('---', content)
                self.assertIn('fetched_at:', content)
                self.assertIn('subject:', content)
            finally:
                eml_path.unlink(missing_ok=True)

    def test_output_dir_created_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            eml_path = _write_eml(SIMPLE_EML, '.eml')
            new_dir = Path(tmpdir) / 'deep' / 'nested' / 'dir'
            try:
                out = process_eml_file(eml_path, new_dir, 'md')
                self.assertTrue(out.exists())
            finally:
                eml_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# process_mbox_file
# ---------------------------------------------------------------------------

def _make_mbox(messages: list, path: Path) -> None:
    """Write a list of raw EML strings into an mbox file."""
    mbox = mailbox.mbox(str(path))
    mbox.lock()
    for raw in messages:
        msg = email.message_from_string(raw, policy=email.policy.compat32)
        mbox.add(msg)
    mbox.flush()
    mbox.unlock()
    mbox.close()


class TestProcessMboxFile(unittest.TestCase):
    def test_creates_one_file_per_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mbox_path = Path(tmpdir) / 'archive.mbox'
            _make_mbox([SIMPLE_EML, HTML_EML], mbox_path)
            out_dir = Path(tmpdir) / 'out'
            written = process_mbox_file(mbox_path, out_dir, 'md')
            self.assertEqual(len(written), 2)
            for p in written:
                self.assertTrue(p.exists())

    def test_files_are_numbered(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mbox_path = Path(tmpdir) / 'archive.mbox'
            _make_mbox([SIMPLE_EML, HTML_EML], mbox_path)
            out_dir = Path(tmpdir) / 'out'
            written = process_mbox_file(mbox_path, out_dir, 'md')
            names = [p.name for p in written]
            self.assertIn('archive_001.md', names)
            self.assertIn('archive_002.md', names)

    def test_empty_mbox_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mbox_path = Path(tmpdir) / 'empty.mbox'
            _make_mbox([], mbox_path)
            out_dir = Path(tmpdir) / 'out'
            written = process_mbox_file(mbox_path, out_dir, 'md')
            self.assertEqual(written, [])

    def test_each_file_has_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mbox_path = Path(tmpdir) / 'archive.mbox'
            _make_mbox([SIMPLE_EML], mbox_path)
            out_dir = Path(tmpdir) / 'out'
            written = process_mbox_file(mbox_path, out_dir, 'md')
            content = written[0].read_text(encoding='utf-8')
            self.assertIn('---', content)
            self.assertIn('fetched_at:', content)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    def _runner(self):
        from typer.testing import CliRunner
        return CliRunner()

    def test_help_exits_cleanly(self):
        from any2md.eml import app
        result = self._runner().invoke(app, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('eml', result.output.lower())

    def test_missing_file_exits_with_error(self):
        from any2md.eml import app
        result = self._runner().invoke(app, ['/nonexistent/path/msg.eml'])
        self.assertNotEqual(result.exit_code, 0)

    def test_single_eml_end_to_end(self):
        from any2md.eml import app
        with tempfile.TemporaryDirectory() as tmpdir:
            eml_path = _write_eml(SIMPLE_EML, '.eml')
            out_dir = Path(tmpdir) / 'out'
            try:
                result = self._runner().invoke(app, [str(eml_path), '-o', str(out_dir)])
                self.assertEqual(result.exit_code, 0, msg=result.output)
                out_files = list(out_dir.glob('*.md'))
                self.assertEqual(len(out_files), 1)
            finally:
                eml_path.unlink(missing_ok=True)

    def test_txt_format_flag(self):
        from any2md.eml import app
        with tempfile.TemporaryDirectory() as tmpdir:
            eml_path = _write_eml(SIMPLE_EML, '.eml')
            out_dir = Path(tmpdir) / 'out'
            try:
                result = self._runner().invoke(app, [str(eml_path), '-o', str(out_dir), '-f', 'txt'])
                self.assertEqual(result.exit_code, 0, msg=result.output)
                out_files = list(out_dir.glob('*.txt'))
                self.assertEqual(len(out_files), 1)
                content = out_files[0].read_text(encoding='utf-8')
                self.assertNotIn('fetched_at:', content)
            finally:
                eml_path.unlink(missing_ok=True)

    def test_mbox_end_to_end(self):
        from any2md.eml import app
        with tempfile.TemporaryDirectory() as tmpdir:
            mbox_path = Path(tmpdir) / 'archive.mbox'
            _make_mbox([SIMPLE_EML, HTML_EML], mbox_path)
            out_dir = Path(tmpdir) / 'out'
            result = self._runner().invoke(app, [str(mbox_path), '-o', str(out_dir)])
            self.assertEqual(result.exit_code, 0, msg=result.output)
            out_files = sorted(out_dir.glob('*.md'))
            self.assertEqual(len(out_files), 2)


if __name__ == '__main__':
    unittest.main()
