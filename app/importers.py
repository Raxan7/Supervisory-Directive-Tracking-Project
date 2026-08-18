import csv
import io
import re
from pathlib import Path
from typing import Any
from docx import Document
from openpyxl import load_workbook
import pdfplumber

SUPPORTED_IMPORTS = {".csv", ".xlsx", ".docx", ".pdf"}


def _header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _table_to_rows(table: list[list[Any]]) -> list[dict[str, Any]]:
    table = [row for row in table if any(cell not in (None, "") for cell in row)]
    if len(table) < 2:
        return []
    headers = [_header(value) for value in table[0]]
    return [{headers[i]: row[i] if i < len(row) else None for i in range(len(headers))} for row in table[1:]]


def parse_csv(content: bytes) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    return [{_header(k): v for k, v in row.items()} for row in reader]


def parse_xlsx(content: bytes) -> list[dict[str, Any]]:
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    sheet = workbook.active
    return _table_to_rows([list(row) for row in sheet.iter_rows(values_only=True)])


def parse_docx(content: bytes) -> list[dict[str, Any]]:
    document = Document(io.BytesIO(content))
    rows: list[dict[str, Any]] = []
    for table in document.tables:
        rows.extend(_table_to_rows([[cell.text.strip() for cell in row.cells] for row in table.rows]))
    if not rows:
        lines = [line.strip() for p in document.paragraphs for line in p.text.splitlines() if line.strip()]
        rows = _table_to_rows([next(csv.reader([line])) for line in lines if "," in line])
    return rows


def parse_pdf(content: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                rows.extend(_table_to_rows(table))
        if not rows:
            lines = [line.strip() for page in pdf.pages for line in (page.extract_text() or "").splitlines() if "," in line]
            rows = _table_to_rows([next(csv.reader([line])) for line in lines])
    return rows


def parse_findings_document(filename: str, content: bytes) -> list[dict[str, Any]]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_IMPORTS:
        raise ValueError(f"Unsupported file type. Allowed: {', '.join(sorted(SUPPORTED_IMPORTS))}")
    parser = {".csv": parse_csv, ".xlsx": parse_xlsx, ".docx": parse_docx, ".pdf": parse_pdf}[suffix]
    rows = parser(content)
    if not rows:
        raise ValueError("No tabular finding records were detected in the document")
    return rows

