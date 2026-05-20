# ─────────────────────────────────────────────
#  KEYWORD DICTIONARIES
# ─────────────────────────────────────────────

MODULE_KEYWORDS = [
    "Login", "Authentication", "Registration", "User Management",
    "Dashboard", "Search", "Filter", "Payment", "Checkout", "Cart",
    "Order", "Notification", "Email", "Report", "Export", "API",
    "Integration", "Database", "Admin", "Settings", "Profile",
    "Upload", "Download", "Security", "Performance",
]

FUNCTIONAL_VERBS = [
    "shall", "must", "should", "allow", "enable", "prevent", "validate",
    "calculate", "display", "submit", "process", "return", "create",
    "update", "delete", "search", "filter", "sort", "authenticate",
    "authorise", "authorize", "notify", "generate", "export", "import",
    "upload", "download", "verify", "confirm", "reject", "approve",
    "assign", "track", "monitor", "log", "record", "send", "receive",
]

NON_FUNCTIONAL_KEYWORDS = [
    "performance", "response time", "latency", "throughput", "availability",
    "uptime", "scalability", "security", "encryption", "compliance",
    "usability", "accessibility", "reliability", "load", "concurrent users",
    "concurrent", "sla", "milliseconds", "transactions per second",
    "requests per second", "bandwidth", "memory", "cpu", "disk",
]

BOUNDARY_TRIGGERS = [
    "maximum", "minimum", "limit", "length", "range", "between",
    "at least", "at most", "no more than", "up to", "exceed",
    "greater than", "less than", "exactly", "characters", "digits",
    "max", "min", "threshold", "capacity", "quota",
]

SECURITY_KEYWORDS = [
    "authentication", "authorisation", "authorization", "encrypt",
    "token", "password", "injection", "xss", "csrf", "privilege",
    "role", "permission", "access control", "session", "credential",
    "oauth", "jwt", "ssl", "tls", "certificate", "hash", "salt",
    "sanitize", "sanitise", "escape", "firewall", "audit",
]

PERFORMANCE_KEYWORDS = [
    "response time", "latency", "throughput", "load", "concurrent",
    "uptime", "availability", "sla", "milliseconds", "seconds",
    "transactions per second", "requests per second", "benchmark",
    "stress", "capacity", "scalab", "performance",
]

INTEGRATION_KEYWORDS = [
    "integrates", "connects", "communicates", "interacts", "calls",
    "sends to", "receives from", "synchronises", "synchronizes",
    "api", "webhook", "third-party", "external", "service",
    "middleware", "message queue", "kafka", "rabbitmq", "rest",
    "soap", "graphql", "grpc", "endpoint", "interface",
]

VALIDATION_ACTION_WORDS = [
    "display", "show", "submit", "login", "log in", "checkout",
    "register", "upload", "download", "view", "navigate", "click",
    "enter", "fill", "select", "render", "present", "page",
]

# ─────────────────────────────────────────────
#  STEP TEMPLATES
# ─────────────────────────────────────────────

STEP_TEMPLATES = {
    "normal": [
        "1. Ensure all preconditions are satisfied",
        "2. Prepare valid test data for {subject}",
        "3. Execute the action: {action}",
        "4. Observe system response",
        "5. Compare actual result with expected outcome",
    ],
    "boundary": [
        "1. Ensure all preconditions are satisfied",
        "2. Identify boundary values: minimum, maximum, min-1, max+1",
        "3. Set input to boundary value: [min / max / min-1 / max+1 / null / empty]",
        "4. Execute the action: {action}",
        "5. Record system response for each boundary value",
        "6. Verify system accepts valid limits and rejects out-of-range values",
    ],
    "edge": [
        "1. Configure system to an unusual but valid state",
        "2. Prepare edge-case input: {edge_input}",
        "3. Execute {action} under the edge condition",
        "4. Observe system behaviour (concurrent access / state transition / timeout)",
        "5. Verify system remains stable and produces correct output",
        "6. Check for data integrity and no residual state corruption",
    ],
    "robustness": [
        "1. Ensure all preconditions are satisfied",
        "2. Prepare malformed/attack input: {robustness_input}",
        "3. Submit the malformed input via: {action}",
        "4. Verify system returns appropriate error (HTTP 400 / validation error)",
        "5. Confirm no data corruption, crash, or security bypass occurred",
        "6. Review system logs for error handling evidence",
    ],
}

# ─────────────────────────────────────────────
#  INPUT TEMPLATES
# ─────────────────────────────────────────────

INPUT_TEMPLATES = {
    "normal": [
        "{subject}: valid data conforming to SRS specification",
        "Test environment: properly initialised",
        "User credentials: valid and authorised",
    ],
    "boundary": [
        "{subject}: minimum allowed value (as per SRS)",
        "{subject}: maximum allowed value (as per SRS)",
        "{subject}: minimum - 1 (below valid range)",
        "{subject}: maximum + 1 (above valid range)",
        "{subject}: null / None / undefined",
        "{subject}: empty string ''",
        "{subject}: zero (0) where numeric",
    ],
    "edge": [
        "{subject}: concurrent request with duplicate data",
        "{subject}: valid data during active session expiry/timeout",
        "{subject}: valid data with maximum simultaneous users active",
        "{subject}: rapid successive requests (within 100ms)",
        "{subject}: valid data after partial system failure/recovery",
    ],
    "robustness": [
        "{subject}: SQL injection — ' OR 1=1 --",
        "{subject}: XSS payload — <script>alert(document.cookie)</script>",
        "{subject}: extremely large value (10,000+ characters / 999999999)",
        "{subject}: special characters — !@#$%^&*()<>?/|{{}}[]",
        "{subject}: null bytes — \\x00\\x00\\x00",
        "{subject}: Unicode overflow — \\uFFFD\\uFFFE",
        "{subject}: path traversal — ../../etc/passwd",
    ],
}

# ─────────────────────────────────────────────
#  PRECONDITION TEMPLATES
# ─────────────────────────────────────────────

PRECONDITION_TEMPLATES = {
    "normal": [
        "System is initialised and running in {env} environment",
        "Test data for {module} module is prepared and available",
        "User has appropriate permissions for {module} operations",
        "Required dependent services/modules are active",
    ],
    "boundary": [
        "System is initialised and running in {env} environment",
        "Boundary values for {subject} are defined and documented in SRS",
        "Test data includes minimum, maximum, and out-of-range values",
        "Validation rules for {subject} are implemented and active",
    ],
    "edge": [
        "System is initialised and running in {env} environment",
        "System is in a valid but non-standard state for {module}",
        "Concurrent access simulation tooling is available if required",
        "Session and timeout configurations are set to test values",
    ],
    "robustness": [
        "System is initialised and running in {env} environment",
        "System logging is enabled and being actively monitored",
        "Intrusion detection/WAF is in monitoring mode (not blocking) for test",
        "Test is performed in isolated environment with no production data",
    ],
}

# ─────────────────────────────────────────────
#  EXPECTED OUTCOME TEMPLATES
# ─────────────────────────────────────────────

EXPECTED_OUTCOME_TEMPLATES = {
    "normal": (
        "System successfully {action} with valid inputs. "
        "Response is returned within acceptable time. "
        "Data is persisted/processed correctly as per SRS specification."
    ),
    "boundary": (
        "System correctly handles all boundary values: "
        "accepts inputs within valid range, rejects out-of-range inputs "
        "with a clear, user-friendly error message. No data corruption occurs."
    ),
    "edge": (
        "System remains stable and produces correct output under edge-case conditions. "
        "No data loss, state corruption, or unhandled exceptions occur. "
        "System recovers gracefully from the edge condition."
    ),
    "robustness": (
        "System rejects malformed/malicious input with HTTP 400 or appropriate error response. "
        "No data corruption, no application crash, and no security bypass occurs. "
        "Error is logged. No sensitive information is exposed in the error response."
    ),
}
