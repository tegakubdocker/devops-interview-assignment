"""
scoring.py — Weight aggregation and total score computation.
"""

from typing import Dict, List


# Module weights and max scores
MODULE_CONFIG = {
    "terraform": {"max_score": 25, "weight": 0.25},
    "k8s": {"max_score": 25, "weight": 0.25},
    "network": {"max_score": 20, "weight": 0.20},
    "cicd": {"max_score": 15, "weight": 0.15},
    "debug": {"max_score": 15, "weight": 0.15},
}


def compute_module_score(checks: List[Dict]) -> int:
    """Sum points from a list of check results."""
    return sum(c.get("points_awarded", 0) for c in checks)


def compute_total_score(module_results: Dict[str, List[Dict]]) -> Dict:
    """Compute total score across all modules.

    Args:
        module_results: Dict mapping module name to list of check results.
            Each check result has: name, max_points, points_awarded, passed, details

    Returns:
        Dict with total_score, max_score, band, and per-module breakdown.
    """
    modules = {}
    total_score = 0
    max_score = 0

    for module_name, config in MODULE_CONFIG.items():
        checks = module_results.get(module_name, [])
        score = compute_module_score(checks)
        module_max = config["max_score"]

        modules[module_name] = {
            "score": score,
            "max": module_max,
            "checks": checks,
        }
        total_score += score
        max_score += module_max

    band = score_to_band(total_score)

    return {
        "total_score": total_score,
        "max_score": max_score,
        "band": band,
        "modules": modules,
    }


def score_to_band(score: int) -> str:
    """Convert a numeric score to a hiring band."""
    if score >= 80:
        return "Strong Hire"
    elif score >= 65:
        return "Hire"
    elif score >= 50:
        return "Borderline"
    else:
        return "No Hire"
