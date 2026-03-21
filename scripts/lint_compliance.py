#!/usr/bin/env python3
"""Compliance lint: checks frontend and pipeline output for prohibited patterns.

This script enforces rules from legal-compliance.md, frontend-spec.md, and
display-philosophy.md mechanically. It is not a substitute for human review,
but it catches the highest-risk class of drift: advisory language, directional
color coding, and prohibited framing that could create legal exposure.

Run via: make compliance-lint
Or directly: python scripts/lint_compliance.py

Exit code 0 = clean, 1 = violations found.

Antifragile design: adding a new prohibited pattern is one line in a list.
Adding a new directory to scan is one line in SCAN_PATHS. The cost of the
next rule is less than the previous one.
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ─── Scan targets ──────────────────────────────────────────────────────
# Each entry: (glob pattern, base directory relative to project root)
SCAN_PATHS: list[tuple[str, str]] = [
    ("**/*.tsx", "frontend"),
    ("**/*.ts", "frontend"),
    ("**/*.py", "pipeline/render"),
    ("**/*.py", "pipeline/export"),
    ("**/*.py", "api"),
]

# ─── Prohibited patterns ──────────────────────────────────────────────
# Each entry: (compiled regex, human-readable rule, source rule file)
# Patterns are case-insensitive. They match against file content line by line.
#
# IMPORTANT: when adding patterns, test against the codebase first to avoid
# false positives. Comments and string literals are not excluded — if a
# prohibited string appears in a comment, it should either be removed or
# the pattern should be refined.

_ADVISORY_LANGUAGE: list[tuple[str, str]] = [
    # Positioning violations (legal-compliance.md § Positioning)
    (r"\bleaderboard\b", "Prohibited term 'leaderboard' — use 'sort and filter'"),
    (r"\branking(?:s)?\b", "Prohibited term 'ranking(s)' — use 'sorted by'"),
    (r"\btop\s+\d+\b", "Prohibited 'top N' framing"),
    (r"\bbottom\s+\d+\b", "Prohibited 'bottom N' framing"),
    (r"\bbest\s+hospital", "Prohibited 'best hospital' framing"),
    (r"\bworst\s+hospital", "Prohibited 'worst hospital' framing"),
    (r"\bbest\s+nursing", "Prohibited 'best nursing home' framing"),
    (r"\bworst\s+nursing", "Prohibited 'worst nursing home' framing"),
    (r"\bhelps?\s+you\s+choose\b", "Prohibited advisory language 'helps you choose'"),
    (r"\bfind\s+the\s+right\b", "Prohibited advisory language 'find the right'"),
    (r"\byour\s+guide\b", "Prohibited advisory language 'your guide'"),
    (r"\bmaking\s+better\s+(?:healthcare|medical)\b", "Prohibited advisory framing"),
    (r"\beverything\s+you\s+need\s+to\s+know\b", "Prohibited completeness claim"),

    # Personalized advisory (legal-compliance.md § Prohibited Language)
    (r"\bbased\s+on\s+your\s+needs\b", "Prohibited personalization"),
    (r"\bfor\s+your\s+situation\b", "Prohibited personalization"),
    (r"\bgiven\s+your\s+history\b", "Prohibited personalization"),
    (r"\byou\s+should\b", "Prohibited directive 'you should'"),
    (r"\byour\s+risk\b", "Prohibited personalization 'your risk'"),
    (r"\bwhat\s+could\s+go\s+wrong\b", "Prohibited predictive framing"),
    (r"\bpatients\s+can\s+expect\b", "Prohibited predictive language"),
    (r"\byou\s+are\s+likely\b", "Prohibited predictive language"),
    (r"\blikelihood\s+of\s+complications\b", "Prohibited predictive language"),
    (r"\bpredicted\s+outcomes?\b", "Prohibited predictive language"),

    # Clinical directives (legal-compliance.md § Prohibited Language)
    (r"\bpatients\s+should\b", "Prohibited clinical directive"),
    (r"\bseek\s+care\b", "Prohibited clinical directive"),
    (r"\bshould\s+consider\b", "Prohibited clinical directive"),
    (r"\brecommend\b", "Prohibited clinical directive (use only in comments about what NOT to do)"),
]

_DIRECTIONAL_COLOR: list[tuple[str, str]] = [
    # Directional color coding (DEC-009, frontend-spec.md, legal-compliance.md)
    # These patterns target Tailwind classes that encode better/worse judgments.
    # orange-700/orange-50 is permitted ONLY for tail risk thresholds and repeat
    # deficiencies — those files are excluded below in ALLOWED_COLOR_FILES.
    (r"\btext-red-\d+\b", "Prohibited red color — no directional color coding (DEC-009)"),
    (r"\btext-green-\d+\b", "Prohibited green color — no directional color coding (DEC-009)"),
    (r"\bbg-red-\d+\b", "Prohibited red background — no directional color coding (DEC-009)"),
    (r"\bbg-green-\d+\b", "Prohibited green background — no directional color coding (DEC-009)"),
    (r"\bborder-red-\d+\b", "Prohibited red border — no directional color coding (DEC-009)"),
    (r"\bborder-green-\d+\b", "Prohibited green border — no directional color coding (DEC-009)"),
    (r"\btext-blue-\d+\b", "Blue color in measure display — verify not encoding better/worse (DEC-009)"),
]

# Files where orange color IS permitted (tail risk threshold, repeat deficiency)
ALLOWED_COLOR_FILES: set[str] = {
    "DeficiencyCitation.tsx",
    "RepeatDeficiency.tsx",
    "SFFBadge.tsx",
    "AbuseIconBadge.tsx",
    "StaffingThreshold.tsx",
    # Add component filenames here as they are created
}

# Files where blue color is permitted (non-measure UI elements)
ALLOWED_BLUE_FILES: set[str] = {
    "DisclaimerBanner.tsx",
    "SESDisclosureBlock.tsx",
    # Tailwind config, layout, nav — add as needed
}


def compile_patterns(
    raw: list[tuple[str, str]],
) -> list[tuple[re.Pattern[str], str]]:
    """Compile regex patterns with case-insensitive flag."""
    return [(re.compile(p, re.IGNORECASE), msg) for p, msg in raw]


ADVISORY_PATTERNS = compile_patterns(_ADVISORY_LANGUAGE)
COLOR_PATTERNS = compile_patterns(_DIRECTIONAL_COLOR)


def scan_file(
    filepath: Path,
    patterns: list[tuple[re.Pattern[str], str]],
) -> list[tuple[int, str, str]]:
    """Scan a single file for pattern violations.

    Lines containing '// compliance-ok' or '# compliance-ok' are skipped.
    Use this sparingly — only for comments that document prohibitions
    (e.g., "Do not use 'your risk'").

    Returns list of (line_number, matched_text, rule_message).
    """
    violations: list[tuple[int, str, str]] = []
    try:
        text = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return violations

    for line_num, line in enumerate(text.splitlines(), start=1):
        if "compliance-ok" in line:
            continue
        for pattern, message in patterns:
            match = pattern.search(line)
            if match:
                violations.append((line_num, match.group(), message))
    return violations


def main() -> int:
    """Run compliance lint across all scan targets.

    Returns 0 if clean, 1 if violations found.
    """
    total_violations = 0
    files_scanned = 0

    for glob_pattern, base_dir in SCAN_PATHS:
        scan_root = PROJECT_ROOT / base_dir
        if not scan_root.exists():
            continue

        for filepath in scan_root.glob(glob_pattern):
            files_scanned += 1
            rel_path = filepath.relative_to(PROJECT_ROOT)
            filename = filepath.name

            # Advisory language: check all files
            advisory_hits = scan_file(filepath, ADVISORY_PATTERNS)

            # Color coding: check all files, but skip allowed files for
            # orange (threshold signals) and blue (non-measure UI)
            if filename in ALLOWED_COLOR_FILES:
                color_hits = []
            elif filename in ALLOWED_BLUE_FILES:
                # Skip blue patterns only; still check red/green
                non_blue = [
                    (p, m) for p, m in COLOR_PATTERNS
                    if "blue" not in m.lower()
                ]
                color_hits = scan_file(filepath, non_blue)
            else:
                color_hits = scan_file(filepath, COLOR_PATTERNS)

            all_hits = advisory_hits + color_hits
            if all_hits:
                for line_num, matched, message in all_hits:
                    print(f"  {rel_path}:{line_num}: '{matched}' — {message}")
                total_violations += len(all_hits)

    print(f"\n{'-' * 60}")
    print(f"Files scanned: {files_scanned}")
    print(f"Violations found: {total_violations}")

    if total_violations > 0:
        print("\nCompliance lint FAILED. Fix violations before committing.")
        return 1

    print("\nCompliance lint passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
