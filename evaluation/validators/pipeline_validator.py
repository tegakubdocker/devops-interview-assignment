"""
pipeline_validator.py — YAML stage/step checks for CI/CD pipeline files.
"""

import os
import re
from typing import Dict, List

import yaml


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


def _strip_yaml_comments(content: str) -> str:
    """Strip YAML comment lines from content."""
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


def _strip_md_template(content: str) -> str:
    """Strip markdown headings, HTML comments (including multi-line), and template placeholders."""
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.match(r'^\|[\s\-|]+\|$', stripped):
            continue
        if stripped == "-":
            continue
        lines.append(line)
    return "\n".join(lines)


def validate(submission_dir: str, quick: bool = False) -> List[Dict]:
    """Validate CI/CD pipeline and related files."""
    checks = []
    cicd_dir = os.path.join(submission_dir, "cicd")

    pipeline_file = os.path.join(cicd_dir, "pipeline.yaml")
    content = _read_file(pipeline_file)

    # --- Check 1: Pipeline YAML syntax (1 pt) ---
    parsed = None
    if not content.strip():
        checks.append(_check("Pipeline YAML syntax", 1, False, "pipeline.yaml is empty"))
    else:
        # Strip lines that are only comments
        non_comment = "\n".join(
            l for l in content.splitlines()
            if l.strip() and not l.strip().startswith("#")
        )
        if not non_comment.strip():
            checks.append(_check("Pipeline YAML syntax", 1, False, "pipeline.yaml has no YAML content"))
        else:
            try:
                parsed = yaml.safe_load(content)
                checks.append(_check("Pipeline YAML syntax", 1, parsed is not None))
            except yaml.YAMLError as e:
                checks.append(_check("Pipeline YAML syntax", 1, False, f"YAML error: {e}"))

    if quick:
        return checks

    # Strip comments for keyword matching (don't match skeleton instructions)
    stripped_content = _strip_yaml_comments(content)
    content_lower = stripped_content.lower()

    # --- Check 2: Build + test + deploy stages (3 pts) ---
    has_build = bool(re.search(r'build', content_lower))
    has_test = bool(re.search(r'test', content_lower))
    has_deploy = bool(re.search(r'deploy', content_lower))

    stage_score = sum([has_build, has_test, has_deploy])

    # Check ordering: build should come before test, test before deploy
    order_ok = True
    if has_build and has_test:
        build_pos = content_lower.find("build")
        test_pos = content_lower.find("test")
        if build_pos > test_pos:
            order_ok = False
    if has_test and has_deploy:
        test_pos = content_lower.find("test")
        deploy_pos = content_lower.find("deploy")
        if test_pos > deploy_pos:
            order_ok = False

    if not order_ok:
        stage_score = max(stage_score - 1, 0)

    checks.append({
        "name": "Build + test + deploy stages in order",
        "max_points": 3,
        "points_awarded": stage_score,
        "passed": stage_score >= 3,
        "details": f"build={'yes' if has_build else 'no'}, "
                   f"test={'yes' if has_test else 'no'}, "
                   f"deploy={'yes' if has_deploy else 'no'}, "
                   f"order={'correct' if order_ok else 'incorrect'}",
    })

    # --- Check 3: ECR push, staging, prod with manual gate (3 pts) ---
    ecr_score = 0
    ecr_details = []

    if any(kw in content_lower for kw in ["ecr", "docker push", "docker build", "container registry"]):
        ecr_score += 1
        ecr_details.append("ECR/container push")

    if any(kw in content_lower for kw in ["staging", "stage"]):
        ecr_score += 1
        ecr_details.append("staging deploy")

    if any(kw in content_lower for kw in [
        "manual", "approval", "approve", "environment.*protection",
        "required_reviewers", "gate", "confirm"
    ]):
        ecr_score += 1
        ecr_details.append("manual approval gate")

    checks.append({
        "name": "ECR push, staging deploy, prod manual gate",
        "max_points": 3,
        "points_awarded": ecr_score,
        "passed": ecr_score >= 2,
        "details": f"Found: {', '.join(ecr_details)}" if ecr_details else "Missing deployment stages",
    })

    # --- Check 4: Rollback / failure handling (1 pt) ---
    has_rollback = any(kw in content_lower for kw in ["rollback", "roll back", "undo", "revert", "failure", "on_failure", "if.*fail"])
    checks.append(_check("Rollback/failure handling in pipeline", 1, has_rollback))

    # --- Check 5: deploy.py (handled by python_validator) ---
    # This is validated by python_validator.py, included here for module completeness

    # --- Check 6: monitoring_setup.md (3 pts) ---
    import json as _json
    keywords_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "concept_keywords.json")
    try:
        with open(keywords_path, "r") as f:
            keywords = _json.load(f)
    except (FileNotFoundError, _json.JSONDecodeError):
        keywords = {}

    monitoring_raw = _read_file(os.path.join(cicd_dir, "monitoring_setup.md"))
    monitoring_content = _strip_md_template(monitoring_raw).lower()

    mon_score = 0
    mon_details = []

    # Metrics
    metrics_kws = keywords.get("monitoring_setup_metrics", {}).get("keywords", [])
    if sum(1 for kw in metrics_kws if re.search(kw, monitoring_content)) >= 3:
        mon_score += 1
        mon_details.append("metrics")

    # SLOs
    slo_kws = keywords.get("monitoring_setup_slo", {}).get("keywords", [])
    if sum(1 for kw in slo_kws if re.search(kw, monitoring_content)) >= 2:
        mon_score += 1
        mon_details.append("SLOs")

    # Alerting + escalation
    alert_kws = keywords.get("monitoring_setup_alerting", {}).get("keywords", [])
    esc_kws = keywords.get("monitoring_setup_escalation", {}).get("keywords", [])
    alert_matches = sum(1 for kw in alert_kws if re.search(kw, monitoring_content))
    esc_matches = sum(1 for kw in esc_kws if re.search(kw, monitoring_content))
    if alert_matches >= 2 and esc_matches >= 1:
        mon_score += 1
        mon_details.append("alerting + escalation")

    checks.append({
        "name": "monitoring_setup.md: metrics, SLOs, alerting, escalation",
        "max_points": 3,
        "points_awarded": mon_score,
        "passed": mon_score >= 2,
        "details": f"Found: {', '.join(mon_details)}" if mon_details else "Insufficient monitoring detail",
    })

    return checks
