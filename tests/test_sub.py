#!/usr/bin/env python3
"""
test_sub.py - Unit tests for any2md.sub (subtitle to markdown converter)

Tests cover:
- format_timestamp_md: timestamp formatting (reused from yt)
- strip_html_tags: HTML tag removal and formatting conversion
- ms_to_seconds: millisecond conversion
- extract_subtitle_metadata: frontmatter fields, speaker extraction
- _merge_consecutive_speaker_lines: merging logic
- subs_to_markdown: SRT, ASS with speakers, HTML in text
- subs_to_plain_text: plain text output
- process_sub_file: file I/O, md and txt modes
- CLI: help, missing file, empty directory, single file end-to-end
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


import any2md.sub as sub_mod
from any2md.sub import (
    strip_html_tags,
    ms_to_seconds,
    extract_subtitle_metadata,
    _merge_consecutive_speaker_lines,
    subs_to_markdown,
    subs_to_plain_text,
    process_sub_file,
)
from any2md.yt import format_timestamp_md


# ---------------------------------------------------------------------------
# Sample subtitle content
# ---------------------------------------------------------------------------

SAMPLE_SRT = """\
1
00:00:01,000 --> 00:00:03,500
Hello world

2
00:00:04,000 --> 00:00:06,000
How are <i>you</i>?

3
00:00:06,500 --> 00:00:08,000
I am <b>doing great</b>!
"""

SAMPLE_ASS = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 384
PlayResY: 288

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.50,Default,Alice,0,0,0,,Hello there!
Dialogue: 0,0:00:04.00,0:00:06.00,Default,Bob,0,0,0,,How are you doing today?
Dialogue: 0,0:00:06.50,0:00:08.00,Default,Alice,0,0,0,,I am doing great!
Dialogue: 0,0:00:08.10,0:00:09.00,Default,Alice,0,0,0,,Thanks for asking.
"""

SAMPLE_VTT = """\
WEBVTT

00:00:01.000 --> 00:00:03.500
Hello world

00:00:04.000 --> 00:00:06.000
How are you?
"""


# ---------------------------------------------------------------------------
# Helpers for creating temp subtitle files
# ---------------------------------------------------------------------------

def _write_temp(content: str, suffix: str) -> Path:
    """Write content to a named temp file and return its Path."""
    f = tempfile.NamedTemporaryFile(
        suffix=suffix, mode='w', delete=False, encoding='utf-8'
    )
    f.write(content)
    f.close()
    return Path(f.name)


def _load(content: str, suffix: str):
    """Write content to a temp file, load via pysubs2, return (subs, path)."""
    import pysubs2
    path = _write_temp(content, suffix)
    subs = pysubs2.load(str(path))
    return subs, path


# ---------------------------------------------------------------------------
# format_timestamp_md (imported from yt, tested here for subtitle use)
# ---------------------------------------------------------------------------

class TestFormatTimestampMd(unittest.TestCase):
    def test_under_one_hour(self):
        self.assertEqual(format_timestamp_md(65.0), '01:05')

    def test_over_one_hour(self):
        self.assertEqual(format_timestamp_md(3661.0), '01:01:01')

    def test_zero(self):
        self.assertEqual(format_timestamp_md(0.0), '00:00')

    def test_exactly_one_minute(self):
        self.assertEqual(format_timestamp_md(60.0), '01:00')


# ---------------------------------------------------------------------------
# ms_to_seconds
# ---------------------------------------------------------------------------

class TestMsToSeconds(unittest.TestCase):
    def test_basic(self):
        self.assertAlmostEqual(ms_to_seconds(1000), 1.0)

    def test_fractional(self):
        self.assertAlmostEqual(ms_to_seconds(1500), 1.5)

    def test_zero(self):
        self.assertEqual(ms_to_seconds(0), 0.0)

    def test_large(self):
        self.assertAlmostEqual(ms_to_seconds(3661000), 3661.0)


# ---------------------------------------------------------------------------
# strip_html_tags
# ---------------------------------------------------------------------------

class TestStripHtmlTags(unittest.TestCase):
    def test_italic_converted_to_markdown(self):
        result = strip_html_tags('<i>hello</i>')
        self.assertEqual(result, '*hello*')

    def test_bold_converted_to_markdown(self):
        result = strip_html_tags('<b>world</b>')
        self.assertEqual(result, '**world**')

    def test_other_tags_stripped(self):
        result = strip_html_tags('<font color="red">text</font>')
        self.assertNotIn('<', result)
        self.assertIn('text', result)

    def test_no_tags_unchanged(self):
        result = strip_html_tags('plain text')
        self.assertEqual(result, 'plain text')

    def test_nested_tags(self):
        result = strip_html_tags('<i><b>both</b></i>')
        # Inner <b> converted first, then outer <i>
        self.assertIn('both', result)
        self.assertNotIn('<', result)

    def test_no_conversion_mode(self):
        result = strip_html_tags('<i>text</i>', convert_formatting=False)
        self.assertEqual(result, 'text')
        self.assertNotIn('*', result)


# ---------------------------------------------------------------------------
# extract_subtitle_metadata
# ---------------------------------------------------------------------------

class TestExtractSubtitleMetadata(unittest.TestCase):
    def setUp(self):
        self.srt_path = _write_temp(SAMPLE_SRT, '.srt')
        self.ass_path = _write_temp(SAMPLE_ASS, '.ass')

    def tearDown(self):
        self.srt_path.unlink(missing_ok=True)
        self.ass_path.unlink(missing_ok=True)

    def test_srt_basic_fields(self):
        import pysubs2
        subs = pysubs2.load(str(self.srt_path))
        meta = extract_subtitle_metadata(subs, self.srt_path)
        self.assertIn('source', meta)
        self.assertIn('fetched_at', meta)
        self.assertIn('subtitle_count', meta)
        self.assertIn('format', meta)

    def test_srt_subtitle_count(self):
        import pysubs2
        subs = pysubs2.load(str(self.srt_path))
        meta = extract_subtitle_metadata(subs, self.srt_path)
        self.assertEqual(meta['subtitle_count'], 3)

    def test_srt_format_detected(self):
        import pysubs2
        subs = pysubs2.load(str(self.srt_path))
        meta = extract_subtitle_metadata(subs, self.srt_path)
        self.assertEqual(meta['format'], 'srt')

    def test_srt_duration_set(self):
        import pysubs2
        subs = pysubs2.load(str(self.srt_path))
        meta = extract_subtitle_metadata(subs, self.srt_path)
        self.assertIn('duration', meta)
        self.assertGreater(meta['duration'], 0)

    def test_srt_no_speakers_field(self):
        import pysubs2
        subs = pysubs2.load(str(self.srt_path))
        meta = extract_subtitle_metadata(subs, self.srt_path)
        self.assertNotIn('speakers', meta)

    def test_ass_speakers_extracted(self):
        import pysubs2
        subs = pysubs2.load(str(self.ass_path))
        meta = extract_subtitle_metadata(subs, self.ass_path)
        self.assertIn('speakers', meta)
        self.assertIn('Alice', meta['speakers'])
        self.assertIn('Bob', meta['speakers'])

    def test_ass_speakers_order_preserved(self):
        """First speaker seen should come first in the list."""
        import pysubs2
        subs = pysubs2.load(str(self.ass_path))
        meta = extract_subtitle_metadata(subs, self.ass_path)
        self.assertEqual(meta['speakers'][0], 'Alice')
        self.assertEqual(meta['speakers'][1], 'Bob')

    def test_source_is_absolute(self):
        import pysubs2
        subs = pysubs2.load(str(self.srt_path))
        meta = extract_subtitle_metadata(subs, self.srt_path)
        self.assertTrue(Path(meta['source']).is_absolute())

    def test_fetched_at_is_iso8601(self):
        import pysubs2
        from datetime import datetime
        subs = pysubs2.load(str(self.srt_path))
        meta = extract_subtitle_metadata(subs, self.srt_path)
        datetime.strptime(meta['fetched_at'], '%Y-%m-%dT%H:%M:%SZ')


# ---------------------------------------------------------------------------
# _merge_consecutive_speaker_lines
# ---------------------------------------------------------------------------

class TestMergeConsecutiveSpeakerLines(unittest.TestCase):
    def _make_event(self, name: str, start_ms: int, text: str):
        """Create a minimal mock SSAEvent."""
        e = MagicMock()
        e.name = name
        e.start = start_ms
        e.text = text
        e.plaintext = text
        e.is_text = True
        return e

    def test_same_speaker_consecutive_merged(self):
        events = [
            self._make_event('Alice', 1000, 'Hello'),
            self._make_event('Alice', 2000, 'World'),
        ]
        result = _merge_consecutive_speaker_lines(events)
        self.assertEqual(len(result), 1)
        speaker, start, text = result[0]
        self.assertEqual(speaker, 'Alice')
        self.assertEqual(start, 1000)
        self.assertIn('Hello', text)
        self.assertIn('World', text)

    def test_different_speakers_not_merged(self):
        events = [
            self._make_event('Alice', 1000, 'Hello'),
            self._make_event('Bob', 2000, 'Hi'),
        ]
        result = _merge_consecutive_speaker_lines(events)
        self.assertEqual(len(result), 2)

    def test_alternating_speakers(self):
        events = [
            self._make_event('Alice', 1000, 'A1'),
            self._make_event('Bob', 2000, 'B1'),
            self._make_event('Alice', 3000, 'A2'),
        ]
        result = _merge_consecutive_speaker_lines(events)
        self.assertEqual(len(result), 3)

    def test_no_speaker_name_not_merged_with_named(self):
        events = [
            self._make_event('', 1000, 'Anonymous'),
            self._make_event('Alice', 2000, 'Named'),
        ]
        result = _merge_consecutive_speaker_lines(events)
        self.assertEqual(len(result), 2)

    def test_empty_events_skipped(self):
        events = [
            self._make_event('Alice', 1000, ''),
            self._make_event('Alice', 2000, 'Hello'),
        ]
        result = _merge_consecutive_speaker_lines(events)
        self.assertEqual(len(result), 1)
        self.assertIn('Hello', result[0][2])

    def test_preserves_first_start_time(self):
        events = [
            self._make_event('Alice', 1000, 'First'),
            self._make_event('Alice', 5000, 'Second'),
        ]
        result = _merge_consecutive_speaker_lines(events)
        self.assertEqual(result[0][1], 1000)


# ---------------------------------------------------------------------------
# subs_to_markdown (SRT)
# ---------------------------------------------------------------------------

class TestSubsToMarkdownSrt(unittest.TestCase):
    def setUp(self):
        self.path = _write_temp(SAMPLE_SRT, '.srt')
        import pysubs2
        self.subs = pysubs2.load(str(self.path))

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_contains_timestamp(self):
        result = subs_to_markdown(self.subs)
        # First event at 1 second -> [00:01]
        self.assertIn('[00:01]', result)

    def test_timestamp_bold_format(self):
        result = subs_to_markdown(self.subs)
        self.assertIn('**[', result)

    def test_text_present(self):
        result = subs_to_markdown(self.subs)
        self.assertIn('Hello world', result)

    def test_html_italic_converted(self):
        result = subs_to_markdown(self.subs)
        self.assertIn('*you*', result)
        self.assertNotIn('<i>', result)

    def test_html_bold_converted(self):
        result = subs_to_markdown(self.subs)
        self.assertIn('**doing great**', result)
        self.assertNotIn('<b>', result)

    def test_frontmatter_included_when_metadata_provided(self):
        meta = {'source': '/tmp/test.srt', 'subtitle_count': 3, 'fetched_at': '2026-03-18T00:00:00Z'}
        result = subs_to_markdown(self.subs, metadata=meta)
        self.assertIn('---', result)
        self.assertIn('subtitle_count:', result)

    def test_no_frontmatter_without_metadata(self):
        result = subs_to_markdown(self.subs)
        self.assertNotIn('---', result)


# ---------------------------------------------------------------------------
# subs_to_markdown (ASS with speakers)
# ---------------------------------------------------------------------------

class TestSubsToMarkdownAss(unittest.TestCase):
    def setUp(self):
        self.path = _write_temp(SAMPLE_ASS, '.ass')
        import pysubs2
        self.subs = pysubs2.load(str(self.path))

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_speaker_name_bold(self):
        result = subs_to_markdown(self.subs)
        self.assertIn('**Alice**', result)
        self.assertIn('**Bob**', result)

    def test_speaker_attribution_format(self):
        """Speaker line should be: **Name** [timestamp]"""
        result = subs_to_markdown(self.subs)
        self.assertRegex(result, r'\*\*Alice\*\* \[\d+:\d+\]')

    def test_consecutive_alice_lines_merged(self):
        """Alice's last two consecutive lines should be merged into one block."""
        result = subs_to_markdown(self.subs)
        # Alice appears at start and then twice at end — the last two are consecutive
        # We should see "Thanks for asking" in the same block as "I am doing great"
        alice_blocks = [line for line in result.split('\n') if '**Alice**' in line]
        # Alice should appear twice (first occurrence, then merged second+third)
        self.assertEqual(len(alice_blocks), 2)

    def test_all_text_present(self):
        result = subs_to_markdown(self.subs)
        self.assertIn('Hello there', result)
        self.assertIn('How are you doing today', result)
        self.assertIn('I am doing great', result)
        self.assertIn('Thanks for asking', result)


# ---------------------------------------------------------------------------
# subs_to_plain_text
# ---------------------------------------------------------------------------

class TestSubsToPlainText(unittest.TestCase):
    def setUp(self):
        self.srt_path = _write_temp(SAMPLE_SRT, '.srt')
        self.ass_path = _write_temp(SAMPLE_ASS, '.ass')
        import pysubs2
        self.srt_subs = pysubs2.load(str(self.srt_path))
        self.ass_subs = pysubs2.load(str(self.ass_path))

    def tearDown(self):
        self.srt_path.unlink(missing_ok=True)
        self.ass_path.unlink(missing_ok=True)

    def test_srt_no_timestamps(self):
        result = subs_to_plain_text(self.srt_subs)
        self.assertNotIn('[00:', result)
        self.assertNotIn('**[', result)

    def test_srt_text_present(self):
        result = subs_to_plain_text(self.srt_subs)
        self.assertIn('Hello world', result)

    def test_ass_speaker_prefix(self):
        result = subs_to_plain_text(self.ass_subs)
        self.assertIn('Alice:', result)
        self.assertIn('Bob:', result)

    def test_ass_no_markdown_bold(self):
        result = subs_to_plain_text(self.ass_subs)
        self.assertNotIn('**Alice**', result)

    def test_no_frontmatter(self):
        result = subs_to_plain_text(self.srt_subs)
        self.assertNotIn('---', result)
        self.assertNotIn('fetched_at', result)


# ---------------------------------------------------------------------------
# process_sub_file (file I/O)
# ---------------------------------------------------------------------------

class TestProcessSubFile(unittest.TestCase):
    def test_creates_md_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src = tmpdir_path / 'test.srt'
            src.write_text(SAMPLE_SRT, encoding='utf-8')
            out_dir = tmpdir_path / 'out'

            out = process_sub_file(src, out_dir, 'md')

            self.assertTrue(out.exists())
            self.assertEqual(out.suffix, '.md')
            self.assertEqual(out.stem, 'test')

    def test_md_has_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'test.srt'
            src.write_text(SAMPLE_SRT, encoding='utf-8')
            out = process_sub_file(src, Path(tmpdir) / 'out', 'md')
            content = out.read_text(encoding='utf-8')
            self.assertIn('---', content)
            self.assertIn('fetched_at:', content)

    def test_txt_mode_no_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'test.srt'
            src.write_text(SAMPLE_SRT, encoding='utf-8')
            out = process_sub_file(src, Path(tmpdir) / 'out', 'txt')
            self.assertEqual(out.suffix, '.txt')
            content = out.read_text(encoding='utf-8')
            self.assertNotIn('fetched_at:', content)

    def test_output_dir_created_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'test.srt'
            src.write_text(SAMPLE_SRT, encoding='utf-8')
            deep_dir = Path(tmpdir) / 'deeply' / 'nested' / 'dir'
            out = process_sub_file(src, deep_dir, 'md')
            self.assertTrue(out.exists())

    def test_ass_file_processed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'panel.ass'
            src.write_text(SAMPLE_ASS, encoding='utf-8')
            out = process_sub_file(src, Path(tmpdir) / 'out', 'md')
            content = out.read_text(encoding='utf-8')
            self.assertIn('Alice', content)
            self.assertIn('Bob', content)

    def test_vtt_file_processed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'captions.vtt'
            src.write_text(SAMPLE_VTT, encoding='utf-8')
            out = process_sub_file(src, Path(tmpdir) / 'out', 'md')
            self.assertTrue(out.exists())
            content = out.read_text(encoding='utf-8')
            self.assertIn('Hello world', content)


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    def _runner(self):
        from typer.testing import CliRunner
        return CliRunner()

    def test_help_exits_cleanly(self):
        from any2md.sub import app
        result = self._runner().invoke(app, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('subtitle', result.output.lower())

    def test_missing_file_exits_with_error(self):
        from any2md.sub import app
        result = self._runner().invoke(app, ['/nonexistent/path/file.srt'])
        self.assertNotEqual(result.exit_code, 0)

    def test_empty_directory_exits_with_error(self):
        from any2md.sub import app
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._runner().invoke(app, [tmpdir])
            self.assertNotEqual(result.exit_code, 0)

    def test_single_srt_end_to_end(self):
        from any2md.sub import app
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'captions.srt'
            src.write_text(SAMPLE_SRT, encoding='utf-8')
            out_dir = Path(tmpdir) / 'out'

            result = self._runner().invoke(app, [str(src), '-o', str(out_dir)])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            out_file = out_dir / 'captions.md'
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding='utf-8')
            self.assertIn('---', content)
            self.assertIn('Hello world', content)

    def test_txt_format_flag(self):
        from any2md.sub import app
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'captions.srt'
            src.write_text(SAMPLE_SRT, encoding='utf-8')
            out_dir = Path(tmpdir) / 'out'

            result = self._runner().invoke(app, [str(src), '-o', str(out_dir), '-f', 'txt'])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            out_file = out_dir / 'captions.txt'
            self.assertTrue(out_file.exists())

    def test_batch_directory_mode(self):
        from any2md.sub import app
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / 'a.srt').write_text(SAMPLE_SRT, encoding='utf-8')
            (tmpdir_path / 'b.srt').write_text(SAMPLE_SRT, encoding='utf-8')
            out_dir = tmpdir_path / 'out'

            result = self._runner().invoke(app, [str(tmpdir_path), '-o', str(out_dir)])

            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertTrue((out_dir / 'a.md').exists())
            self.assertTrue((out_dir / 'b.md').exists())


if __name__ == "__main__":
    unittest.main()
