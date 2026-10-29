import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from app.models.schemas import Component, DependencyHealthFinding

# Popular reference packages for typosquatting checks
POPULAR_PACKAGES = {
    "pypi": [
        "requests", "urllib3", "pyyaml", "numpy", "pandas", "django", "flask",
        "scipy", "pytest", "cryptography", "boto3", "wheel", "setuptools", "colorama"
    ],
    "npm": [
        "lodash", "react", "express", "axios", "chalk", "commander", "moment",
        "debug", "async", "next", "webpack", "vue", "typescript"
    ]
}

def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
        
    return prev_row[-1]

class DependencyHealthService:
    @staticmethod
    def analyze_health(repo_path: Path, components: List[Component]) -> List[DependencyHealthFinding]:
        findings: List[DependencyHealthFinding] = []
        
        # Check suspicious lifecycle scripts in package.json
        suspicious_scripts: Dict[str, str] = {}
        for pkg_json in repo_path.glob("**/package.json"):
            if "node_modules" in pkg_json.parts:
                continue
            try:
                import json
                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
                scripts = data.get("scripts", {})
                for s_name in ("preinstall", "install", "postinstall"):
                    cmd = scripts.get(s_name, "")
                    if cmd and any(bad in cmd.lower() for bad in ("curl", "wget", "powershell", "nc ", "bash -i", "eval(")):
                        suspicious_scripts[s_name] = cmd
            except Exception:
                pass

        for comp in components:
            pkg_name = comp.name.lower()
            eco = comp.ecosystem
            is_suspicious = False
            suspicious_reasons = []
            health_score = 9.0
            signals: Dict[str, Any] = {
                "direct_dependency": comp.direct,
                "version_format": comp.version,
                "license": comp.license
            }

            # 1. Typosquatting detection
            popular_list = POPULAR_PACKAGES.get(eco, [])
            for canonical in popular_list:
                if pkg_name != canonical:
                    dist = levenshtein_distance(pkg_name, canonical)
                    # 1 or 2 edits on a famous name
                    if dist <= 2 and abs(len(pkg_name) - len(canonical)) <= 2:
                        is_suspicious = True
                        suspicious_reasons.append(
                            f"Potential typosquatting candidate: '{pkg_name}' is suspiciously close to famous package '{canonical}' (edit distance: {dist})."
                        )
                        health_score -= 4.0
                        signals["typosquat_candidate"] = canonical

            # 2. Suspicious script detection
            if suspicious_scripts and comp.direct:
                for s_name, cmd in suspicious_scripts.items():
                    suspicious_reasons.append(
                        f"Manifest contains high-risk '{s_name}' script executing external commands: {cmd[:60]}"
                    )
                    is_suspicious = True
                    health_score -= 3.0

            # 3. OpenSSF scorecard heuristic emulation
            # (Checks if version is prehistoric or 0.0.0, or unpinned)
            if comp.version in ("0.0.0", "unknown"):
                health_score -= 2.0
                signals["unresolved_version"] = True
                
            if comp.license in ("Unknown", "NOASSERTION", None):
                health_score -= 0.5
                signals["missing_declared_license"] = True

            health_score = max(1.0, min(10.0, round(health_score, 1)))
            maintenance_status = "active" if health_score >= 6.0 else "needs_review"

            # Create finding if health is degraded or suspicious
            if is_suspicious or health_score < 7.5 or comp.vulnerability_count > 0:
                findings.append(DependencyHealthFinding(
                    package=comp.name,
                    ecosystem=comp.ecosystem,
                    health_score=health_score,
                    is_suspicious=is_suspicious,
                    suspicious_reasons=suspicious_reasons,
                    signals=signals,
                    maintenance_status=maintenance_status
                ))

        return findings

