#!/usr/bin/env python3
"""
pdf2md.py - PDF to Markdown Extraction Tool

Extracts text from PDF files to markdown (default), SRT-style, or plain text using
pymupdf4llm. Produces page-delineated output with YAML frontmatter from PDF metadata.

Usage:
    python pdf2md.py [options] <input.pdf>

Examples:
    python pdf2md.py document.pdf
    python pdf2md.py slides.pdf -o ~/notes/
    python pdf2md.py report.pdf --pages 1-10
    python pdf2md.py scanned.pdf -f txt
"""

import os
import re
import sys
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import typer
from typing_extensions import Annotated

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reuse frontmatter builder from yt2md
from yt2md import build_frontmatter

# Minimum chars on a page before flagging as image-heavy
THIN_PAGE_THRESHOLD = 50


def parse_page_range(page_range: str, total_pages: int) -> List[int]:
    """
    Parse a page range string into a list of 0-based page indices.

    Accepts formats like "1-10", "1,3,5", "1-5,8,10-12".
    Input is 1-based (user-facing), output is 0-based (fitz).

    Args:
        page_range: Page range string
        total_pages: Total number of pages in the document

    Returns:
        Sorted list of 0-based page indices
    """
    pages = set()
    for part in page_range.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start = max(1, int(start.strip()))
            end = min(total_pages, int(end.strip()))
            pages.update(range(start - 1, end))
        else:
            p = int(part.strip())
            if 1 <= p <= total_pages:
                pages.add(p - 1)
    return sorted(pages)


def extract_pdf_metadata(doc) -> Dict:
    """
    Extract metadata from a fitz Document object.

    Args:
        doc: fitz.Document object

    Returns:
        Cleaned metadata dict suitable for frontmatter
    """
    meta = doc.metadata or {}

    # Parse PDF date format: D:YYYYMMDDHHmmSS or similar
    def parse_pdf_date(date_str: str) -> Optional[str]:
        if not date_str:
            return None
        # Strip D: prefix
        date_str = date_str.lstrip("D:")
        # Take first 8 chars for YYYYMMDD
        if len(date_str) >= 8:
            try:
                dt = datetime.strptime(date_str[:8], "%Y%m%d")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return date_str

    result = {
        'title': meta.get('title') or None,
        'author': meta.get('author') or None,
        'subject': meta.get('subject') or None,
        'keywords': meta.get('keywords') or None,
        'creator': meta.get('creator') or None,
        'producer': meta.get('producer') or None,
        'created': parse_pdf_date(meta.get('creationDate', '')),
        'modified': parse_pdf_date(meta.get('modDate', '')),
        'format': meta.get('format') or None,
        'pages': doc.page_count,
        'fetched_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }

    # Parse keywords into a list
    if result['keywords']:
        result['keywords'] = [k.strip() for k in result['keywords'].split(',') if k.strip()]

    # Remove None/empty values
    return {k: v for k, v in result.items() if v is not None and v != '' and v != []}


def extract_pages(pdf_path: str, page_indices: Optional[List[int]] = None) -> List[Dict]:
    """
    Extract markdown from PDF pages using pymupdf4llm.

    Args:
        pdf_path: Path to the PDF file
        page_indices: Optional list of 0-based page indices to extract

    Returns:
        List of dicts with 'page' (1-based) and 'text' keys
    """
    try:
        import pymupdf4llm
    except ImportError:
        logger.error("pymupdf4llm is required. Install it with: pip install pymupdf4llm")
        raise

    logger.info(f"Extracting text from: {pdf_path}")

    # Pass page_indices directly to pymupdf4llm to avoid processing all pages
    chunks = pymupdf4llm.to_markdown(pdf_path, pages=page_indices, page_chunks=True)

    results = []
    for chunk in chunks:
        page_num = chunk['metadata']['page'] + 1  # 0-based to 1-based
        text = chunk['text'].strip()
        is_thin = len(text) < THIN_PAGE_THRESHOLD

        results.append({
            'page': page_num,
            'text': text,
            'is_thin': is_thin,
        })

    return results


def pages_to_markdown(pages: List[Dict], metadata: Optional[Dict] = None,
                      title: Optional[str] = None) -> str:
    """
    Convert extracted pages to markdown format.

    Args:
        pages: List of page dicts from extract_pages()
        metadata: Optional metadata dict for YAML frontmatter
        title: Optional title for the document heading

    Returns:
        Markdown formatted string
    """
    lines = []

    if metadata:
        lines.append(build_frontmatter(metadata))
        lines.append("")

    if title:
        lines.append(f"# {title}")
        lines.append("")

    thin_pages = []
    for page in pages:
        lines.append(f"## Page {page['page']}")
        lines.append("")

        if page['is_thin']:
            thin_pages.append(page['page'])
            if page['text']:
                lines.append(page['text'])
            else:
                lines.append("*[This page appears to be image-only — no extractable text]*")
            lines.append("")
        else:
            lines.append(page['text'])
            lines.append("")

    if thin_pages:
        logger.warning(
            f"Pages with little/no text (may need OCR): {thin_pages}"
        )

    return "\n".join(lines)


def pages_to_text(pages: List[Dict]) -> str:
    """
    Convert extracted pages to plain text (no formatting).

    Args:
        pages: List of page dicts from extract_pages()

    Returns:
        Plain text string
    """
    parts = []
    for page in pages:
        if page['text']:
            parts.append(page['text'])
    return "\n\n".join(parts)


# --- CLI ---

class OutputFormat(str, Enum):
    md = "md"
    txt = "txt"


app = typer.Typer(
    help="Extract text from PDFs to markdown or plain text using pymupdf4llm.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command()
def main(
    input: Annotated[str, typer.Argument(
        help="Path to a PDF file.",
    )],
    output_dir: Annotated[Path, typer.Option(
        "--output-dir", "-o",
        help="Directory to save output files.",
    )] = Path.cwd(),
    format: Annotated[OutputFormat, typer.Option(
        "--format", "-f",
        help="Output format: [bold]md[/bold] (markdown with frontmatter + page headings), [bold]txt[/bold] (plain text).",
    )] = OutputFormat.md,
    pages: Annotated[Optional[str], typer.Option(
        "--pages", "-p",
        help="Page range to extract, e.g. [bold]1-10[/bold], [bold]1,3,5[/bold], [bold]1-5,8,10-12[/bold]. Defaults to all pages.",
    )] = None,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose (DEBUG) logging.",
    )] = False,
):
    """
    Extract text from a PDF file to markdown (default) or plain text.

    Produces page-delineated output with YAML frontmatter from PDF metadata.
    Pages with little/no extractable text are flagged as potentially image-only.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)

    pdf_path = os.path.abspath(input)
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        raise typer.Exit(code=1)

    if not pdf_path.lower().endswith('.pdf'):
        logger.error(f"Not a PDF file: {pdf_path}")
        raise typer.Exit(code=1)

    # Open document for metadata
    import fitz
    doc = fitz.open(pdf_path)
    metadata = extract_pdf_metadata(doc)
    metadata['source'] = pdf_path
    total_pages = doc.page_count
    doc.close()

    logger.info(f"PDF has {total_pages} pages")

    # Parse page range
    page_indices = None
    if pages:
        page_indices = parse_page_range(pages, total_pages)
        logger.info(f"Extracting pages: {[i+1 for i in page_indices]}")

    # Extract
    extracted = extract_pages(pdf_path, page_indices)
    logger.info(f"Extracted {len(extracted)} pages")

    # Determine output filename
    output_dir_str = str(output_dir)
    os.makedirs(output_dir_str, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    ext = format.value
    output_file = os.path.join(output_dir_str, f"{base_name}.{ext}")

    # Format output
    title = metadata.get('title') or base_name
    if format == OutputFormat.md:
        content = pages_to_markdown(extracted, metadata=metadata, title=title)
    else:
        content = pages_to_text(extracted)

    # Write
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Output saved to: {output_file}")


if __name__ == "__main__":
    app()
