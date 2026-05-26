# backend/mcp_client.py
# Calls the MCP server from within the FastAPI backend.
# Used when the React UI requests generation and MCP is enabled.
# Falls back silently — never crashes the generation pipeline.

import json
import subprocess
import os
import sys
import logging
from typing import List, Optional

from models import TestCase, DocumentChunk
from test_case_generator import (
    assign_priority,
    assign_environment,
)

logger = logging.getLogger(__name__)

BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
MCP_SCRIPT   = os.path.join(BACKEND_DIR, "mcp_server.py")
PYTHON_EXE   = sys.executable
TIMEOUT_SECS = 120   # 2 minutes per chunk


def generate_via_mcp(
    chunks: List[DocumentChunk],
    review_points: dict,
) -> Optional[List[TestCase]]:
    """
    Generates test cases for all chunks by calling mcp_server.py
    as a subprocess for each chunk.

    Returns list of TestCase objects or None if MCP is unavailable.
    Falls back to None on any error — caller uses rule-based engine.
    """
    if not os.path.exists(MCP_SCRIPT):
        logger.warning("mcp_server.py not found — skipping MCP")
        return None

    all_test_cases: List[TestCase] = []
    tc_counters = {"VD": 0, "IT": 0, "UT": 0}
    prefix_map  = {
        "validation": "VD",
        "integration": "IT",
        "verification": "UT",
    }
    sc_counter = 1

    for chunk in chunks:
        if not chunk.requirement_ids:
            continue

        primary_id = chunk.requirement_ids[0]

        try:
            # Call mcp_server generate_test_cases tool directly via Python
            call_script = f"""
import sys, json, os
sys.path.insert(0, r'{BACKEND_DIR}')
from document_ingestion import ingest_document
from test_case_generator import generate_all

prefixed = {json.dumps(primary_id + ' ' + chunk.content)}
chunks   = ingest_document(prefixed)
if chunks:
    review_points = {json.dumps(review_points)}
    tcs, removed = generate_all(chunks, review_points)
    result = {{
        "test_cases": [
            {{
                "tc_id":         tc.test_case_id,
                "req_id":        tc.traceability_req_id,
                "scenario_no":   tc.scenario_id,
                "priority":      tc.priority,
                "module":        tc.module,
                "objective":     tc.objective,
                "preconditions": tc.preconditions,
                "steps":         tc.test_steps,
                "inputs":        tc.inputs,
                "expected":      tc.expected_outcome,
                "methodology":   tc.design_methodology,
                "dependent":     tc.dependent_test_cases,
                "remarks":       tc.remarks,
                "req_type":      tc.requirement_type,
                "scenario_type": tc.scenario_type,
                "testing_type":  tc.testing_type,
            }}
            for tc in tcs
        ]
    }}
else:
    result = {{"test_cases": []}}
print(json.dumps(result))
"""
            proc = subprocess.run(
                [PYTHON_EXE, "-c", call_script],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECS,
                cwd=BACKEND_DIR,
            )

            if proc.returncode != 0:
                logger.warning(
                    f"MCP subprocess error for {primary_id}: "
                    f"{proc.stderr[:200]}"
                )
                continue

            output = proc.stdout.strip()
            if not output:
                continue

            data      = json.loads(output)
            tc_list   = data.get("test_cases", [])
            chunk_tcs = _build_test_cases(
                tc_list, chunk, tc_counters, sc_counter, prefix_map
            )
            all_test_cases.extend(chunk_tcs)
            sc_counter += len(chunk_tcs)

            logger.info(
                f"MCP generated {len(chunk_tcs)} TCs for {primary_id}"
            )

        except subprocess.TimeoutExpired:
            logger.warning(f"MCP timeout for {primary_id} — skipping")
            continue
        except Exception as e:
            logger.warning(f"MCP error for {primary_id}: {e} — skipping")
            continue

    return all_test_cases if all_test_cases else None


def _build_test_cases(
    tc_list:     list,
    chunk:       DocumentChunk,
    tc_counters: dict,
    sc_counter:  int,
    prefix_map:  dict,
) -> List[TestCase]:
    """Converts raw dict list into validated TestCase objects."""
    results = []

    for tc_data in tc_list:
        testing_type = tc_data.get("testing_type", "verification")
        prefix       = prefix_map.get(testing_type, "UT")
        tc_counters[prefix] += 1

        try:
            results.append(TestCase(
                traceability_req_id  = tc_data.get("req_id", chunk.requirement_ids[0]),
                test_case_id         = tc_data.get("tc_id", f"TC_{prefix}_{tc_counters[prefix]:03d}"),
                scenario_id          = tc_data.get("scenario_no", f"SC-{sc_counter:03d}"),
                priority             = tc_data.get("priority", "P1"),
                objective            = tc_data.get("objective", ""),
                preconditions        = tc_data.get("preconditions", []),
                test_steps           = tc_data.get("steps", []),
                inputs               = tc_data.get("inputs", []),
                design_methodology   = tc_data.get("methodology", "Black Box Testing"),
                dependent_test_cases = tc_data.get("dependent", "None"),
                expected_outcome     = tc_data.get("expected", ""),
                test_environment     = assign_environment(testing_type),
                remarks              = tc_data.get("remarks", ""),
                module               = tc_data.get("module", chunk.module),
                requirement_type     = tc_data.get("req_type", chunk.requirement_type),
                scenario_type        = tc_data.get("scenario_type", "normal"),
                testing_type         = testing_type,
            ))
        except Exception as e:
            logger.warning(f"Could not build TestCase: {e}")
            continue

    return results
