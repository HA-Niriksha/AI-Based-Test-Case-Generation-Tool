import logging
import traceback
import uuid
from collections import Counter
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from models import (
    UploadResponse, GenerateRequest, GenerateResponse,
    GenerateSummary, HealthResponse, ReviewPoints,
)
from config import ENGINE, VERSION, CHUNK_SIZE_WORDS
from file_parser import parse_file
from document_ingestion import ingest_document
from test_case_generator import generate_all, is_spacy_available
from output_generator import generate_excel, generate_docx

# ─── LOGGING ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ─── APP ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Rule-Based Test Case Generator",
    version=VERSION,
    description="Generates test cases from SRS documents using pure rule-based NLP — no API, no LLM.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── SESSION STORE ────────────────────────────────────────────────────────────
# In-memory store: session_id → { text, chunks, test_cases }
sessions: Dict[str, Dict[str, Any]] = {}


def _error(error: str, layer: str, detail: str, suggestion: str, status: int = 500):
    raise HTTPException(
        status_code=status,
        detail={
            "error": error,
            "layer": layer,
            "detail": detail,
            "retry_count": 0,
            "suggestion": suggestion,
        },
    )


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@app.get("/api/debug/chunks")
def debug_chunks(session_id: str = Query(...)):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    text   = session.get("text", "")
    chunks = ingest_document(text)
    return {
        "total_chunks": len(chunks),
        "chunks": [
            {
                "chunk_index":      c.chunk_index,
                "requirement_ids":  c.requirement_ids,
                "module":           c.module,
                "requirement_type": c.requirement_type,
                "content_preview":  c.content[:150],
            }
            for c in chunks
        ],
    }

@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        engine=ENGINE,
        spacy_available=is_spacy_available(),
        version=VERSION,
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    allowed = {".pdf", ".docx", ".doc", ".xlsx", ".xls"}
    suffix = f".{file.filename.lower().rsplit('.', 1)[-1]}" if "." in file.filename else ""
    if suffix not in allowed:
        _error(
            "Unsupported file type",
            "parsing",
            f"Received: {suffix}",
            "Upload a .pdf, .docx, or .xlsx file",
            400,
        )

    try:
        raw_bytes = await file.read()
        text = parse_file(file.filename, raw_bytes)
    except Exception as e:
        _error(
            "File parsing failed",
            "parsing",
            traceback.format_exc(),
            "Re-upload the file. PDF may be password-protected or empty.",
            422,
        )

    if not text or len(text.strip()) < 50:
        _error(
            "Document appears empty",
            "parsing",
            "Extracted text is too short",
            "Ensure the document has readable text content.",
            422,
        )

    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "filename": file.filename,
        "text": text,
        "chunks": None,
        "test_cases": None,
        "removed": 0,
    }

    return UploadResponse(
        session_id=session_id,
        filename=file.filename,
        char_count=len(text),
        text_preview=text[:500],
    )


@app.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    session = sessions.get(request.session_id)
    if not session:
        _error("Session not found", "generation", "", "Upload a file first.", 404)

    try:
        text   = session["text"]
        chunks = ingest_document(text, CHUNK_SIZE_WORDS)

        if not chunks:
            _error(
                "No requirements found",
                "ingestion",
                "Document produced zero chunks",
                "Verify SRS language uses shall/must/should and contains requirement sentences.",
                422,
            )

        rp = request.review_points
        review_points = {
            "rp1": rp.rp1,
            "rp2": rp.rp2,
            "rp3": rp.rp3,
            "rp4": rp.rp4,
            "rp5": rp.rp5,
        }

        try:
            test_cases, removed = generate_all(chunks, review_points)
        except Exception as gen_err:
            import traceback
            logger.error(f"Generation error: {traceback.format_exc()}")
            raise

        if not test_cases:
            _error(
                "No test cases generated",
                "generation",
                "Generator produced zero test cases",
                "No requirement sentences matched keyword patterns. "
                "Verify SRS language uses shall/must/should.",
                422,
            )

        sessions[request.session_id]["chunks"]     = chunks
        sessions[request.session_id]["test_cases"] = test_cases
        sessions[request.session_id]["removed"]    = removed

        summary = GenerateSummary(
            total=len(test_cases),
            by_module=dict(Counter(tc.module            for tc in test_cases)),
            by_requirement_type=dict(Counter(tc.requirement_type  for tc in test_cases)),
            by_scenario_type=dict(Counter(tc.scenario_type     for tc in test_cases)),
            by_testing_type=dict(Counter(tc.testing_type       for tc in test_cases)),
            by_priority=dict(Counter(tc.priority          for tc in test_cases)),
            duplicates_removed=removed,
        )

        return GenerateResponse(test_cases=test_cases, summary=summary)

    except HTTPException:
        raise
    except Exception as e:
        _error(
            "Generation failed",
            "generation",
            traceback.format_exc(),
            "Check server logs for details.",
        )


@app.get("/api/export/excel")
def export_excel(session_id: str = Query(...)):
    session = sessions.get(session_id)
    if not session or not session.get("test_cases"):
        _error("No generated test cases found", "export", "", "Run /api/generate first.", 404)

    try:
        xlsx_bytes = generate_excel(session["test_cases"], session["removed"])
    except Exception as e:
        _error("Excel export failed", "export", traceback.format_exc(), "Check server logs.")

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=test_cases.xlsx"},
    )


@app.get("/api/export/docx")
def export_docx(session_id: str = Query(...)):
    session = sessions.get(session_id)
    if not session or not session.get("test_cases"):
        _error("No generated test cases found", "export", "", "Run /api/generate first.", 404)

    try:
        docx_bytes = generate_docx(session["test_cases"], session["removed"])
    except Exception as e:
        _error("Word export failed", "export", traceback.format_exc(), "Check server logs.")

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=test_cases.docx"},
    )
