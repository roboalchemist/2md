#!/usr/bin/env python3
"""
Tests for pdf2md.py

Run with: python -m pytest test_pdf2md.py -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf2md import (
    parse_page_range,
    pages_to_markdown,
    pages_to_text,
)


class TestPdf2Md(unittest.TestCase):

    def test_parse_page_range_single(self):
        self.assertEqual(parse_page_range("3", 10), [2])

    def test_parse_page_range_range(self):
        self.assertEqual(parse_page_range("1-5", 10), [0, 1, 2, 3, 4])

    def test_parse_page_range_mixed(self):
        self.assertEqual(parse_page_range("1-3,5,8-10", 10), [0, 1, 2, 4, 7, 8, 9])

    def test_parse_page_range_clamps_to_total(self):
        result = parse_page_range("1-100", 5)
        self.assertEqual(result, [0, 1, 2, 3, 4])

    def test_parse_page_range_out_of_bounds_ignored(self):
        result = parse_page_range("0,6", 5)
        self.assertEqual(result, [])

    def test_pages_to_markdown_basic(self):
        pages = [
            {'page': 1, 'text': 'Hello world', 'is_thin': False},
            {'page': 2, 'text': 'Second page content', 'is_thin': False},
        ]
        result = pages_to_markdown(pages, title="Test Doc")
        self.assertIn("# Test Doc", result)
        self.assertIn("## Page 1", result)
        self.assertIn("Hello world", result)
        self.assertIn("## Page 2", result)
        self.assertIn("Second page content", result)

    def test_pages_to_markdown_thin_page(self):
        pages = [
            {'page': 1, 'text': '', 'is_thin': True},
        ]
        result = pages_to_markdown(pages)
        self.assertIn("image-only", result)

    def test_pages_to_markdown_with_metadata(self):
        pages = [{'page': 1, 'text': 'Content', 'is_thin': False}]
        metadata = {
            'title': 'My PDF',
            'author': 'Jane',
            'pages': 10,
            'fetched_at': '2026-01-01T00:00:00Z',
        }
        result = pages_to_markdown(pages, metadata=metadata, title="My PDF")
        self.assertTrue(result.startswith("---"))
        self.assertIn("author: Jane", result)
        self.assertIn("pages: 10", result)
        self.assertIn("# My PDF", result)

    def test_pages_to_text(self):
        pages = [
            {'page': 1, 'text': 'First page', 'is_thin': False},
            {'page': 2, 'text': 'Second page', 'is_thin': False},
        ]
        result = pages_to_text(pages)
        self.assertEqual(result, "First page\n\nSecond page")

    def test_pages_to_text_skips_empty(self):
        pages = [
            {'page': 1, 'text': '', 'is_thin': True},
            {'page': 2, 'text': 'Content', 'is_thin': False},
        ]
        result = pages_to_text(pages)
        self.assertEqual(result, "Content")


if __name__ == "__main__":
    unittest.main()
