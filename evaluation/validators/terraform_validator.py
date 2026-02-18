"""
terraform_validator.py — HCL parsing and resource checks for Terraform files.
"""

import os
import re
from typing import Dict, List

try:
    import hcl2
    import json as _json

    HCL2_AVAILABLE = True
except ImportError:
    HCL2_AVAILABLE = False


def _check(name: str, max_points: int, passed: bool, details: str = "") -> Dict:
    return {
        "name": name,
        "max_points": max_points,
        "points_awarded": max_points if passed else 0,
        "passed": passed,
        "details": details,
    }


def _parse_hcl_file(filepath: str) -> Dict:
    """Parse an HCL file and return the parsed dict, or None on error."""
    if not HCL2_AVAILABLE:
        return None
    try:
        with open(filepath, "r") as f:
            return hcl2.load(f)
    except Exception:
        return None


def _read_file(filepath: str) -> str:
    """Read file contents, return empty string if not found."""
    try:
        with open(filepath, "r") as f:
            return f.read()
    except (FileNotFoundError, IOError):
        return ""


def _strip_tf_comments(content: str) -> str:
    """Strip HCL/Terraform comments (# and //) from content."""
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        # Remove inline comments
        line = re.sub(r'\s*#(?!.*").*$', '', line)
        lines.append(line)
    return "\n".join(lines)


def validate(submission_dir: str, quick: bool = False) -> List[Dict]:
    """Validate Terraform submission files.

    Args:
        submission_dir: Path to the submission/ directory.
        quick: If True, only run syntax checks.

    Returns:
        List of check results.
    """
    tf_dir = os.path.join(submission_dir, "terraform")
    checks = []

    if not os.path.isdir(tf_dir):
        checks.append(_check("Terraform directory exists", 5, False, "submission/terraform/ not found"))
        return checks

    # Collect all .tf files
    tf_files = {}
    for fname in os.listdir(tf_dir):
        if fname.endswith(".tf"):
            fpath = os.path.join(tf_dir, fname)
            tf_files[fname] = fpath

    # --- Check 1: HCL files parse without errors (5 pts) ---
    if not HCL2_AVAILABLE:
        checks.append(
            _check(
                "HCL parsing (python-hcl2)",
                5,
                False,
                "python-hcl2 not installed — install with: pip install python-hcl2",
            )
        )
        all_parsed = {}
    else:
        parse_errors = []
        all_parsed = {}
        for fname, fpath in tf_files.items():
            parsed = _parse_hcl_file(fpath)
            if parsed is None:
                parse_errors.append(fname)
            else:
                all_parsed[fname] = parsed

        if parse_errors:
            checks.append(
                _check(
                    "HCL parsing",
                    5,
                    False,
                    f"Parse errors in: {', '.join(parse_errors)}",
                )
            )
        else:
            checks.append(_check("HCL parsing", 5, len(tf_files) > 0, "No .tf files found" if not tf_files else ""))

    # --- Check 2: No syntax errors / plan structure (5 pts) ---
    # Check that key files exist and have content beyond skeleton
    key_files = ["main.tf", "networking.tf", "variables.tf"]
    files_with_content = 0
    for kf in key_files:
        content = _read_file(os.path.join(tf_dir, kf))
        # Check if file has content beyond comments and TODOs
        lines = [
            l.strip()
            for l in content.splitlines()
            if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("//")
        ]
        if len(lines) > 3:
            files_with_content += 1

    has_resource_blocks = False
    for parsed in all_parsed.values():
        if "resource" in parsed:
            has_resource_blocks = True
            break

    plan_ok = files_with_content >= 2 and has_resource_blocks
    checks.append(
        _check(
            "Plan structure (resource blocks exist)",
            5,
            plan_ok,
            "Missing resource blocks in Terraform files" if not plan_ok else "",
        )
    )

    if quick:
        return checks

    # --- Check 3: VPC with public + private subnets, NAT gateway (4 pts) ---
    all_content = ""
    for fpath in tf_files.values():
        all_content += _read_file(fpath) + "\n"
    content_lower = all_content.lower()

    has_vpc = "aws_vpc" in all_content
    has_public_subnet = "public" in content_lower and "aws_subnet" in all_content
    has_private_subnet = "private" in content_lower and "aws_subnet" in all_content
    has_nat = "aws_nat_gateway" in all_content
    has_igw = "aws_internet_gateway" in all_content

    vpc_score = 0
    if has_vpc:
        vpc_score += 1
    if has_public_subnet and has_private_subnet:
        vpc_score += 1
    if has_nat:
        vpc_score += 1
    if has_igw:
        vpc_score += 1

    checks.append(
        _check(
            "VPC: public + private subnets, NAT gateway",
            4,
            vpc_score >= 3,
            f"VPC components found: {vpc_score}/4 (VPC, subnets, NAT, IGW)",
        )
    )

    # --- Check 4: Security groups — no 0.0.0.0/0 on SSH (2 pts) ---
    networking_content = _read_file(os.path.join(tf_dir, "networking.tf"))

    # Look for SSH (port 22) with 0.0.0.0/0
    # Simple heuristic: find ingress blocks with port 22 and check for 0.0.0.0/0
    ssh_open = False
    # Check all .tf file contents
    for fpath in tf_files.values():
        content = _read_file(fpath)
        # Find security group ingress blocks that reference port 22
        # and also contain 0.0.0.0/0
        ingress_blocks = re.findall(
            r'ingress\s*\{[^}]*(?:from_port\s*=\s*22|to_port\s*=\s*22)[^}]*\}',
            content,
            re.DOTALL,
        )
        for block in ingress_blocks:
            if "0.0.0.0/0" in block:
                ssh_open = True
                break

    checks.append(
        _check(
            "Security groups: no 0.0.0.0/0 on SSH",
            2,
            not ssh_open,
            "SSH (port 22) is open to 0.0.0.0/0 — restrict to management CIDR" if ssh_open else "",
        )
    )

    # --- Check 5: EKS cluster with IAM, node group config (2 pts) ---
    has_eks_cluster = "aws_eks_cluster" in all_content
    has_eks_node_group = "aws_eks_node_group" in all_content
    has_iam_role = "aws_iam_role" in all_content

    eks_score = 0
    if has_eks_cluster:
        eks_score += 1
    if has_eks_node_group and has_iam_role:
        eks_score += 1

    checks.append(
        _check(
            "EKS: cluster, IAM roles, node groups",
            2,
            eks_score >= 2,
            f"EKS components: cluster={'yes' if has_eks_cluster else 'no'}, "
            f"node_group={'yes' if has_eks_node_group else 'no'}, "
            f"iam={'yes' if has_iam_role else 'no'}",
        )
    )

    # --- Check 6: Cost optimization (4 pts) ---
    cost_file = os.path.join(tf_dir, "cost_optimization.tf")
    cost_content_raw = _read_file(cost_file)
    cost_content = _strip_tf_comments(cost_content_raw)
    cost_lower = cost_content.lower()

    cost_score = 0
    cost_details = []

    # Spot/mixed instances (look in HCL code, not comments)
    if any(kw in cost_lower for kw in ["spot", "mixed_instances", "mixed instance", "on_demand_percentage"]):
        cost_score += 1
        cost_details.append("spot/mixed instances")

    # S3 lifecycle
    if any(kw in cost_lower for kw in ["lifecycle", "transition", "glacier", "infrequent_access", "intelligent_tiering"]):
        cost_score += 1
        cost_details.append("S3 lifecycle")

    # Rightsizing / instance changes
    if any(kw in cost_lower for kw in ["rightsize", "right-size", "smaller instance", "instance_type", "graviton"]):
        cost_score += 1
        cost_details.append("rightsizing")

    # Cost analysis comments (beyond skeleton TODOs — need substantial analysis)
    cost_comment_lines = [
        l for l in cost_content_raw.splitlines()
        if l.strip().startswith("#") and len(l.strip()) > 10
        and not any(marker in l.lower() for marker in [
            "todo", "hint:", "task:", "requirements:", "implement", "---",
            "your cost analysis", "such as:", "address the findings",
        ])
    ]
    if len(cost_comment_lines) >= 5:
        cost_score += 1
        cost_details.append("cost analysis comments")

    checks.append(
        _check(
            "Cost optimization: spot, lifecycle, rightsizing",
            4,
            cost_score >= 2,
            f"Found: {', '.join(cost_details)}" if cost_details else "No cost optimization measures found",
        )
    )

    # --- Check 7: Cost analysis response (3 pts) ---
    # Check if the cost_optimization.tf has meaningful analysis in comments.
    # Filter out skeleton instructional text aggressively.
    analysis_comments = [
        l for l in cost_content_raw.splitlines()
        if l.strip().startswith("#") and len(l.strip()) > 10
        and not any(marker in l.lower() for marker in [
            "todo", "hint:", "task:", "requirements:", "implement", "---",
            "your cost analysis", "such as:", "address the findings",
            "analyze", "propose", "explain", "describe", "consider",
            "lifecycle policies", "spot/mixed", "right-siz", "cost-sav",
            "cost_optimization.tf", "cost report",
        ])
    ]
    analysis_text = "\n".join(analysis_comments).lower()
    analysis_score = 0

    # Only score if candidate added substantial NEW analysis
    if len(analysis_comments) >= 5:
        if any(kw in analysis_text for kw in ["monthly cost", "total cost", "saving", "reduce", "current spend"]):
            analysis_score += 1
        if any(kw in analysis_text for kw in ["$", "usd", "percent", "%", "estimated"]):
            analysis_score += 1
        if any(kw in analysis_text for kw in ["trade-off", "tradeoff", "risk", "consideration", "impact"]):
            analysis_score += 1

    checks.append(
        _check(
            "Cost analysis: report review and savings proposals",
            3,
            analysis_score >= 2,
            f"Cost analysis depth: {analysis_score}/3",
        )
    )

    return checks
