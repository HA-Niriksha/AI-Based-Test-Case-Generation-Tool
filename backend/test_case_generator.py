import re
import logging
from difflib import SequenceMatcher
from typing import List, Tuple, Dict

from models import TestCase, DocumentChunk
from constants import (
    MODULE_KEYWORDS, FUNCTIONAL_VERBS, SECURITY_KEYWORDS,
    PERFORMANCE_KEYWORDS, INTEGRATION_KEYWORDS, VALIDATION_ACTION_WORDS,
    BOUNDARY_TRIGGERS, STEP_TEMPLATES, INPUT_TEMPLATES,
    PRECONDITION_TEMPLATES, EXPECTED_OUTCOME_TEMPLATES,
)
from config import DEDUP_THRESHOLD

logger = logging.getLogger(__name__)

# ─── NLP SETUP ───────────────────────────────────────────────────────────────

_NLP = None

def get_nlp():
    return None  # use regex fallback — no spaCy dependency


def is_spacy_available() -> bool:
    try:
        import spacy
        return True
    except ImportError:
        return False


# ─── SENTENCE EXTRACTION ─────────────────────────────────────────────────────

def extract_requirement_sentences(text: str) -> List[str]:
    nlp = get_nlp()
    if nlp is not None:
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents]
    else:
        sentences = re.split(r'(?<=[.!?])\s+', text)

    filtered = []
    for s in sentences:
        s = s.strip()
        word_count = len(s.split())
        if word_count >= 8:
            filtered.append(s)
    return filtered if filtered else [text[:500]]


# ─── SUBJECT / ACTION EXTRACTION ─────────────────────────────────────────────

def extract_subject(sentence: str) -> str:
    nlp = get_nlp()
    if nlp is not None:
        doc = nlp(sentence)
        # Try dependency parse for subject
        for chunk in doc.noun_chunks:
            if chunk.root.dep_ in ("nsubj", "nsubjpass"):
                return chunk.text.strip()
        # Fall back to first noun chunk
        for chunk in doc.noun_chunks:
            return chunk.text.strip()
    # Regex fallback: look for "the system", "the user", "the application", etc.
    match = re.search(r'\b(the system|the user|the application|the module|the service)\b', sentence, re.IGNORECASE)
    if match:
        return match.group(0)
    # Return first 4 words as subject
    words = sentence.split()
    return " ".join(words[:min(4, len(words))])


def extract_action(sentence: str) -> str:
    lower = sentence.lower()
    # Look for modal + verb pattern
    for verb in FUNCTIONAL_VERBS:
        if verb in lower:
            idx = lower.find(verb)
            fragment = sentence[idx:idx + 70]
            # Cut at first period or newline
            fragment = re.split(r'[.\n]', fragment)[0].strip()
            return fragment if len(fragment) > 3 else verb
    # Regex: find first main verb
    match = re.search(r'\b(shall|must|should|will|can)\s+(\w+)', sentence, re.IGNORECASE)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    nlp = get_nlp()
    if nlp is not None:
        doc = nlp(sentence)
        for token in doc:
            if token.pos_ == "VERB" and token.dep_ in ("ROOT", "relcl", "advcl"):
                return sentence[token.idx: token.idx + 60].split(".")[0].strip()
    return "perform the specified operation"


# ─── ASSIGNMENT FUNCTIONS ─────────────────────────────────────────────────────

def assign_priority(req_type: str, scenario_type: str, testing_type: str) -> str:
    if req_type == "functional" and scenario_type == "normal" and testing_type in ("validation", "integration"):
        return "P1"
    if req_type == "functional" and scenario_type == "boundary":
        return "P1"
    if req_type == "functional" and scenario_type == "normal":
        return "P1"
    if req_type == "non-functional" and scenario_type == "normal":
        return "P2"
    if scenario_type in ("edge", "robustness"):
        return "P2"
    if req_type == "non-functional" and scenario_type in ("boundary", "edge"):
        return "P3"
    return "P2"


def assign_methodology(sentence: str, scenario_type: str) -> str:
    lower = sentence.lower()
    if any(k in lower for k in SECURITY_KEYWORDS):
        return "Security Testing"
    if any(k in lower for k in PERFORMANCE_KEYWORDS):
        return "Performance Testing"
    return {
        "normal": "Black Box Testing",
        "boundary": "Boundary Value Analysis",
        "edge": "Equivalence Partitioning",
        "robustness": "Error Guessing",
    }[scenario_type]


def assign_testing_type(sentence: str, module: str) -> str:
    lower = sentence.lower()
    # Count module keyword hits
    module_hits = sum(1 for m in MODULE_KEYWORDS if m.lower() in lower)
    if module_hits >= 2 or any(k in lower for k in INTEGRATION_KEYWORDS):
        return "integration"
    if any(k in lower for k in VALIDATION_ACTION_WORDS):
        return "validation"
    return "verification"


def assign_environment(testing_type: str) -> str:
    return {
        "verification": "Dev",
        "validation": "UAT",
        "integration": "QA",
    }.get(testing_type, "QA")


# ─── REMARKS GENERATION ───────────────────────────────────────────────────────

def generate_remarks(sentence: str, req_id: str) -> str:
    lower = sentence.lower()
    remarks = []

    if not any(k in lower for k in BOUNDARY_TRIGGERS):
        remarks.append("No boundary values specified in SRS — define min/max constraints before testing")

    if any(k in lower for k in SECURITY_KEYWORDS):
        remarks.append("PII/security risk — ensure data masking and credential rotation in test environment")

    if any(w in lower for w in ["payment", "card", "bank", "billing", "invoice", "transaction", "credit"]):
        remarks.append("PCI-DSS compliance concern — use tokenised/synthetic test data only, no real card data")

    if any(k in lower for k in INTEGRATION_KEYWORDS):
        remarks.append("External system dependency detected — mock/stub required for isolated unit testing")

    if any(w in lower for w in ["concurrent", "parallel", "simultaneous", "race", "multi-user"]):
        remarks.append("Race condition risk — concurrency and load testing strongly recommended")

    if "error" not in lower and "fail" not in lower and "invalid" not in lower and "reject" not in lower:
        remarks.append("No error handling path specified in SRS — negative scenario coverage is assumed")

    if not remarks:
        remarks.append(f"Verify this test case against SRS section {req_id} before execution")

    return ". ".join(remarks) + "."


# ─── DEPENDENCY RESOLUTION ────────────────────────────────────────────────────

def resolve_dependencies(scenario_type: str, previous: List[TestCase], req_id: str) -> str:
    if scenario_type == "normal":
        return "None"
    # Boundary, edge, robustness depend on the last normal test for the same req
    normals = [
        tc.test_case_id for tc in previous
        if tc.scenario_type == "normal" and tc.traceability_req_id == req_id
    ]
    return normals[-1] if normals else "None"


# ─── CORE GENERATION ─────────────────────────────────────────────────────────

def generate_for_chunk(
    chunk: DocumentChunk,
    tc_counters: Dict[str, int],
    sc_counter: int,
    review_points: dict,
) -> Tuple[List[TestCase], int]:
    """
    Generates test cases for all sentences in a chunk.
    Returns (test_cases, updated_sc_counter).
    """
    sentences = extract_requirement_sentences(chunk.content)
    results: List[TestCase] = []

    # If RP2 is off, only generate 'normal' scenario
    scenario_types = (
        ("normal", "boundary", "edge", "robustness")
        if review_points.get("rp2", True)
        else ("normal",)
    )

    prefix_map = {"validation": "VD", "integration": "IT", "verification": "UT"}

    for req_id in chunk.requirement_ids:
        for sentence in sentences:
            # RP3: testing type assignment
            if review_points.get("rp3", True):
                testing_type = assign_testing_type(sentence, chunk.module)
            else:
                testing_type = "verification"

            env = assign_environment(testing_type)
            prefix = prefix_map[testing_type]
            subject = extract_subject(sentence)
            action = extract_action(sentence)

            # RP4: remarks
            remarks = (
                generate_remarks(sentence, req_id)
                if review_points.get("rp4", True)
                else f"Verify against SRS section {req_id} before execution."
            )

            for scenario_type in scenario_types:
                tc_counters[prefix] += 1
                tc_id = f"TC_{prefix}_{tc_counters[prefix]:03d}"
                sc_id = f"SC-{sc_counter:03d}"

                priority = assign_priority(chunk.requirement_type, scenario_type, testing_type)
                methodology = assign_methodology(sentence, scenario_type)

                # Build steps
                steps = [
                    s.format(
                        subject=subject,
                        action=action,
                        edge_input="concurrent request / session timeout / state transition",
                        robustness_input="SQL injection / XSS payload / oversized input",
                    )
                    for s in STEP_TEMPLATES[scenario_type]
                ]

                # Build inputs
                inputs = [
                    t.format(subject=subject)
                    for t in INPUT_TEMPLATES[scenario_type]
                ]

                # Build preconditions
                preconditions = [
                    t.format(module=chunk.module, subject=subject, env=env)
                    for t in PRECONDITION_TEMPLATES[scenario_type]
                ]

                # Build expected outcome
                expected = EXPECTED_OUTCOME_TEMPLATES[scenario_type].format(action=action)

                # Dependency
                deps = resolve_dependencies(scenario_type, results, req_id)

                results.append(TestCase(
                    traceability_req_id=req_id,
                    test_case_id=tc_id,
                    scenario_id=sc_id,
                    priority=priority,
                    objective=f"Verify that {subject} can {action} under {scenario_type} conditions",
                    preconditions=preconditions,
                    test_steps=steps,
                    inputs=inputs,
                    design_methodology=methodology,
                    dependent_test_cases=deps,
                    expected_outcome=expected,
                    test_environment=env,
                    remarks=remarks,
                    module=chunk.module,
                    requirement_type=chunk.requirement_type,
                    scenario_type=scenario_type,
                    testing_type=testing_type,
                ))

            sc_counter += 1

    return results, sc_counter


# ─── DEDUPLICATION ────────────────────────────────────────────────────────────

def deduplicate(test_cases: List[TestCase]) -> Tuple[List[TestCase], int]:
    kept, seen, removed = [], [], 0
    for tc in test_cases:
        is_dup = any(
            SequenceMatcher(None, tc.objective.lower(), s.lower()).ratio() > DEDUP_THRESHOLD
            for s in seen
        )
        if is_dup:
            removed += 1
            logger.debug(f"Duplicate removed: {tc.test_case_id} — {tc.objective[:60]}")
        else:
            seen.append(tc.objective)
            kept.append(tc)
    logger.info(f"Deduplication: kept {len(kept)}, removed {removed}")
    return kept, removed


# ─── MAIN ENTRY POINT ─────────────────────────────────────────────────────────

def generate_all(
    chunks: List[DocumentChunk],
    review_points: dict,
) -> Tuple[List[TestCase], int]:
    """
    Generate test cases for all document chunks.
    Returns (test_cases, duplicates_removed).
    """
    tc_counters = {"VD": 0, "IT": 0, "UT": 0}
    sc_counter = 1
    all_test_cases: List[TestCase] = []

    for chunk in chunks:
        tcs, sc_counter = generate_for_chunk(
            chunk, tc_counters, sc_counter, review_points
        )
        all_test_cases.extend(tcs)
        logger.info(
            f"Chunk {chunk.chunk_index} [{chunk.module}]: generated {len(tcs)} test cases"
        )

    if review_points.get("rp5", True):
        all_test_cases, removed = deduplicate(all_test_cases)
    else:
        removed = 0

    return all_test_cases, removed
