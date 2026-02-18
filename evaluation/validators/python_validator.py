"""
python_validator.py — AST parsing and function checks for Python files.
"""

import ast
import os
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


def _get_function_names(tree: ast.Module) -> List[str]:
    """Extract top-level function names from an AST."""
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]


def _has_argparse(tree: ast.Module) -> bool:
    """Check if the AST uses argparse."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "argparse":
                return True
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "ArgumentParser":
                return True
    return False


def _has_subparsers(content: str) -> bool:
    """Check if the code uses argparse subparsers."""
    return "add_subparsers" in content or "subcommand" in content.lower()


def validate(submission_dir: str, quick: bool = False) -> List[Dict]:
    """Validate Python files in the CI/CD module."""
    checks = []

    deploy_py = os.path.join(submission_dir, "cicd", "deploy.py")
    content = _read_file(deploy_py)

    if not content:
        checks.append(_check("deploy.py exists", 4, False, "File not found or empty"))
        return checks

    # --- Check: Valid Python with argparse, rollback, healthcheck (4 pts) ---
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        checks.append(_check("deploy.py: valid Python syntax", 4, False, f"SyntaxError: {e}"))
        return checks

    if quick:
        checks.append(_check("deploy.py: valid Python syntax", 1, True))
        return checks

    func_names = _get_function_names(tree)
    has_argparse_usage = _has_argparse(tree)

    # Check which functions have actual implementations (not just `pass` or docstring+pass)
    implemented_funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body = node.body
            real_stmts = [
                s for s in body
                if not isinstance(s, ast.Pass)
                and not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
            ]
            if len(real_stmts) > 0:
                implemented_funcs.add(node.name)

    score = 0
    details = []

    # Valid Python (1 pt)
    score += 1
    details.append("valid syntax")

    # argparse with subcommands (1 pt) — must have actual argument definitions
    if has_argparse_usage and ("add_argument" in content or "add_subparsers" in content):
        score += 1
        details.append("argparse")
        if _has_subparsers(content):
            details.append("subcommands")

    # Rollback function (1 pt) — must be implemented, not just a stub
    rollback_funcs = [fn for fn in implemented_funcs if "rollback" in fn.lower()]
    if rollback_funcs:
        score += 1
        details.append("rollback function")

    # Health check function (1 pt) — must be implemented, not just a stub
    health_funcs = [fn for fn in implemented_funcs if "health" in fn.lower()]
    if health_funcs:
        score += 1
        details.append("healthcheck function")

    checks.append({
        "name": "deploy.py: valid Python, argparse, rollback, healthcheck",
        "max_points": 4,
        "points_awarded": score,
        "passed": score >= 3,
        "details": f"Found: {', '.join(details)}",
    })

    return checks
