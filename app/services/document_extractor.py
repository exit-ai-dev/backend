"""
Text extraction from PDF / DOCX / XLSX / TXT / MD
and fixed-size chunking with overlap.
"""
from __future__ import annotations
import io
from pathlib import Path
from typing import List


SUPPORTED = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md"}


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _pdf(content)
    if suffix in (".docx", ".doc"):
        return _docx(content)
    if suffix in (".xlsx", ".xls"):
        return _xlsx(content)
    if suffix in (".txt", ".md"):
        return content.decode("utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {suffix!r}")


def _pdf(content: bytes) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(stream=content, filetype="pdf")
    pages = [page.get_text() for page in doc]
    return "\n".join(pages)


def _docx(content: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _xlsx(content: bytes) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    lines: List[str] = []
    for sheet in wb.worksheets:
        lines.append(f"=== {sheet.title} ===")
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks."""
    text = text.strip()
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks
