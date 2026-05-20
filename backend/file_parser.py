import io
import fitz  # PyMuPDF
from docx import Document
import openpyxl


def parse_pdf(file_bytes: bytes) -> str:
    parts = []
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                parts.append(f"[Page {page_num + 1}]\n{text}")
        doc.close()
    except Exception as e:
        raise RuntimeError(f"PDF parsing error: {e}")
    return "\n".join(parts)


def parse_docx(file_bytes: bytes) -> str:
    parts = []
    try:
        doc = Document(io.BytesIO(file_bytes))
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                # Preserve heading structure
                if para.style.name.startswith("Heading"):
                    parts.append(f"\n## {text}")
                else:
                    parts.append(text)
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(
                    cell.text.strip() for cell in row.cells if cell.text.strip()
                )
                if row_text:
                    parts.append(row_text)
    except Exception as e:
        raise RuntimeError(f"DOCX parsing error: {e}")
    return "\n".join(parts)


def parse_xlsx(file_bytes: bytes) -> str:
    parts = []
    try:
        wb = openpyxl.load_workbook(
            io.BytesIO(file_bytes), read_only=True, data_only=True
        )
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            parts.append(f"\n[Sheet: {sheet_name}]")
            headers = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if all(v is None for v in row):
                    continue
                if i == 0:
                    headers = [str(c).strip() if c is not None else f"Col{j}" for j, c in enumerate(row)]
                    continue
                for h, val in zip(headers, row):
                    if val is not None and str(val).strip():
                        parts.append(f"{h}: {val}")
        wb.close()
    except Exception as e:
        raise RuntimeError(f"Excel parsing error: {e}")
    return "\n".join(parts)


def parse_file(filename: str, file_bytes: bytes) -> str:
    if not filename or not file_bytes:
        raise ValueError("Filename and file content are required")
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        return parse_pdf(file_bytes)
    elif ext in ("docx", "doc"):
        return parse_docx(file_bytes)
    elif ext in ("xlsx", "xls"):
        return parse_xlsx(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type: .{ext}. Accepted: .pdf, .docx, .xlsx"
        )
