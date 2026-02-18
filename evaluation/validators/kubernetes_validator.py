"""
kubernetes_validator.py — YAML parsing and manifest checks for Kubernetes files.
"""

import os
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


def _load_yaml(filepath: str):
    """Load a YAML file, return parsed content or None on error."""
    try:
        with open(filepath, "r") as f:
            content = f.read()
        # Skip files that are only comments
        stripped = "\n".join(
            l for l in content.splitlines()
            if l.strip() and not l.strip().startswith("#")
        )
        if not stripped.strip():
            return None
        docs = list(yaml.safe_load_all(content))
        return [d for d in docs if d is not None]
    except yaml.YAMLError:
        return None
    except (FileNotFoundError, IOError):
        return None


def _read_file(filepath: str) -> str:
    try:
        with open(filepath, "r") as f:
            return f.read()
    except (FileNotFoundError, IOError):
        return ""


def _find_container_spec(doc: Dict) -> List[Dict]:
    """Extract container specs from a Kubernetes resource."""
    containers = []
    try:
        spec = doc.get("spec", {})
        # Deployment / DaemonSet / StatefulSet
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
        containers.extend(pod_spec.get("containers", []))
        # Bare pod
        containers.extend(spec.get("containers", []))
    except (AttributeError, TypeError):
        pass
    return containers


def validate(submission_dir: str, quick: bool = False) -> List[Dict]:
    """Validate Kubernetes submission files."""
    k8s_dir = os.path.join(submission_dir, "k8s")
    checks = []

    if not os.path.isdir(k8s_dir):
        checks.append(_check("K8s directory exists", 3, False, "submission/k8s/ not found"))
        return checks

    # Parse all YAML files
    yaml_files = {}
    parse_errors = []
    for fname in os.listdir(k8s_dir):
        if fname.endswith((".yaml", ".yml")):
            fpath = os.path.join(k8s_dir, fname)
            docs = _load_yaml(fpath)
            if docs is None:
                # Check if file has non-comment content
                content = _read_file(fpath)
                has_content = any(
                    l.strip() and not l.strip().startswith("#")
                    for l in content.splitlines()
                )
                if has_content:
                    parse_errors.append(fname)
                # Empty/skeleton files are OK, just skip
            else:
                yaml_files[fname] = docs

    # --- Check 1: YAML validation (3 pts) ---
    if parse_errors:
        checks.append(_check("YAML parsing", 3, False, f"Parse errors in: {', '.join(parse_errors)}"))
    else:
        has_content = len(yaml_files) > 0
        checks.append(_check("YAML parsing", 3, has_content, "" if has_content else "No YAML content found"))

    if quick:
        return checks

    # Collect all documents across files
    all_docs = []
    for docs in yaml_files.values():
        all_docs.extend(docs)

    # Find the deployment doc
    deployment = None
    for doc in all_docs:
        if isinstance(doc, dict) and doc.get("kind") == "Deployment":
            deployment = doc
            break

    # --- Check 2: Resource requests + limits (1 pt) ---
    has_resources = False
    for doc in all_docs:
        for container in _find_container_spec(doc):
            res = container.get("resources", {})
            if res.get("requests") and res.get("limits"):
                has_resources = True
                break

    checks.append(_check("Resource requests and limits", 1, has_resources))

    # --- Check 3: Liveness + readiness probes (1 pt) ---
    has_liveness = False
    has_readiness = False
    for doc in all_docs:
        for container in _find_container_spec(doc):
            if container.get("livenessProbe"):
                has_liveness = True
            if container.get("readinessProbe"):
                has_readiness = True

    checks.append(_check("Liveness and readiness probes", 1, has_liveness and has_readiness))

    # --- Check 4: HPA with min/max/metrics (1 pt) ---
    has_hpa = False
    for doc in all_docs:
        if isinstance(doc, dict) and doc.get("kind") == "HorizontalPodAutoscaler":
            spec = doc.get("spec", {})
            if spec.get("minReplicas") and spec.get("maxReplicas"):
                has_hpa = True

    checks.append(_check("HPA with min/max replicas", 1, has_hpa))

    # --- Check 5: Anti-affinity or topology spread (1 pt) ---
    has_anti_affinity = False
    for doc in all_docs:
        try:
            pod_spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            affinity = pod_spec.get("affinity", {})
            if affinity.get("podAntiAffinity"):
                has_anti_affinity = True
            if pod_spec.get("topologySpreadConstraints"):
                has_anti_affinity = True
        except (AttributeError, TypeError):
            pass

    checks.append(_check("Anti-affinity or topology spread", 1, has_anti_affinity))

    # --- Check 6: NetworkPolicy restricts ingress (1 pt) ---
    has_netpol = False
    for doc in all_docs:
        if isinstance(doc, dict) and doc.get("kind") == "NetworkPolicy":
            spec = doc.get("spec", {})
            if "Ingress" in spec.get("policyTypes", []):
                has_netpol = True

    checks.append(_check("NetworkPolicy restricts ingress", 1, has_netpol))

    # --- Check 7: Security context (2 pts) ---
    has_non_root = False
    has_read_only_fs = False
    for doc in all_docs:
        try:
            pod_spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            # Pod-level security context
            pod_sc = pod_spec.get("securityContext", {})
            if pod_sc.get("runAsNonRoot") is True:
                has_non_root = True

            for container in pod_spec.get("containers", []):
                sc = container.get("securityContext", {})
                if sc.get("runAsNonRoot") is True:
                    has_non_root = True
                if sc.get("readOnlyRootFilesystem") is True:
                    has_read_only_fs = True
        except (AttributeError, TypeError):
            pass

    sec_score = 0
    if has_non_root:
        sec_score += 1
    if has_read_only_fs:
        sec_score += 1

    checks.append(
        _check(
            "Security context (non-root, read-only fs)",
            2,
            sec_score >= 2,
            f"non-root={'yes' if has_non_root else 'no'}, "
            f"readOnlyRootFs={'yes' if has_read_only_fs else 'no'}",
        )
    )

    # --- Check 8: Image tag not :latest (1 pt) ---
    has_latest = False
    has_any_image = False
    for doc in all_docs:
        for container in _find_container_spec(doc):
            image = container.get("image", "")
            if image:
                has_any_image = True
                if image.endswith(":latest") or ":" not in image:
                    has_latest = True

    checks.append(
        _check(
            "Image tag not :latest",
            1,
            has_any_image and not has_latest,
            "Image uses :latest or has no tag" if has_latest else "",
        )
    )

    # --- Check 9: ConfigMap referenced from deployment (1 pt) ---
    has_configmap = False
    has_configmap_ref = False
    for doc in all_docs:
        if isinstance(doc, dict) and doc.get("kind") == "ConfigMap":
            has_configmap = True

    for doc in all_docs:
        if not isinstance(doc, dict):
            continue
        try:
            pod_spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            for container in pod_spec.get("containers", []):
                # Check envFrom
                for env_from in container.get("envFrom", []):
                    if env_from.get("configMapRef"):
                        has_configmap_ref = True
                # Check env valueFrom
                for env_var in container.get("env", []):
                    vf = env_var.get("valueFrom", {})
                    if vf and vf.get("configMapKeyRef"):
                        has_configmap_ref = True
            # Check volumes
            for vol in pod_spec.get("volumes", []):
                if vol.get("configMap"):
                    has_configmap_ref = True
        except (AttributeError, TypeError):
            pass

    checks.append(
        _check(
            "ConfigMap referenced from deployment",
            1,
            has_configmap and has_configmap_ref,
            f"configmap={'yes' if has_configmap else 'no'}, "
            f"referenced={'yes' if has_configmap_ref else 'no'}",
        )
    )

    # --- Incident Responses (4 + 4 + 4 + 1 = 13 pts) ---
    import json
    keywords_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "concept_keywords.json")
    try:
        with open(keywords_path, "r") as f:
            keywords = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        keywords = {}

    incident_dir = os.path.join(k8s_dir, "incident_responses")

    for scenario_num, key_root_cause, key_remed, max_pts in [
        (1, "incident_1", "incident_1", 4),
        (2, "incident_2", "incident_2", 4),
        (3, "incident_3", "incident_3", 4),
    ]:
        fpath = os.path.join(incident_dir, f"scenario_{scenario_num}.md")
        content = _read_file(fpath).lower()

        if not content or len(content.strip()) < 100:
            checks.append(
                _check(
                    f"Incident {scenario_num}: root cause + remediation",
                    max_pts,
                    False,
                    "Response is empty or too short",
                )
            )
            continue

        kw_data = keywords.get(key_root_cause, {})
        rc_keywords = kw_data.get("root_cause", [])
        rem_keywords = kw_data.get("remediation", [])

        import re

        rc_matches = sum(1 for kw in rc_keywords if re.search(kw, content))
        rem_matches = sum(1 for kw in rem_keywords if re.search(kw, content))

        # Need at least 2 root cause keywords and 1 remediation keyword
        passed = rc_matches >= 2 and rem_matches >= 1
        score = 0
        if rc_matches >= 2:
            score += 2
        elif rc_matches >= 1:
            score += 1
        if rem_matches >= 1:
            score += min(rem_matches, 2)

        score = min(score, max_pts)

        checks.append({
            "name": f"Incident {scenario_num}: root cause + remediation",
            "max_points": max_pts,
            "points_awarded": score,
            "passed": passed,
            "details": f"root_cause_keywords={rc_matches}, remediation_keywords={rem_matches}",
        })

    # --- Prevention measures (1 pt) ---
    prevention_count = 0
    for scenario_num in [1, 2, 3]:
        fpath = os.path.join(incident_dir, f"scenario_{scenario_num}.md")
        content = _read_file(fpath).lower()
        kw_data = keywords.get(f"incident_{scenario_num}", {})
        prev_keywords = kw_data.get("prevention", [])
        import re
        if any(re.search(kw, content) for kw in prev_keywords):
            prevention_count += 1

    checks.append(
        _check("Prevention measures in incident responses", 1, prevention_count >= 2)
    )

    return checks
