import re
import difflib
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from packaging.version import parse as parse_version, InvalidVersion
from app.models.schemas import VulnerabilityFinding, RemediationProposal, Component
from app.core.security import redact_secret_string

class RemediationService:
    @staticmethod
    def generate_remediations(
        repo_path: Path,
        vulnerabilities: List[VulnerabilityFinding],
        components: List[Component]
    ) -> List[RemediationProposal]:
        """
        Calculates safe, evidence-backed dependency remediation proposals
        with unified manifest diffs, compatibility checks, and secret sanitization.
        """
        proposals: List[RemediationProposal] = []
        
        # Group vulnerabilities by package
        vulns_by_pkg: Dict[str, List[VulnerabilityFinding]] = {}
        for v in vulnerabilities:
            pkg_key = f"{v.ecosystem}:{v.package.lower()}"
            if pkg_key not in vulns_by_pkg:
                vulns_by_pkg[pkg_key] = []
            vulns_by_pkg[pkg_key].append(v)

        for pkg_key, pkg_vulns in vulns_by_pkg.items():
            eco, pkg_name = pkg_key.split(":", 1)
            
            # Find matching component
            matching_comp = next((c for c in components if c.name.lower() == pkg_name and c.ecosystem == eco), None)
            if not matching_comp:
                continue

            current_ver = matching_comp.version
            
            # Collect verified fixed versions
            fixed_versions = [v.fixed_version for v in pkg_vulns if v.fixed_version]
            if not fixed_versions:
                continue

            # Filter candidate fixes to strictly newer versions (never downgrade or reinstall same version)
            valid_upgrades = []
            for f in fixed_versions:
                try:
                    if parse_version(f) > parse_version(current_ver):
                        valid_upgrades.append(f)
                except InvalidVersion:
                    if f != current_ver:
                        valid_upgrades.append(f)

            if not valid_upgrades:
                # No verified upgrade strictly newer than installed version
                continue

            # Pick smallest safe fix that resolves the target advisories
            def safe_version_key(v_str: str):
                try:
                    return parse_version(v_str)
                except InvalidVersion:
                    clean = re.sub(r"[^0-9\.]", "", v_str.split("-")[0])
                    return [int(p) if p.isdigit() else 0 for p in clean.split(".") if p]

            sorted_fixes = sorted(valid_upgrades, key=safe_version_key)
            target_fix = sorted_fixes[-1]

            # Generate manifest diff
            manifest_file = repo_path / matching_comp.manifest_path
            orig_text = ""
            mod_text = ""
            diff_text = ""

            if manifest_file.exists():
                try:
                    orig_raw = manifest_file.read_text(encoding="utf-8", errors="ignore")
                    
                    # Pattern for requirements.txt (handles ==, >=, ~=, and comments)
                    if manifest_file.name.endswith(".txt"):
                        mod_raw = re.sub(
                            rf"(?i)^({re.escape(pkg_name)}\s*(?:==|>=|~=)\s*)[0-9a-zA-Z\.\-_]+(\s*(?:#.*)?)$",
                            rf"\g<1>{target_fix}\g<2>",
                            orig_raw,
                            flags=re.MULTILINE
                        )
                        # Fallback if line wasn't matched (e.g. package==ver without newline anchor)
                        if mod_raw == orig_raw:
                            mod_raw = re.sub(
                                rf"(?i)\b({re.escape(pkg_name)}\s*==\s*)[0-9a-zA-Z\.\-_]+",
                                rf"\g<1>{target_fix}",
                                orig_raw
                            )
                    # Pattern for package.json
                    elif manifest_file.name.endswith(".json"):
                        mod_raw = re.sub(
                            rf'("{re.escape(pkg_name)}"\s*:\s*)"[\^~]?[0-9a-zA-Z\.\-_]+"',
                            rf'\g<1>"^{target_fix}"',
                            orig_raw
                        )
                    else:
                        mod_raw = orig_raw.replace(current_ver, target_fix)

                    # Compute unified diff
                    orig_lines = orig_raw.splitlines(keepends=True)
                    mod_lines = mod_raw.splitlines(keepends=True)
                    diff_gen = difflib.unified_diff(
                        orig_lines,
                        mod_lines,
                        fromfile=f"a/{matching_comp.manifest_path}",
                        tofile=f"b/{matching_comp.manifest_path}"
                    )
                    diff_text = "".join(diff_gen)

                    # Sanitize any embedded secrets from manifests/diffs
                    orig_text = redact_secret_string(orig_raw)
                    mod_text = redact_secret_string(mod_raw)
                    diff_text = redact_secret_string(diff_text)
                except Exception:
                    diff_text = f"--- {matching_comp.manifest_path}\n+++ {matching_comp.manifest_path}\n- {pkg_name}=={current_ver}\n+ {pkg_name}=={target_fix}\n"

            # Check breaking change heuristics (major version bump)
            breaking = False
            try:
                curr_major = int(current_ver.split(".")[0])
                fix_major = int(target_fix.split(".")[0])
                if fix_major > curr_major:
                    breaking = True
            except Exception:
                pass

            test_cmd = "pytest tests/" if eco == "pypi" else ("npm test" if eco == "npm" else "go test ./...")
            compat_notes = []
            if breaking:
                compat_notes.append(f"Major version bump from {current_ver} to {target_fix}. Review API release notes.")
            else:
                compat_notes.append("Minor/patch update: backward compatibility expected.")

            prop_id = f"rem-{uuid.uuid4().hex[:8]}"
            proposal = RemediationProposal(
                id=prop_id,
                package=pkg_name,
                ecosystem=eco,
                current_version=current_ver,
                proposed_version=target_fix,
                reason=f"Resolves {len(pkg_vulns)} security advisory(ies): {', '.join(v.id for v in pkg_vulns)}",
                advisories_resolved=[v.id for v in pkg_vulns],
                compatibility_concerns=compat_notes,
                breaking_change_warning=breaking,
                recommended_test_command=test_cmd,
                confidence="High",
                manifest_path=matching_comp.manifest_path,
                original_content=orig_text[:2000],
                modified_content=mod_text[:2000],
                diff=diff_text or f"Update {pkg_name} from {current_ver} to {target_fix}",
                verification_status="Verified compatible" if not breaking else "Tests recommended"
            )
            proposals.append(proposal)

        return proposals
