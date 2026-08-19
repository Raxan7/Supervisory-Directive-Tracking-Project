from pathlib import Path
from typing import Any
from docx import Document
import pdfplumber

SUPPORTED_IMPORTS = {".docx", ".pdf"}


def parse_docx(content: bytes) -> list[dict[str, Any]]:
    document = Document(__import__("io").BytesIO(content))
    rows: list[dict[str, Any]] = []
    for table in document.tables:
        rows.extend(_table_to_rows([[cell.text.strip() for cell in row.cells] for row in table.rows]))
    return rows


def parse_pdf(content: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with pdfplumber.open(__import__("io").BytesIO(content)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                rows.extend(_table_to_rows(table))
    return rows


def _table_to_rows(table: list[list[Any]]) -> list[dict[str, Any]]:
    import re
    table = [row for row in table if any(cell not in (None, "") for cell in row)]
    if len(table) < 2:
        return []
    headers = [re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_") for value in table[0]]
    return [{headers[i]: row[i] if i < len(row) else None for i in range(len(headers))} for row in table[1:]]


def parse_findings_document(filename: str, content: bytes) -> list[dict[str, Any]]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_IMPORTS:
        raise ValueError(f"Unsupported file type. Allowed: {', '.join(sorted(SUPPORTED_IMPORTS))}")
    parser = {".docx": parse_docx, ".pdf": parse_pdf}[suffix]
    return parser(content)
