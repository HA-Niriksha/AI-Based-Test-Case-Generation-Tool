"""
output_generator.py
Generates Excel and Word exports matching the One_TC.xlsx template format.

Key structure (matches One_TC.xlsx exactly):
  Row 1: Main column headers (merged groups for Inputs / Expected Outputs)
  Row 2: Signal sub-headers (actual input/output signal names from requirements)
  Row 3+: Data rows — one per test scenario

Column layout:
  A  Requirement_ID
  B  TC_ID
  C  Scenario No
  D  Module
  E  Test Objective
  F  Test Precondition
  G  Test Steps
  H+ [Input signal columns — dynamic, from parsed test cases]
  …  [Output signal columns — dynamic]
  …  Depands On
  …  Remarks/Additional information
  …  Methodology
  …  Req_Type
  …  Scenario_Type
"""

import io
import re
from datetime import datetime
from typing import List, Dict, Tuple

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from models import TestCase
from config import ENGINE


# ─── COLOUR CONSTANTS ─────────────────────────────────────────────────────────

HEADER_BG     = "4472C4"    # Blue (main header row)
HEADER_FG     = "FFFFFF"
SUBHEADER_BG  = "8EB4E3"    # Light blue (signal sub-header row)
SUBHEADER_FG  = "000000"
ALT_ROW       = "EEF2F9"
P1_FILL       = "FFD7D7"
P2_FILL       = "FFE8CC"
P3_FILL       = "FFFACC"
SUMMARY_BG    = "2F4F8F"
INPUT_COL_BG  = "E2F0CB"    # Light green for input signal columns
OUTPUT_COL_BG = "FCE4D6"    # Light orange for output signal columns


THIN_SIDE   = Side(style="thin", color="CCCCCC")
THIN_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)

ALT_FILL  = PatternFill("solid", fgColor=ALT_ROW)
IN_FILL   = PatternFill("solid", fgColor=INPUT_COL_BG)
OUT_FILL  = PatternFill("solid", fgColor=OUTPUT_COL_BG)


# ─── STATIC COLUMN DEFINITIONS ────────────────────────────────────────────────
# These columns appear before (prefix) and after (suffix) the dynamic signal cols

STATIC_PREFIX = [
    # (excel_header, tc_field_or_None,  col_width)
    ("Requirement_ID",                "traceability_req_id", 18),
    ("TC_ID",                         "test_case_id",        14),
    ("Scenario No",                   "scenario_id",         12),
    ("Module",                        "module",              20),
    ("Test Objective",                "objective",           42),
    ("Test Precondition",             "preconditions",       35),
    ("Test Steps",                    "test_steps",          42),
]

STATIC_SUFFIX = [
    ("Depands On",                    "dependent_test_cases", 20),
    ("Remarks/Additional information","remarks",              45),
    ("Methodology",                   "design_methodology",   22),
    ("Req_Type",                      "requirement_type",     16),
    ("Scenario_Type",                 "scenario_type",        14),
]


# ─── INPUT / OUTPUT SIGNAL EXTRACTION ─────────────────────────────────────────

_KV_PATTERN = re.compile(r'^(.+?):\s*(.+)$')


def _parse_signal_value(entry: str) -> Tuple[str, str]:
    """
    Parses 'Signal Name: value' → (signal_name, value).
    Falls back to (entry, entry) if not key-value.
    """
    m = _KV_PATTERN.match(entry.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return entry.strip(), entry.strip()


def extract_signal_columns(test_cases: List[TestCase]) -> Tuple[List[str], List[str]]:
    """
    Scans all test cases to collect the full ordered set of unique input signal
    names and output signal names.

    Input signals: from tc.inputs (entries in 'Name: value' format)
    Output signals: inferred from tc.expected_outcome ('Name = value' patterns)

    Returns:
      (input_signal_names, output_signal_names)
    """
    input_signals_ordered: List[str]  = []
    output_signals_ordered: List[str] = []
    seen_inputs:  set = set()
    seen_outputs: set = set()

    for tc in test_cases:
        for entry in tc.inputs:
            name, _ = _parse_signal_value(entry)
            if name and name not in seen_inputs:
                seen_inputs.add(name)
                input_signals_ordered.append(name)

        # Parse expected_outcome: "SignalName = Value" or "SignalName: Value"
        for m in re.finditer(r'([\w\s]{3,50}?)\s*[=:]\s*(\w+)', tc.expected_outcome):
            name = m.group(1).strip()
            # Skip generic phrases (but not avionics signal names)
            if any(skip in name.lower() for skip in [
                "system successfully", "response is", "data is", "result is",
                "all sub", "no data", "logic module", "specification",
                "test case", "is correct", "the logic", "and sets"
            ]):
                continue
            if len(name.split()) <= 6 and name not in seen_outputs:
                seen_outputs.add(name)
                output_signals_ordered.append(name)

    return input_signals_ordered, output_signals_ordered


def _get_signal_value(tc: TestCase, signal_name: str, kind: str) -> str:
    """
    Returns the value for a specific signal from a test case.
    kind = 'input' | 'output'
    """
    if kind == "input":
        for entry in tc.inputs:
            name, value = _parse_signal_value(entry)
            if name.lower() == signal_name.lower():
                return value
        return ""
    else:
        # Output: scan expected_outcome
        for m in re.finditer(r'([\w\s]{3,50}?)\s*[=:]\s*(\w+)', tc.expected_outcome):
            name = m.group(1).strip()
            if name.lower() == signal_name.lower():
                return m.group(2).strip()
        return ""


# ─── HELPER FORMATTERS ────────────────────────────────────────────────────────

def _list_to_str(value) -> str:
    if isinstance(value, list):
        return "\n".join(str(v) for v in value if v)
    return str(value) if value else ""


def _cell_value(tc: TestCase, field: str) -> str:
    val = getattr(tc, field, "")
    return _list_to_str(val)


# ─── EXCEL EXPORT ─────────────────────────────────────────────────────────────

def generate_excel(test_cases: List[TestCase], removed_count: int) -> bytes:
    """
    Generates an Excel workbook matching the One_TC.xlsx template structure:
    - Row 1: Main column headers (with merged cells over Input/Output groups)
    - Row 2: Signal sub-header row (actual input/output signal names)
    - Row 3+: Data rows
    Two additional sheets: Summary (stats) and By_Scenario_Type (segregated).
    """
    wb = openpyxl.Workbook()

    # ── Sheet 1: test_cases ─────────────────────────────────────────────────
    ws = wb.active
    ws.title = "test_cases"

    # Determine dynamic signal columns
    input_signals, output_signals = extract_signal_columns(test_cases)

    # Build full column list for layout:
    #   prefix cols | input signal cols | output signal cols | suffix cols
    n_prefix = len(STATIC_PREFIX)
    n_inputs = len(input_signals)
    n_outputs = len(output_signals)
    n_suffix = len(STATIC_SUFFIX)

    total_cols = n_prefix + n_inputs + n_outputs + n_suffix

    header_font    = Font(bold=True, color=HEADER_FG, size=10, name="Calibri")
    header_fill    = PatternFill("solid", fgColor=HEADER_BG)
    header_align   = Alignment(horizontal="center", vertical="center", wrap_text=True)

    subheader_font  = Font(bold=True, color=SUBHEADER_FG, size=9, name="Calibri")
    subheader_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    body_font  = Font(size=9, name="Calibri")
    body_align = Alignment(vertical="top", wrap_text=True)

    # ── Row 1: Main headers ──────────────────────────────────────────────────
    col = 1
    for (hdr, _, width) in STATIC_PREFIX:
        cell = ws.cell(row=1, column=col, value=hdr)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = header_align
        cell.border    = THIN_BORDER
        ws.column_dimensions[get_column_letter(col)].width = width
        # Prefix cols: merge rows 1 and 2 (no sub-header)
        ws.merge_cells(start_row=1, start_column=col, end_row=2, end_column=col)
        col += 1

    # "Inputs" merged header over all input signal columns
    if n_inputs > 0:
        inputs_start_col = col
        cell = ws.cell(row=1, column=col, value="Inputs")
        cell.font      = header_font
        cell.fill      = PatternFill("solid", fgColor="375623")  # dark green
        cell.alignment = header_align
        cell.border    = THIN_BORDER
        if n_inputs > 1:
            ws.merge_cells(start_row=1, start_column=col, end_row=1, end_column=col + n_inputs - 1)
        for i, sig in enumerate(input_signals):
            c = col + i
            ws.column_dimensions[get_column_letter(c)].width = max(18, len(sig) + 4)
        col += n_inputs

    # "Expected Outputs" merged header over all output signal columns
    if n_outputs > 0:
        outputs_start_col = col
        cell = ws.cell(row=1, column=col, value="Expected Outputs")
        cell.font      = header_font
        cell.fill      = PatternFill("solid", fgColor="833C00")  # dark orange
        cell.alignment = header_align
        cell.border    = THIN_BORDER
        if n_outputs > 1:
            ws.merge_cells(start_row=1, start_column=col, end_row=1, end_column=col + n_outputs - 1)
        for i, sig in enumerate(output_signals):
            c = col + i
            ws.column_dimensions[get_column_letter(c)].width = max(22, len(sig) + 4)
        col += n_outputs
    else:
        outputs_start_col = col

    for (hdr, _, width) in STATIC_SUFFIX:
        cell = ws.cell(row=1, column=col, value=hdr)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = header_align
        cell.border    = THIN_BORDER
        ws.column_dimensions[get_column_letter(col)].width = width
        ws.merge_cells(start_row=1, start_column=col, end_row=2, end_column=col)
        col += 1

    ws.row_dimensions[1].height = 30

    # ── Row 2: Signal sub-headers ────────────────────────────────────────────
    col = n_prefix + 1
    for i, sig in enumerate(input_signals):
        c = ws.cell(row=2, column=col + i, value=sig)
        c.font      = subheader_font
        c.fill      = PatternFill("solid", fgColor=INPUT_COL_BG)
        c.alignment = subheader_align
        c.border    = THIN_BORDER
    col += n_inputs
    for i, sig in enumerate(output_signals):
        c = ws.cell(row=2, column=col + i, value=sig)
        c.font      = subheader_font
        c.fill      = PatternFill("solid", fgColor=OUTPUT_COL_BG)
        c.alignment = subheader_align
        c.border    = THIN_BORDER

    ws.row_dimensions[2].height = 25
    ws.freeze_panes = "A3"

    # ── Data rows (start at row 3) ───────────────────────────────────────────
    for row_idx, tc in enumerate(test_cases, start=3):
        is_alt = (row_idx % 2 == 0)
        col = 1

        # Prefix static columns
        for (_, field, _) in STATIC_PREFIX:
            cell = ws.cell(row=row_idx, column=col, value=_cell_value(tc, field))
            cell.font      = body_font
            cell.alignment = body_align
            cell.border    = THIN_BORDER
            if is_alt:
                cell.fill = ALT_FILL
            col += 1

        # Input signal columns
        for sig in input_signals:
            val = _get_signal_value(tc, sig, "input")
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.font      = body_font
            cell.alignment = Alignment(horizontal="center", vertical="top")
            cell.border    = THIN_BORDER
            cell.fill      = IN_FILL
            col += 1

        # Output signal columns
        for sig in output_signals:
            val = _get_signal_value(tc, sig, "output")
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.font      = body_font
            cell.alignment = Alignment(horizontal="center", vertical="top")
            cell.border    = THIN_BORDER
            cell.fill      = OUT_FILL
            col += 1

        # Suffix static columns
        for (_, field, _) in STATIC_SUFFIX:
            cell = ws.cell(row=row_idx, column=col, value=_cell_value(tc, field))
            cell.font      = body_font
            cell.alignment = body_align
            cell.border    = THIN_BORDER
            if is_alt:
                cell.fill = ALT_FILL
            col += 1

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

    from collections import Counter
    mod_cnt = Counter(tc.module            for tc in test_cases)
    rt_cnt  = Counter(tc.requirement_type  for tc in test_cases)
    sc_cnt  = Counter(tc.scenario_type     for tc in test_cases)
    tt_cnt  = Counter(tc.testing_type      for tc in test_cases)
    pr_cnt  = Counter(tc.priority          for tc in test_cases)

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


def _write_tc_row(ws, row_idx: int, tc: TestCase,
                  input_signals: List[str], output_signals: List[str]):
    """Write one data row for a test case into worksheet ws at row_idx."""
    is_alt = (row_idx % 2 == 0)
    body_font  = Font(size=9, name="Calibri")
    body_align = Alignment(vertical="top", wrap_text=True)

    col = 1
    for (_, field, _) in STATIC_PREFIX:
        cell = ws.cell(row=row_idx, column=col, value=_cell_value(tc, field))
        cell.font = body_font; cell.alignment = body_align; cell.border = THIN_BORDER
        if is_alt: cell.fill = ALT_FILL
        col += 1
    for sig in input_signals:
        val = _get_signal_value(tc, sig, "input")
        cell = ws.cell(row=row_idx, column=col, value=val)
        cell.font = body_font
        cell.alignment = Alignment(horizontal="center", vertical="top")
        cell.border = THIN_BORDER; cell.fill = IN_FILL
        col += 1
    for sig in output_signals:
        val = _get_signal_value(tc, sig, "output")
        cell = ws.cell(row=row_idx, column=col, value=val)
        cell.font = body_font
        cell.alignment = Alignment(horizontal="center", vertical="top")
        cell.border = THIN_BORDER; cell.fill = OUT_FILL
        col += 1
    for (_, field, _) in STATIC_SUFFIX:
        cell = ws.cell(row=row_idx, column=col, value=_cell_value(tc, field))
        cell.font = body_font; cell.alignment = body_align; cell.border = THIN_BORDER
        if is_alt: cell.fill = ALT_FILL
        col += 1


def _write_header_rows(ws, input_signals: List[str], output_signals: List[str]):
    """Write the 2-row header (main + signal sub-headers) into a worksheet."""
    header_font    = Font(bold=True, color=HEADER_FG, size=10, name="Calibri")
    header_fill    = PatternFill("solid", fgColor=HEADER_BG)
    header_align   = Alignment(horizontal="center", vertical="center", wrap_text=True)
    subheader_font = Font(bold=True, size=9, name="Calibri")
    subheader_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    n_prefix = len(STATIC_PREFIX)
    n_inputs = len(input_signals)
    n_outputs = len(output_signals)

    col = 1
    for (hdr, _, width) in STATIC_PREFIX:
        cell = ws.cell(row=1, column=col, value=hdr)
        cell.font = header_font; cell.fill = header_fill
        cell.alignment = header_align; cell.border = THIN_BORDER
        ws.column_dimensions[get_column_letter(col)].width = width
        ws.merge_cells(start_row=1, start_column=col, end_row=2, end_column=col)
        col += 1
    if n_inputs > 0:
        cell = ws.cell(row=1, column=col, value="Inputs")
        cell.font = header_font
        cell.fill = PatternFill("solid", fgColor="375623")
        cell.alignment = header_align; cell.border = THIN_BORDER
        if n_inputs > 1:
            ws.merge_cells(start_row=1, start_column=col, end_row=1, end_column=col + n_inputs - 1)
        for i, sig in enumerate(input_signals):
            c = col + i
            ws.column_dimensions[get_column_letter(c)].width = max(18, len(sig) + 4)
            sh = ws.cell(row=2, column=c, value=sig)
            sh.font = subheader_font
            sh.fill = PatternFill("solid", fgColor=INPUT_COL_BG)
            sh.alignment = subheader_align; sh.border = THIN_BORDER
        col += n_inputs
    if n_outputs > 0:
        cell = ws.cell(row=1, column=col, value="Expected Outputs")
        cell.font = header_font
        cell.fill = PatternFill("solid", fgColor="833C00")
        cell.alignment = header_align; cell.border = THIN_BORDER
        if n_outputs > 1:
            ws.merge_cells(start_row=1, start_column=col, end_row=1, end_column=col + n_outputs - 1)
        for i, sig in enumerate(output_signals):
            c = col + i
            ws.column_dimensions[get_column_letter(c)].width = max(22, len(sig) + 4)
            sh = ws.cell(row=2, column=c, value=sig)
            sh.font = subheader_font
            sh.fill = PatternFill("solid", fgColor=OUTPUT_COL_BG)
            sh.alignment = subheader_align; sh.border = THIN_BORDER
        col += n_outputs
    for (hdr, _, width) in STATIC_SUFFIX:
        cell = ws.cell(row=1, column=col, value=hdr)
        cell.font = header_font; cell.fill = header_fill
        cell.alignment = header_align; cell.border = THIN_BORDER
        ws.column_dimensions[get_column_letter(col)].width = width
        ws.merge_cells(start_row=1, start_column=col, end_row=2, end_column=col)
        col += 1
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 25
    ws.freeze_panes = "A3"


def _build_segregated_sheet(wb, test_cases: List[TestCase],
                              input_signals: List[str], output_signals: List[str]):
    """
    Sheet: Segregated
    Organises test cases with section-break rows:
      1) By Req_Type (Functional / Non-Functional)
      2) Within each type, by Scenario_Type (Normal, Boundary, Edge, Robustness)
    Spec §5: segregate by Req_Type and Scenario_Type.
    """
    ws = wb.create_sheet(title="Segregated")
    _write_header_rows(ws, input_signals, output_signals)

    grp_header_font = Font(bold=True, color="FFFFFF", size=10, name="Calibri")
    grp_fills = {
        "functional":     PatternFill("solid", fgColor="17375E"),
        "non-functional": PatternFill("solid", fgColor="4E4E4E"),
        "normal":         PatternFill("solid", fgColor="1F7145"),
        "boundary":       PatternFill("solid", fgColor="843C0C"),
        "edge":           PatternFill("solid", fgColor="7B3F00"),
        "robustness":     PatternFill("solid", fgColor="632523"),
    }

    total_cols = len(STATIC_PREFIX) + len(input_signals) + len(output_signals) + len(STATIC_SUFFIX)

    row_idx = 3
    for req_type in ("functional", "non-functional"):
        type_tcs = [tc for tc in test_cases if tc.requirement_type == req_type]
        if not type_tcs:
            continue
        # Section header: Req_Type
        cell = ws.cell(row=row_idx, column=1, value=f"  ▶  Requirement Type: {req_type.upper()}")
        cell.font = grp_header_font
        cell.fill = grp_fills.get(req_type, grp_fills["functional"])
        cell.alignment = Alignment(horizontal="left", vertical="center")
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=total_cols)
        row_idx += 1

        for scenario_type in ("normal", "boundary", "edge", "robustness"):
            sc_tcs = [tc for tc in type_tcs if tc.scenario_type == scenario_type]
            if not sc_tcs:
                continue
            # Sub-section header: Scenario_Type
            cell = ws.cell(row=row_idx, column=1,
                           value=f"    → Scenario Type: {scenario_type.capitalize()} ({len(sc_tcs)} test cases)")
            cell.font = grp_header_font
            cell.fill = grp_fills.get(scenario_type, ALT_FILL)
            cell.alignment = Alignment(horizontal="left", vertical="center")
            ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=total_cols)
            row_idx += 1

            for tc in sc_tcs:
                _write_tc_row(ws, row_idx, tc, input_signals, output_signals)
                row_idx += 1


def _build_module_sheet(wb, test_cases: List[TestCase],
                         input_signals: List[str], output_signals: List[str]):
    """
    Sheet: By_Module
    Groups test cases by module (detected from bold heading structure).
    Spec §5.3: segregate by module based on document heading structure.
    """
    ws = wb.create_sheet(title="By_Module")
    _write_header_rows(ws, input_signals, output_signals)

    grp_header_font = Font(bold=True, color="FFFFFF", size=10, name="Calibri")
    mod_fill = PatternFill("solid", fgColor="2E4057")
    total_cols = len(STATIC_PREFIX) + len(input_signals) + len(output_signals) + len(STATIC_SUFFIX)

    from collections import defaultdict
    by_module = defaultdict(list)
    for tc in test_cases:
        by_module[tc.module].append(tc)

    row_idx = 3
    for module in sorted(by_module.keys()):
        tcs = by_module[module]
        cell = ws.cell(row=row_idx, column=1,
                       value=f"  ▶  Module: {module}  ({len(tcs)} test cases)")
        cell.font = grp_header_font
        cell.fill = mod_fill
        cell.alignment = Alignment(horizontal="left", vertical="center")
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=total_cols)
        row_idx += 1
        for tc in tcs:
            _write_tc_row(ws, row_idx, tc, input_signals, output_signals)
            row_idx += 1


# ─── WORD EXPORT ──────────────────────────────────────────────────────────────

def generate_docx(test_cases: List[TestCase], removed_count: int) -> bytes:
    doc = DocxDocument()

    for section in doc.sections:
        section.top_margin    = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin   = Inches(0.9)
        section.right_margin  = Inches(0.9)

    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_para.add_run("Rule-Based Test Case Report")
    run.font.size  = Pt(20)
    run.font.bold  = True
    run.font.color.rgb = RGBColor(0x44, 0x72, 0xC4)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
        f"Engine: {ENGINE}  |  "
        f"Total: {len(test_cases)} test cases  |  "
        f"Duplicates removed: {removed_count}"
    ).font.size = Pt(9)
    doc.add_paragraph()

    from collections import defaultdict
    by_module = defaultdict(list)
    for tc in test_cases:
        by_module[tc.module].append(tc)

    toc_heading = doc.add_paragraph("Table of Contents")
    toc_heading.style = "Heading 1"
    for module in sorted(by_module.keys()):
        p = doc.add_paragraph(f"  • {module} ({len(by_module[module])} test cases)")
        p.paragraph_format.left_indent = Inches(0.3)
    doc.add_page_break()

    FIELD_LABELS = [
        ("Test Case ID",           "test_case_id"),
        ("Traceability Req-ID",    "traceability_req_id"),
        ("Scenario No",            "scenario_id"),
        ("Test Objective",         "objective"),
        ("Test Precondition",      "preconditions"),
        ("Test Steps",             "test_steps"),
        ("Inputs",                 "inputs"),
        ("Design Methodology",     "design_methodology"),
        ("Depands On",             "dependent_test_cases"),
        ("Expected Outcome",       "expected_outcome"),
        ("Remarks/Additional Info","remarks"),
        ("Module",                 "module"),
        ("Req_Type",               "requirement_type"),
        ("Scenario_Type",          "scenario_type"),
        ("Testing Type",           "testing_type"),
    ]

    for module in sorted(by_module.keys()):
        h = doc.add_paragraph(f"Module: {module}")
        h.style = "Heading 1"

        for tc in by_module[module]:
            sub = doc.add_paragraph(f"{tc.test_case_id}  |  {tc.scenario_type.capitalize()}")
            sub.style = "Heading 2"

            table = doc.add_table(rows=len(FIELD_LABELS), cols=2)
            table.style = "Table Grid"

            for row_i, (label, field) in enumerate(FIELD_LABELS):
                row = table.rows[row_i]
                lc = row.cells[0]; lc.width = Inches(2.0)
                lp = lc.paragraphs[0]; lr = lp.add_run(label)
                lr.font.bold = True; lr.font.size = Pt(9)
                vc = row.cells[1]; vp = vc.paragraphs[0]
                vr = vp.add_run(_cell_value(tc, field))
                vr.font.size = Pt(9)

            doc.add_paragraph()

    doc.add_paragraph()
    footer_para = doc.add_paragraph(
        f"Generated by Rule-Based Test Case Tool — {datetime.now().strftime('%Y-%m-%d')}"
    )
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_para.runs[0].font.size = Pt(8)
    footer_para.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
