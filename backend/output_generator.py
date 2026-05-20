import io
from datetime import datetime
from typing import List

import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter
from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from models import TestCase
from config import ENGINE


# ─── COLOUR CONSTANTS ─────────────────────────────────────────────────────────

HEADER_BG = "4472C4"     # Blue header
HEADER_FG = "FFFFFF"
ALT_ROW    = "EEF2F9"
P1_FILL    = "FFD7D7"    # Light red
P2_FILL    = "FFE8CC"    # Light orange
P3_FILL    = "FFFACC"    # Light yellow
SUMMARY_BG = "2F4F8F"


# ─── COLUMN DEFINITIONS ──────────────────────────────────────────────────────

COLUMNS = [
    ("Traceability Req-ID",           "traceability_req_id",  15),
    ("Test Case ID",                   "test_case_id",         14),
    ("Scenario ID",                    "scenario_id",          12),
    ("Priority",                       "priority",              9),
    ("Test Case Objective",            "objective",            40),
    ("Test Precondition",              "preconditions",        35),
    ("Test Steps",                     "test_steps",           40),
    ("Test Inputs (Conditions/Values)","inputs",               35),
    ("Test Case Design Methodology",   "design_methodology",   22),
    ("Dependent Test Cases",           "dependent_test_cases", 20),
    ("Expected Outcome",               "expected_outcome",     40),
    ("Test Environment",               "test_environment",     15),
    ("Remarks / Additional Info",      "remarks",              40),
    ("Module",                         "module",               15),
    ("Requirement Type",               "requirement_type",     16),
    ("Scenario Type",                  "scenario_type",        14),
    ("Testing Type",                   "testing_type",         14),
]

PRIORITY_FILLS = {
    "P1": PatternFill("solid", fgColor=P1_FILL),
    "P2": PatternFill("solid", fgColor=P2_FILL),
    "P3": PatternFill("solid", fgColor=P3_FILL),
}

ALT_FILL   = PatternFill("solid", fgColor=ALT_ROW)
THIN_SIDE  = Side(style="thin", color="CCCCCC")
THIN_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)


def _list_to_str(value) -> str:
    if isinstance(value, list):
        return "\n".join(f"• {v}" for v in value) if len(value) > 1 else (value[0] if value else "")
    return str(value) if value else ""


def _cell_value(tc: TestCase, field: str) -> str:
    val = getattr(tc, field, "")
    return _list_to_str(val)


# ─── EXCEL EXPORT ─────────────────────────────────────────────────────────────

def generate_excel(test_cases: List[TestCase], removed_count: int) -> bytes:
    wb = openpyxl.Workbook()

    # ── Sheet 1: test_cases ──────────────────────────────────────────────────
    ws = wb.active
    ws.title = "test_cases"

    # Header
    header_font   = Font(bold=True, color=HEADER_FG, size=10, name="Calibri")
    header_fill   = PatternFill("solid", fgColor=HEADER_BG)
    header_align  = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for col_idx, (col_name, _, col_width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font   = header_font
        cell.fill   = header_fill
        cell.alignment = header_align
        cell.border = THIN_BORDER
        ws.column_dimensions[get_column_letter(col_idx)].width = col_width

    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"

    # Data rows
    body_font  = Font(size=9, name="Calibri")
    body_align = Alignment(vertical="top", wrap_text=True)

    for row_idx, tc in enumerate(test_cases, start=2):
        is_alt = (row_idx % 2 == 0)
        priority_fill = PRIORITY_FILLS.get(tc.priority)

        for col_idx, (_, field, _) in enumerate(COLUMNS, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=_cell_value(tc, field))
            cell.font      = body_font
            cell.alignment = body_align
            cell.border    = THIN_BORDER
            # Priority column (col 4) gets priority colour, others get alt shading
            if col_idx == 4 and priority_fill:
                cell.fill = priority_fill
            elif is_alt:
                cell.fill = ALT_FILL

    # ── Sheet 2: Summary ─────────────────────────────────────────────────────
    ws2 = wb.create_sheet(title="Summary")
    ws2.column_dimensions["A"].width = 35
    ws2.column_dimensions["B"].width = 25

    sum_header_font = Font(bold=True, color=HEADER_FG, size=11, name="Calibri")
    sum_header_fill = PatternFill("solid", fgColor=SUMMARY_BG)
    label_font      = Font(bold=True, size=10, name="Calibri")
    value_font      = Font(size=10, name="Calibri")

    def sum_title(row: int, text: str):
        c = ws2.cell(row=row, column=1, value=text)
        c.font  = sum_header_font
        c.fill  = sum_header_fill
        ws2.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        c.alignment = Alignment(horizontal="center")

    def sum_row(row: int, label: str, value):
        lc = ws2.cell(row=row, column=1, value=label)
        vc = ws2.cell(row=row, column=2, value=value)
        lc.font = label_font
        vc.font = value_font

    # Compute stats
    from collections import Counter
    mod_cnt   = Counter(tc.module            for tc in test_cases)
    rt_cnt    = Counter(tc.requirement_type  for tc in test_cases)
    sc_cnt    = Counter(tc.scenario_type     for tc in test_cases)
    tt_cnt    = Counter(tc.testing_type      for tc in test_cases)
    pr_cnt    = Counter(tc.priority          for tc in test_cases)

    r = 1
    sum_title(r, "Test Case Generation Summary"); r += 1
    sum_row(r, "Total Test Cases Generated",    len(test_cases)); r += 1
    sum_row(r, "Duplicates Removed",            removed_count); r += 1
    sum_row(r, "Engine",                        f"Rule-Based NLP ({ENGINE})"); r += 1
    sum_row(r, "Generated On",                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")); r += 2

    sum_title(r, "By Module"); r += 1
    for mod, cnt in sorted(mod_cnt.items()):
        sum_row(r, mod, cnt); r += 1
    r += 1

    sum_title(r, "By Requirement Type"); r += 1
    for rt, cnt in sorted(rt_cnt.items()):
        sum_row(r, rt.capitalize(), cnt); r += 1
    r += 1

    sum_title(r, "By Scenario Type"); r += 1
    for st, cnt in sorted(sc_cnt.items()):
        sum_row(r, st.capitalize(), cnt); r += 1
    r += 1

    sum_title(r, "By Testing Type"); r += 1
    for tt, cnt in sorted(tt_cnt.items()):
        sum_row(r, tt.capitalize(), cnt); r += 1
    r += 1

    sum_title(r, "By Priority"); r += 1
    for pr in ["P1", "P2", "P3"]:
        sum_row(r, pr, pr_cnt.get(pr, 0)); r += 1

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ─── WORD EXPORT ──────────────────────────────────────────────────────────────

def generate_docx(test_cases: List[TestCase], removed_count: int) -> bytes:
    doc = DocxDocument()

    # Margins
    for section in doc.sections:
        section.top_margin    = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin   = Inches(0.9)
        section.right_margin  = Inches(0.9)

    # Title
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_para.add_run("Rule-Based Test Case Report")
    run.font.size  = Pt(20)
    run.font.bold  = True
    run.font.color.rgb = RGBColor(0x44, 0x72, 0xC4)

    # Meta info
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
        f"Engine: {ENGINE}  |  "
        f"Total: {len(test_cases)} test cases  |  "
        f"Duplicates removed: {removed_count}"
    ).font.size = Pt(9)

    doc.add_paragraph()

    # Group by module
    from collections import defaultdict
    by_module = defaultdict(list)
    for tc in test_cases:
        by_module[tc.module].append(tc)

    # TOC header
    toc_heading = doc.add_paragraph("Table of Contents")
    toc_heading.style = "Heading 1"
    for module in sorted(by_module.keys()):
        p = doc.add_paragraph(f"  • {module} ({len(by_module[module])} test cases)")
        p.paragraph_format.left_indent = Inches(0.3)

    doc.add_page_break()

    # Test case tables per module
    FIELD_LABELS = [
        ("Test Case ID",           "test_case_id"),
        ("Traceability Req-ID",    "traceability_req_id"),
        ("Scenario ID",            "scenario_id"),
        ("Priority",               "priority"),
        ("Objective",              "objective"),
        ("Preconditions",          "preconditions"),
        ("Test Steps",             "test_steps"),
        ("Inputs",                 "inputs"),
        ("Design Methodology",     "design_methodology"),
        ("Dependent Test Cases",   "dependent_test_cases"),
        ("Expected Outcome",       "expected_outcome"),
        ("Test Environment",       "test_environment"),
        ("Remarks",                "remarks"),
        ("Module",                 "module"),
        ("Requirement Type",       "requirement_type"),
        ("Scenario Type",          "scenario_type"),
        ("Testing Type",           "testing_type"),
    ]

    for module in sorted(by_module.keys()):
        h = doc.add_paragraph(f"Module: {module}")
        h.style = "Heading 1"

        for tc in by_module[module]:
            sub = doc.add_paragraph(f"{tc.test_case_id}  —  {tc.priority}")
            sub.style = "Heading 2"

            table = doc.add_table(rows=len(FIELD_LABELS), cols=2)
            table.style = "Table Grid"

            for row_i, (label, field) in enumerate(FIELD_LABELS):
                row = table.rows[row_i]
                # Label cell
                lc = row.cells[0]
                lc.width = Inches(2.0)
                lp = lc.paragraphs[0]
                lr = lp.add_run(label)
                lr.font.bold = True
                lr.font.size = Pt(9)

                # Value cell
                vc = row.cells[1]
                vp = vc.paragraphs[0]
                vr = vp.add_run(_cell_value(tc, field))
                vr.font.size = Pt(9)

            doc.add_paragraph()  # spacing between test cases

    # Footer
    doc.add_paragraph()
    footer_para = doc.add_paragraph(
        f"Generated by Rule-Based Test Case Tool — {datetime.now().strftime('%Y-%m-%d')}"
    )
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_para.runs[0].font.size  = Pt(8)
    footer_para.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
