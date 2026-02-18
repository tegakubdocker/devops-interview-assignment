"""
report.py — JSON and markdown report output.
"""

import json
from typing import Dict


def generate_json_report(results: Dict) -> str:
    """Generate a JSON report string."""
    return json.dumps(results, indent=2)


def generate_markdown_report(results: Dict) -> str:
    """Generate a human-readable markdown report."""
    lines = []
    lines.append("# Evaluation Report")
    lines.append("")

    total = results["total_score"]
    max_score = results["max_score"]
    band = results["band"]

    lines.append(f"**Total Score: {total} / {max_score}**")
    lines.append(f"**Recommendation: {band}**")
    lines.append("")

    # Score bar
    pct = int((total / max_score) * 100) if max_score > 0 else 0
    filled = pct // 5
    bar = "#" * filled + "-" * (20 - filled)
    lines.append(f"[{bar}] {pct}%")
    lines.append("")

    # Per-module breakdown
    lines.append("## Module Scores")
    lines.append("")
    lines.append("| Module | Score | Max |")
    lines.append("|--------|-------|-----|")

    for module_name, module_data in results.get("modules", {}).items():
        score = module_data["score"]
        max_pts = module_data["max"]
        lines.append(f"| {module_name} | {score} | {max_pts} |")

    lines.append("")

    # Detailed checks per module
    lines.append("## Detailed Results")
    lines.append("")

    for module_name, module_data in results.get("modules", {}).items():
        lines.append(f"### {module_name.upper()}")
        lines.append("")

        checks = module_data.get("checks", [])
        if not checks:
            lines.append("*No checks ran for this module.*")
            lines.append("")
            continue

        for check in checks:
            status = "PASS" if check.get("passed") else "FAIL"
            name = check.get("name", "Unknown")
            awarded = check.get("points_awarded", 0)
            max_pts = check.get("max_points", 0)
            details = check.get("details", "")

            lines.append(f"- [{status}] {name} ({awarded}/{max_pts} pts)")
            if details and not check.get("passed"):
                lines.append(f"  - {details}")

        lines.append("")

    return "\n".join(lines)


def write_report(results: Dict, output_path: str) -> None:
    """Write report to a file (JSON or markdown based on extension)."""
    if output_path.endswith(".json"):
        content = generate_json_report(results)
    elif output_path.endswith(".md"):
        content = generate_markdown_report(results)
    else:
        content = generate_json_report(results)

    with open(output_path, "w") as f:
        f.write(content)
