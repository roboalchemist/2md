#!/usr/bin/env python3
r"""
test_tex.py - Unit tests for tex.py (LaTeX -> Markdown converter)

Tests cover:
- Section headings (\chapter, \section, \subsection, \subsubsection)
- Math preservation ($...$, $$...$$, \[...\], equation/align environments)
- Emphasis conversion (\textbf, \textit, \emph, \texttt)
- List conversion (itemize -> -, enumerate -> 1.)
- Figure/image (\includegraphics)
- Metadata extraction (\title, \author, \date, abstract)
- Preamble stripping (\documentclass, \usepackage, \begin{document})
- Citations (\cite, \ref, \label)
"""

import tempfile
import unittest
from pathlib import Path

from any2md.tex import (
    tex_to_markdown_text,
    tex_to_full_markdown,
    tex_to_plain_text,
    extract_tex_metadata,
    process_tex_file,
    _protect_math,
    _restore_math,
    _convert_sections,
    _convert_emphasis,
    _convert_lists,
    _convert_figures,
    _convert_citations_and_refs,
    _strip_preamble_and_wrappers,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TEX = r"""
\documentclass[12pt]{article}
\usepackage{amsmath}
\usepackage{graphicx}

\title{My Paper}
\author{Jane Doe}
\date{2026-01-01}

\begin{document}
\maketitle

\begin{abstract}
This paper studies something interesting.
\end{abstract}

\section{Introduction}

This is an introduction with \textbf{bold text} and \textit{italic text}.
We also have \texttt{monospace code}.

\subsection{Background}

Here is some inline math: $E = mc^2$ and display math:
$$\int_0^\infty f(x)\,dx = 1$$

\subsubsection{Details}

A referenced equation \ref{eq:main} and citation \cite{smith2020}.

\begin{itemize}
\item First item
\item Second item
\end{itemize}

\begin{enumerate}
\item One
\item Two
\end{enumerate}

\includegraphics[width=0.5\textwidth]{figure1.png}

\end{document}
"""

MINIMAL_TEX = r"""
Just some plain text with no LaTeX commands.
"""


# ---------------------------------------------------------------------------
# Section headings
# ---------------------------------------------------------------------------

class TestSectionHeadings(unittest.TestCase):

    def test_chapter(self):
        result = _convert_sections(r'\chapter{My Chapter}')
        self.assertIn('# My Chapter', result)

    def test_section(self):
        result = _convert_sections(r'\section{Introduction}')
        self.assertIn('## Introduction', result)

    def test_subsection(self):
        result = _convert_sections(r'\subsection{Background}')
        self.assertIn('### Background', result)

    def test_subsubsection(self):
        result = _convert_sections(r'\subsubsection{Details}')
        self.assertIn('#### Details', result)

    def test_section_star(self):
        """Starred variants (unnumbered) should also convert."""
        result = _convert_sections(r'\section*{Unnumbered}')
        self.assertIn('## Unnumbered', result)

    def test_multiple_sections(self):
        tex = r'\section{A}\subsection{B}\subsubsection{C}'
        result = _convert_sections(tex)
        self.assertIn('## A', result)
        self.assertIn('### B', result)
        self.assertIn('#### C', result)

    def test_full_pipeline_section(self):
        """Section headings survive the full conversion pipeline."""
        result = tex_to_markdown_text(r'\section{Hello World}')
        self.assertIn('## Hello World', result)


# ---------------------------------------------------------------------------
# Math preservation
# ---------------------------------------------------------------------------

class TestMathPreservation(unittest.TestCase):

    def test_inline_dollar(self):
        """$...$ should be preserved unchanged."""
        tex = r'Here is $E = mc^2$ inline.'
        result = tex_to_markdown_text(tex)
        self.assertIn('$E = mc^2$', result)

    def test_display_dollar_dollar(self):
        """$$...$$ should be preserved unchanged."""
        tex = r'$$\int_0^\infty f(x)\,dx$$'
        result = tex_to_markdown_text(tex)
        self.assertIn('$$', result)
        self.assertIn(r'\int_0^\infty', result)

    def test_display_brackets(self):
        r"""\ [...\ ] should be preserved."""
        tex = r'\[a^2 + b^2 = c^2\]'
        result = tex_to_markdown_text(tex)
        self.assertIn(r'\[', result)
        self.assertIn(r'a^2 + b^2 = c^2', result)

    def test_paren_delimiters(self):
        r"""\ (...\ ) should be preserved."""
        tex = r'\(x + y\)'
        result = tex_to_markdown_text(tex)
        self.assertIn(r'\(', result)
        self.assertIn('x + y', result)

    def test_equation_environment(self):
        tex = r'\begin{equation}E = mc^2\end{equation}'
        result = tex_to_markdown_text(tex)
        self.assertIn('E = mc^2', result)
        self.assertIn(r'\begin{equation}', result)

    def test_align_environment(self):
        tex = r'\begin{align}a &= b \\ c &= d\end{align}'
        result = tex_to_markdown_text(tex)
        self.assertIn(r'\begin{align}', result)
        self.assertIn('a &= b', result)

    def test_math_not_mangled_by_emphasis(self):
        """Math containing letters should not be italicized."""
        tex = r'$\alpha + \beta = \gamma$'
        result = tex_to_markdown_text(tex)
        # The math block should be intact, not split by emphasis rules
        self.assertIn(r'$\alpha + \beta = \gamma$', result)

    def test_protect_restore_roundtrip(self):
        """_protect_math / _restore_math are inverses."""
        original = r'Text $x^2$ and $$y^2$$ end.'
        protected, stash = _protect_math(original)
        restored = _restore_math(protected, stash)
        self.assertEqual(restored, original)


# ---------------------------------------------------------------------------
# Emphasis
# ---------------------------------------------------------------------------

class TestEmphasisConversion(unittest.TestCase):

    def test_textbf(self):
        result = _convert_emphasis(r'\textbf{bold}')
        self.assertEqual(result.strip(), '**bold**')

    def test_textit(self):
        result = _convert_emphasis(r'\textit{italic}')
        self.assertEqual(result.strip(), '*italic*')

    def test_emph(self):
        result = _convert_emphasis(r'\emph{emphasis}')
        self.assertEqual(result.strip(), '*emphasis*')

    def test_texttt(self):
        result = _convert_emphasis(r'\texttt{code}')
        self.assertEqual(result.strip(), '`code`')

    def test_nested_textbf_in_sentence(self):
        result = _convert_emphasis(r'This is \textbf{very bold} text.')
        self.assertIn('**very bold**', result)

    def test_full_pipeline_emphasis(self):
        tex = r'Here is \textbf{bold} and \textit{italic} and \texttt{mono}.'
        result = tex_to_markdown_text(tex)
        self.assertIn('**bold**', result)
        self.assertIn('*italic*', result)
        self.assertIn('`mono`', result)


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

class TestListConversion(unittest.TestCase):

    def test_itemize_basic(self):
        tex = r"""
\begin{itemize}
\item Alpha
\item Beta
\item Gamma
\end{itemize}
"""
        result = tex_to_markdown_text(tex)
        self.assertIn('- Alpha', result)
        self.assertIn('- Beta', result)
        self.assertIn('- Gamma', result)

    def test_enumerate_basic(self):
        tex = r"""
\begin{enumerate}
\item First
\item Second
\item Third
\end{enumerate}
"""
        result = tex_to_markdown_text(tex)
        self.assertIn('1.', result)
        self.assertIn('2.', result)
        self.assertIn('3.', result)
        self.assertIn('First', result)
        self.assertIn('Second', result)

    def test_itemize_no_begin_end_in_output(self):
        tex = r'\begin{itemize}\item A\end{itemize}'
        result = tex_to_markdown_text(tex)
        self.assertNotIn(r'\begin{itemize}', result)
        self.assertNotIn(r'\end{itemize}', result)

    def test_enumerate_no_begin_end_in_output(self):
        tex = r'\begin{enumerate}\item X\end{enumerate}'
        result = tex_to_markdown_text(tex)
        self.assertNotIn(r'\begin{enumerate}', result)
        self.assertNotIn(r'\end{enumerate}', result)

    def test_item_with_optional_label(self):
        tex = r'\begin{description}\item[Term] Definition here.\end{description}'
        result = tex_to_markdown_text(tex)
        self.assertIn('Term', result)
        self.assertIn('Definition here', result)


# ---------------------------------------------------------------------------
# Figures / images
# ---------------------------------------------------------------------------

class TestFigureConversion(unittest.TestCase):

    def test_includegraphics_basic(self):
        result = _convert_figures(r'\includegraphics{image.png}')
        self.assertIn('![](image.png)', result)

    def test_includegraphics_with_options(self):
        result = _convert_figures(r'\includegraphics[width=0.5\textwidth]{photo.jpg}')
        self.assertIn('![](photo.jpg)', result)

    def test_includegraphics_path_preserved(self):
        result = _convert_figures(r'\includegraphics{figs/result_plot.pdf}')
        self.assertIn('![](figs/result_plot.pdf)', result)

    def test_full_pipeline_figure(self):
        tex = r'\includegraphics[scale=0.8]{diagram.png}'
        result = tex_to_markdown_text(tex)
        self.assertIn('![](diagram.png)', result)

    def test_figure_environment_stripped(self):
        tex = r"""
\begin{figure}
\includegraphics{plot.png}
\caption{My caption}
\end{figure}
"""
        result = tex_to_markdown_text(tex)
        self.assertIn('![](plot.png)', result)
        self.assertNotIn(r'\begin{figure}', result)
        self.assertNotIn(r'\end{figure}', result)


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

class TestMetadataExtraction(unittest.TestCase):

    def _dummy_path(self) -> Path:
        return Path('/tmp/test_document.tex')

    def test_title_extracted(self):
        tex = r'\title{My Amazing Paper}'
        meta, _ = extract_tex_metadata(tex, self._dummy_path())
        self.assertEqual(meta.get('title'), 'My Amazing Paper')

    def test_author_extracted(self):
        tex = r'\author{Jane Doe}'
        meta, _ = extract_tex_metadata(tex, self._dummy_path())
        self.assertEqual(meta.get('author'), 'Jane Doe')

    def test_date_extracted(self):
        tex = r'\date{January 2026}'
        meta, _ = extract_tex_metadata(tex, self._dummy_path())
        self.assertEqual(meta.get('date'), 'January 2026')

    def test_abstract_extracted(self):
        tex = r'\begin{abstract}This is the abstract.\end{abstract}'
        meta, abstract = extract_tex_metadata(tex, self._dummy_path())
        self.assertIn('abstract', meta)
        self.assertIn('abstract', meta['abstract'])
        self.assertEqual(abstract, 'This is the abstract.')

    def test_source_and_fetched_at_always_present(self):
        meta, _ = extract_tex_metadata('', self._dummy_path())
        self.assertIn('source', meta)
        self.assertIn('fetched_at', meta)

    def test_full_sample_metadata(self):
        meta, abstract = extract_tex_metadata(SAMPLE_TEX, self._dummy_path())
        self.assertEqual(meta.get('title'), 'My Paper')
        self.assertEqual(meta.get('author'), 'Jane Doe')
        self.assertTrue(len(abstract) > 0)  # abstract text is present

    def test_empty_tex_returns_minimal_metadata(self):
        meta, abstract = extract_tex_metadata('', self._dummy_path())
        self.assertFalse(abstract)
        self.assertNotIn('title', meta)


# ---------------------------------------------------------------------------
# Preamble stripping
# ---------------------------------------------------------------------------

class TestPreambleStripping(unittest.TestCase):

    def test_documentclass_stripped(self):
        tex = r'\documentclass[12pt]{article}' + '\n' + r'Some text.'
        result = _strip_preamble_and_wrappers(tex)
        self.assertNotIn(r'\documentclass', result)
        self.assertIn('Some text.', result)

    def test_usepackage_stripped(self):
        tex = r'\usepackage{amsmath}' + '\n' + r'\usepackage[utf8]{inputenc}'
        result = _strip_preamble_and_wrappers(tex)
        self.assertNotIn(r'\usepackage', result)

    def test_begin_document_stripped(self):
        tex = r'\begin{document}Hello\end{document}'
        result = _strip_preamble_and_wrappers(tex)
        self.assertNotIn(r'\begin{document}', result)
        self.assertNotIn(r'\end{document}', result)
        self.assertIn('Hello', result)

    def test_maketitle_stripped(self):
        tex = r'\maketitle Some text.'
        result = _strip_preamble_and_wrappers(tex)
        self.assertNotIn(r'\maketitle', result)

    def test_full_pipeline_preamble(self):
        result = tex_to_markdown_text(SAMPLE_TEX)
        self.assertNotIn(r'\documentclass', result)
        self.assertNotIn(r'\usepackage', result)
        self.assertNotIn(r'\begin{document}', result)
        self.assertNotIn(r'\end{document}', result)


# ---------------------------------------------------------------------------
# Citations and cross-references
# ---------------------------------------------------------------------------

class TestCitationsAndRefs(unittest.TestCase):

    def test_cite_basic(self):
        result = _convert_citations_and_refs(r'\cite{smith2020}')
        self.assertIn('[smith2020]', result)

    def test_cite_multiple_keys(self):
        result = _convert_citations_and_refs(r'\cite{smith2020,jones2021}')
        self.assertIn('[smith2020,jones2021]', result)

    def test_cite_with_note(self):
        result = _convert_citations_and_refs(r'\cite[p.~5]{smith2020}')
        self.assertIn('smith2020', result)
        self.assertIn('p.', result)

    def test_ref_basic(self):
        result = _convert_citations_and_refs(r'\ref{fig:result}')
        self.assertIn('[fig:result]', result)

    def test_label_stripped(self):
        result = _convert_citations_and_refs(r'Some text \label{eq:main} more text.')
        self.assertNotIn(r'\label', result)
        self.assertIn('Some text', result)
        self.assertIn('more text', result)

    def test_full_pipeline_cite_ref(self):
        tex = r'See \cite{author2020} and equation \ref{eq:one}. \label{sec:intro}'
        result = tex_to_markdown_text(tex)
        self.assertIn('[author2020]', result)
        self.assertIn('[eq:one]', result)
        self.assertNotIn(r'\label', result)


# ---------------------------------------------------------------------------
# Verbatim / code
# ---------------------------------------------------------------------------

class TestVerbatimConversion(unittest.TestCase):

    def test_verbatim_environment(self):
        tex = r'\begin{verbatim}def hello(): pass\end{verbatim}'
        result = tex_to_markdown_text(tex)
        self.assertIn('```', result)
        self.assertIn('def hello(): pass', result)

    def test_verb_inline(self):
        tex = r'Use \verb|print("hi")| in Python.'
        result = tex_to_markdown_text(tex)
        self.assertIn('`print("hi")`', result)


# ---------------------------------------------------------------------------
# Full pipeline integration
# ---------------------------------------------------------------------------

class TestFullPipeline(unittest.TestCase):

    def test_sample_tex_produces_markdown(self):
        result = tex_to_markdown_text(SAMPLE_TEX)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_sample_tex_has_headings(self):
        result = tex_to_markdown_text(SAMPLE_TEX)
        self.assertIn('## Introduction', result)
        self.assertIn('### Background', result)
        self.assertIn('#### Details', result)

    def test_sample_tex_math_preserved(self):
        result = tex_to_markdown_text(SAMPLE_TEX)
        self.assertIn('$E = mc^2$', result)

    def test_plain_text_strips_headings(self):
        md = tex_to_markdown_text(r'\section{Hello}')
        txt = tex_to_plain_text(md)
        self.assertNotIn('##', txt)
        self.assertIn('Hello', txt)

    def test_frontmatter_in_full_markdown(self):
        meta = {'title': 'Test', 'author': 'Author', 'fetched_at': '2026-01-01T00:00:00Z', 'source': '/tmp/x.tex'}
        result = tex_to_full_markdown('# Body', metadata=meta)
        self.assertIn('---', result)
        self.assertIn('title:', result)
        self.assertIn('# Body', result)

    def test_process_tex_file_roundtrip(self):
        """process_tex_file writes a real file with correct extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = Path(tmpdir) / 'sample.tex'
            tex_path.write_text('\\section{Test}\nHello world.', encoding='utf-8')
            out_dir = Path(tmpdir) / 'out'
            out_path = process_tex_file(tex_path, out_dir, 'md')
            self.assertTrue(out_path.exists())
            self.assertEqual(out_path.suffix, '.md')
            content = out_path.read_text(encoding='utf-8')
            self.assertIn('---', content)  # frontmatter
            self.assertIn('Hello world', content)

    def test_process_tex_file_txt_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = Path(tmpdir) / 'doc.tex'
            tex_path.write_text('\\section{Title}\nBody text.', encoding='utf-8')
            out_dir = Path(tmpdir) / 'out'
            out_path = process_tex_file(tex_path, out_dir, 'txt')
            self.assertEqual(out_path.suffix, '.txt')
            content = out_path.read_text(encoding='utf-8')
            # No frontmatter in txt mode
            self.assertNotIn('---', content)


if __name__ == '__main__':
    unittest.main()
