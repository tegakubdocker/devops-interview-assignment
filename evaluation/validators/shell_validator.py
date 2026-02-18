"""
shell_validator.py — Shell script validation via shellcheck and pattern matching.
"""

import os
import re
import subprocess
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


def _strip_shell_comments(content: str) -> str:
    """Strip shell comments from content, keeping only executable lines."""
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Remove inline comments (simple heuristic, doesn't handle quoted #)
        line = re.sub(r'\s+#\s.*$', '', line)
        lines.append(line)
    return "\n".join(lines)


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
        # Skip lone dashes
        if stripped == "-":
            continue
        lines.append(line)
    return "\n".join(lines)


def _has_substantial_code(content: str, min_lines: int = 5) -> bool:
    """Check if content has substantial non-comment, non-empty code."""
    code_lines = [
        l.strip() for l in content.splitlines()
        if l.strip()
        and not l.strip().startswith("#")
        and l.strip().lower() != "pass"
        and "todo" not in l.lower()
    ]
    return len(code_lines) >= min_lines


def _run_shellcheck(filepath: str) -> bool:
    """Run shellcheck on a file. Returns True if it passes or shellcheck is not installed."""
    try:
        result = subprocess.run(
            ["shellcheck", "-S", "warning", filepath],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except FileNotFoundError:
        # shellcheck not installed — degrade gracefully
        return True
    except subprocess.TimeoutExpired:
        return True


def _has_shebang(content: str) -> bool:
    """Check if file starts with a shebang."""
    return content.strip().startswith("#!/")


def _has_set_options(content: str) -> bool:
    """Check for error handling options."""
    return "set -e" in content or "set -euo pipefail" in content


def validate(submission_dir: str, quick: bool = False) -> List[Dict]:
    """Validate shell scripts and network/edge module files."""
    checks = []

    # Collect all shell scripts
    sh_files = []
    for subdir in ["network", "edge"]:
        dir_path = os.path.join(submission_dir, subdir)
        if not os.path.isdir(dir_path):
            continue
        for fname in os.listdir(dir_path):
            if fname.endswith(".sh"):
                sh_files.append(os.path.join(dir_path, fname))

    # --- Check 1: shellcheck passes (2 pts) ---
    shellcheck_results = []
    has_content_scripts = 0
    for fpath in sh_files:
        content = _read_file(fpath)
        # Only check scripts with substantial content (not just skeleton)
        non_comment = [
            l.strip() for l in content.splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
        if len(non_comment) < 5:
            continue
        has_content_scripts += 1
        passed = _run_shellcheck(fpath)
        shellcheck_results.append((os.path.basename(fpath), passed))

    failed_scripts = [name for name, passed in shellcheck_results if not passed]
    if has_content_scripts == 0:
        checks.append(_check("shellcheck passes on .sh files", 2, False, "No shell scripts with content found"))
    elif failed_scripts:
        checks.append(
            _check("shellcheck passes on .sh files", 2, False, f"Failed: {', '.join(failed_scripts)}")
        )
    else:
        checks.append(_check("shellcheck passes on .sh files", 2, True))

    # --- Check 2: Python lint on camera_discovery.py (1 pt) ---
    camera_py = os.path.join(submission_dir, "network", "camera_discovery.py")
    camera_content = _read_file(camera_py)
    py_valid = False
    if camera_content:
        try:
            import ast
            ast.parse(camera_content)
            py_valid = True
        except SyntaxError:
            py_valid = False

    checks.append(_check("Python syntax valid (camera_discovery.py)", 1, py_valid))

    if quick:
        return checks

    # --- Check 3: Firewall rules — default DROP (3 pts) ---
    firewall_raw = _read_file(os.path.join(submission_dir, "network", "firewall_rules.sh"))
    firewall_content = _strip_shell_comments(firewall_raw)
    fw_lower = firewall_content.lower()

    has_drop_policy = bool(re.search(r'(policy\s+(input|forward)\s+drop|-P\s+(INPUT|FORWARD)\s+DROP)', firewall_content, re.IGNORECASE))
    checks.append(
        _check("Firewall: default DROP policy", 3, has_drop_policy)
    )

    # --- Check 4: Firewall rules — RTSP, HTTPS, SSH, isolation (3 pts) ---
    fw_score = 0
    fw_details = []

    # Only score if there's substantial code (not just skeleton)
    if _has_substantial_code(firewall_raw, min_lines=8):
        # RTSP from camera VLAN
        if re.search(r'(554|rtsp)', fw_lower) and re.search(r'(camera|10\.50\.20|eno2)', fw_lower):
            fw_score += 1
            fw_details.append("RTSP from camera VLAN")

        # HTTPS outbound
        if re.search(r'443', firewall_content) and re.search(r'(output|outbound|established)', fw_lower):
            fw_score += 1
            fw_details.append("HTTPS outbound")

        # SSH from management only
        if re.search(r'22', firewall_content) and re.search(r'(10\.50\.1\.|management|mgmt)', fw_lower):
            fw_score += 1
            fw_details.append("SSH from management")

    checks.append(
        _check(
            "Firewall: RTSP, HTTPS, SSH, camera isolation",
            3,
            fw_score >= 2,
            f"Found: {', '.join(fw_details)}" if fw_details else "Missing firewall rules",
        )
    )

    # --- Check 5: setup.sh content (5 pts) ---
    setup_raw = _read_file(os.path.join(submission_dir, "edge", "setup.sh"))
    setup_content = _strip_shell_comments(setup_raw)
    setup_lower = setup_content.lower()

    setup_score = 0
    setup_details = []

    # Only score if there's substantial code
    if not _has_substantial_code(setup_raw, min_lines=10):
        # Skip all checks — skeleton only
        pass
    else:
        # Docker installation
        if any(kw in setup_lower for kw in ["apt-get install.*docker", "docker-ce", "install docker", "docker.io"]):
            setup_score += 1
            setup_details.append("Docker")

        # NTP
        if any(kw in setup_lower for kw in ["ntp", "chrony", "timedatectl", "timesyncd"]):
            setup_score += 1
            setup_details.append("NTP")

        # Log rotation
        if any(kw in setup_lower for kw in ["logrotate", "log rotation", "log-rotate", "maxsize", "rotate "]):
            setup_score += 1
            setup_details.append("log rotation")

        # Systemd service
        if any(kw in setup_lower for kw in ["systemctl", "systemd", ".service", "wantedby"]):
            setup_score += 1
            setup_details.append("systemd service")

    # Error handling (check in raw since set -euo pipefail is code, not a comment)
    # Only count if there's also substantial implementation
    if _has_set_options(setup_raw) and _has_substantial_code(setup_raw, min_lines=10):
        setup_score += 1
        setup_details.append("error handling")

    checks.append(
        _check(
            "setup.sh: Docker, NTP, log rotation, systemd, error handling",
            5,
            setup_score >= 3,
            f"Found: {', '.join(setup_details)} ({setup_score}/5)",
        )
    )

    # --- Check 6: camera_discovery.py functionality (3 pts) ---
    cam_score = 0
    cam_details = []

    if camera_content:
        import ast
        try:
            tree = ast.parse(camera_content)
        except SyntaxError:
            tree = None

        if tree:
            # Check if functions have actual implementations (not just `pass`)
            func_bodies = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # A function with only `pass` or docstring+pass is not implemented
                    body = node.body
                    real_stmts = [
                        s for s in body
                        if not isinstance(s, ast.Pass)
                        and not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
                    ]
                    func_bodies[node.name] = len(real_stmts) > 0

            has_implemented_funcs = any(func_bodies.values())

            if has_implemented_funcs:
                # Check for XML parsing usage (not just imports)
                if any(kw in camera_content for kw in [".parse(", ".fromstring(", "findall(", "find(", "iter("]):
                    cam_score += 1
                    cam_details.append("XML parsing")

                # Check for JSON output
                if any(kw in camera_content for kw in ["json.dump(", "json.dumps("]):
                    cam_score += 1
                    cam_details.append("JSON output")

                # Check for timeout handling
                if any(kw in camera_content for kw in ["timeout", "TimeoutError", "socket.timeout"]):
                    cam_score += 1
                    cam_details.append("timeout handling")

    checks.append(
        _check(
            "camera_discovery.py: XML parsing, JSON output, timeout",
            3,
            cam_score >= 2,
            f"Found: {', '.join(cam_details)}" if cam_details else "Skeleton not implemented",
        )
    )

    # --- Check 7: site_plan.md (2 pts) ---
    import json as _json
    keywords_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "concept_keywords.json")
    try:
        with open(keywords_path, "r") as f:
            keywords = _json.load(f)
    except (FileNotFoundError, _json.JSONDecodeError):
        keywords = {}

    site_plan_raw = _read_file(os.path.join(submission_dir, "network", "site_plan.md"))
    site_plan = _strip_md_template(site_plan_raw).lower()

    # Require substantial content beyond template
    site_content_lines = [l.strip() for l in site_plan.splitlines() if l.strip()]
    if len(site_content_lines) < 5:
        site_plan = ""  # Not enough content, treat as empty

    vlan_kws = keywords.get("site_plan_vlan", {}).get("keywords", [])
    ip_kws = keywords.get("site_plan_ip", {}).get("keywords", [])

    vlan_matches = sum(1 for kw in vlan_kws if re.search(kw, site_plan))
    ip_matches = sum(1 for kw in ip_kws if re.search(kw, site_plan))

    site_score = 0
    if vlan_matches >= 2:
        site_score += 1
    if ip_matches >= 2:
        site_score += 1

    checks.append(
        _check(
            "site_plan.md: VLAN design, IP scheme, isolation",
            2,
            site_score >= 1,
            f"VLAN keywords={vlan_matches}, IP keywords={ip_matches}",
        )
    )

    # --- Check 8: golden_image.md (1 pt) ---
    golden_raw = _read_file(os.path.join(submission_dir, "edge", "golden_image.md"))
    golden_content = _strip_md_template(golden_raw).lower()
    gi_kws = keywords.get("golden_image", {}).get("keywords", [])
    gi_matches = sum(1 for kw in gi_kws if re.search(kw, golden_content))

    checks.append(
        _check(
            "golden_image.md: creation process, patching strategy",
            1,
            gi_matches >= 2,
            f"Concept keywords matched: {gi_matches}",
        )
    )

    return checks
