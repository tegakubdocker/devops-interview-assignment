"""
evaluate.py — CLI entry point for the DevOps interview evaluation.

Usage:
    python -m evaluation.evaluate --submission ./submission
    python -m evaluation.evaluate --submission ./submission --module terraform
    python -m evaluation.evaluate --submission ./submission --quick
    python -m evaluation.evaluate --submission ./submission --output report.json
"""

import argparse
import os
import sys
from typing import Dict, List, Optional

from .report import generate_markdown_report, write_report
from .scoring import MODULE_CONFIG, compute_total_score
from .validators import (
    document_validator,
    kubernetes_validator,
    pipeline_validator,
    python_validator,
    shell_validator,
    terraform_validator,
)

# Map module names to their validators
MODULE_VALIDATORS = {
    "terraform": [terraform_validator],
    "k8s": [kubernetes_validator],
    "network": [shell_validator],
    "cicd": [pipeline_validator, python_validator],
    "debug": [document_validator],
}

VALID_MODULES = list(MODULE_VALIDATORS.keys())


def run_module(module_name: str, submission_dir: str, quick: bool = False) -> List[Dict]:
    """Run all validators for a given module."""
    validators = MODULE_VALIDATORS.get(module_name, [])
    checks = []
    for validator in validators:
        try:
            result = validator.validate(submission_dir, quick=quick)
            checks.extend(result)
        except Exception as e:
            checks.append({
                "name": f"Validator error ({validator.__name__})",
                "max_points": 0,
                "points_awarded": 0,
                "passed": False,
                "details": str(e),
            })
    return checks


def evaluate(
    submission_dir: str,
    module: Optional[str] = None,
    quick: bool = False,
) -> Dict:
    """Run evaluation and return results.

    Args:
        submission_dir: Path to the submission/ directory.
        module: If set, only evaluate this module.
        quick: If True, only run syntax/parse checks.

    Returns:
        Dict with total_score, max_score, band, modules.
    """
    if not os.path.isdir(submission_dir):
        print(f"Error: submission directory not found: {submission_dir}", file=sys.stderr)
        sys.exit(1)

    modules_to_run = [module] if module else VALID_MODULES
    module_results = {}

    for mod in modules_to_run:
        if mod not in MODULE_VALIDATORS:
            print(f"Warning: unknown module '{mod}', skipping", file=sys.stderr)
            continue
        module_results[mod] = run_module(mod, submission_dir, quick=quick)

    # For modules not run, include empty results
    for mod in VALID_MODULES:
        if mod not in module_results:
            module_results[mod] = []

    return compute_total_score(module_results)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate DevOps interview submission",
        prog="python -m evaluation.evaluate",
    )
    parser.add_argument(
        "--submission",
        required=True,
        help="Path to the submission/ directory",
    )
    parser.add_argument(
        "--module",
        choices=VALID_MODULES,
        help="Evaluate a single module only",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Only run syntax/parse checks (fast mode)",
    )
    parser.add_argument(
        "--output",
        help="Write report to file (JSON or Markdown based on extension)",
    )

    args = parser.parse_args()

    # Resolve submission path
    submission_dir = os.path.abspath(args.submission)

    print(f"Evaluating submission: {submission_dir}")
    if args.module:
        print(f"Module: {args.module}")
    if args.quick:
        print("Mode: quick (syntax only)")
    print()

    results = evaluate(submission_dir, module=args.module, quick=args.quick)

    # Print markdown report to stdout
    report = generate_markdown_report(results)
    print(report)

    # Write to file if requested
    if args.output:
        write_report(results, args.output)
        print(f"\nReport written to: {args.output}")


if __name__ == "__main__":
    main()
