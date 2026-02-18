"""
document_validator.py — Keyword/concept matching for markdown document grading.
Used for Module 5 (debug scenario) documents.
"""

import json
import os
import re
from typing import Dict, List


def _check(name: str, max_points: int, passed: bool, details: str = "") -> Dict:
    return {
        "name": name,
        "max_points": max_points,
        "points_awarded": max_points if passed else 0,
        "passed": passed,
        "details": details,
    }


def _read_file(filepath: str) -> str:
    try:
        with open(filepath, "r") as f:
            return f.read()
    except (FileNotFoundError, IOError):
        return ""


def _strip_md_template(content: str) -> str:
    """Strip markdown headings, HTML comments (including multi-line), and template placeholders."""
    # First, remove multi-line HTML comments
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Skip table separator rows
        if re.match(r'^\|[\s\-|]+\|$', stripped):
            continue
        # Skip empty table rows
        if re.match(r'^\|\s*\|\s*\|\s*\|\s*\|$', stripped):
            continue
        # Skip lone dashes (empty list items)
        if stripped == "-":
            continue
        lines.append(line)
    return "\n".join(lines)


def _count_keyword_matches(content: str, keywords: List[str]) -> int:
    """Count how many keywords from the list match in the content."""
    content_lower = content.lower()
    return sum(1 for kw in keywords if re.search(kw, content_lower))


def validate(submission_dir: str, quick: bool = False) -> List[Dict]:
    """Validate Module 5 debug scenario documents and scripts."""
    checks = []
    debug_dir = os.path.join(submission_dir, "debug")

    # Load concept keywords
    keywords_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "concept_keywords.json")
    try:
        with open(keywords_path, "r") as f:
            keywords = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        keywords = {}

    rca_raw = _read_file(os.path.join(debug_dir, "root_cause_analysis.md"))
    rca_content = _strip_md_template(rca_raw).lower()
    remediation_content = _read_file(os.path.join(debug_dir, "remediation.sh"))
    postmortem_raw = _read_file(os.path.join(debug_dir, "postmortem.md"))
    postmortem_content = _strip_md_template(postmortem_raw).lower()
    product_raw = _read_file(os.path.join(debug_dir, "product_recommendations.md"))
    product_content = _strip_md_template(product_raw).lower()

    # --- Check 1: RCA identifies MTU as root cause (3 pts) ---
    mtu_kws = keywords.get("debug_rca_mtu", {}).get("keywords", [])
    mtu_matches = _count_keyword_matches(rca_content, mtu_kws)

    checks.append({
        "name": "RCA: identifies MTU as root cause",
        "max_points": 3,
        "points_awarded": min(mtu_matches, 3),
        "passed": mtu_matches >= 3,
        "details": f"MTU-related keywords matched: {mtu_matches}",
    })

    # --- Check 2: RCA identifies VPN tunnel + packet fragmentation (3 pts) ---
    vpn_kws = keywords.get("debug_rca_vpn", {}).get("keywords", [])
    vpn_matches = _count_keyword_matches(rca_content, vpn_kws)

    checks.append({
        "name": "RCA: identifies VPN tunnel + packet fragmentation",
        "max_points": 3,
        "points_awarded": min(vpn_matches, 3),
        "passed": vpn_matches >= 3,
        "details": f"VPN-related keywords matched: {vpn_matches}",
    })

    # --- Check 3: Correct timeline reconstruction (1 pt) ---
    timeline_kws = keywords.get("debug_timeline", {}).get("keywords", [])
    timeline_matches = _count_keyword_matches(rca_content, timeline_kws)

    checks.append(
        _check(
            "RCA: correct timeline reconstruction",
            1,
            timeline_matches >= 3,
            f"Timeline keywords matched: {timeline_matches}",
        )
    )

    if quick:
        return checks

    # --- Check 4: remediation.sh sets MTU, passes shellcheck (3 pts) ---
    # Strip shell comments for keyword matching
    rem_stripped = "\n".join(
        l for l in remediation_content.splitlines()
        if l.strip() and not l.strip().startswith("#")
    )
    rem_lower = rem_stripped.lower()
    rem_score = 0
    rem_details = []

    # Only score if there's actual code beyond shebang
    has_code = len([l for l in rem_stripped.splitlines() if l.strip()]) >= 3

    # Check for MTU setting
    if has_code and re.search(r'mtu', rem_lower) and re.search(r'(1500|ip link|ifconfig|netplan)', rem_lower):
        rem_score += 1
        rem_details.append("sets MTU")

    # Check for shebang and error handling (in raw content)
    if has_code and remediation_content.strip().startswith("#!/") and "set -e" in remediation_content:
        rem_score += 1
        rem_details.append("shebang + error handling")

    # Check for verification step (in code, not comments)
    if has_code and any(kw in rem_lower for kw in ["verify", "check", "test", "ip link show", "ping"]):
        rem_score += 1
        rem_details.append("verification step")

    # Run shellcheck if available
    if rem_score > 0:
        import subprocess
        try:
            result = subprocess.run(
                ["shellcheck", "-S", "warning", os.path.join(debug_dir, "remediation.sh")],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                rem_score = max(rem_score - 1, 0)
                rem_details.append("shellcheck warnings")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # shellcheck not available, skip

    checks.append({
        "name": "remediation.sh: sets MTU, passes shellcheck",
        "max_points": 3,
        "points_awarded": rem_score,
        "passed": rem_score >= 2,
        "details": f"Found: {', '.join(rem_details)}" if rem_details else "Script not implemented",
    })

    # --- Check 5: postmortem.md sections + action items (2 pts) ---
    pm_kws = keywords.get("postmortem_sections", {}).get("keywords", [])
    pm_matches = _count_keyword_matches(postmortem_content, pm_kws)

    # Check for action items specifically (in raw content since headings are relevant here,
    # but require substantial content beyond the template)
    has_action_items = bool(re.search(r'action.item', postmortem_raw.lower())) and len(postmortem_content.strip()) > 200

    pm_score = 0
    if pm_matches >= 4:
        pm_score += 1
    if has_action_items:
        pm_score += 1

    checks.append({
        "name": "postmortem.md: all sections, action items",
        "max_points": 2,
        "points_awarded": pm_score,
        "passed": pm_score >= 1,
        "details": f"Sections matched: {pm_matches}, action items: {'yes' if has_action_items else 'no'}",
    })

    # --- Check 6: product_recommendations.md (3 pts) ---
    mon_kws = keywords.get("monitoring_recommendations", {}).get("keywords", [])
    mon_matches = _count_keyword_matches(product_content, mon_kws)

    prod_score = min(mon_matches, 3)

    checks.append({
        "name": "product_recommendations.md: monitoring + automated detection",
        "max_points": 3,
        "points_awarded": prod_score,
        "passed": prod_score >= 2,
        "details": f"Monitoring/detection keywords matched: {mon_matches}",
    })

    return checks
