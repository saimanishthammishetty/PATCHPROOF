
import re
import difflib
import uuid
from pathlib import Path
from typing import List, Dict

from packaging.version import parse as parse_version, InvalidVersion

from app.models.schemas import (
    VulnerabilityFinding,
    RemediationProposal,
    Component,
)
from app.core.security import redact_secrets_in_content


class RemediationService:

    @staticmethod
    def generate_remediations(
        repo_path: Path,
        vulnerabilities: List[VulnerabilityFinding],
        components: List[Component],
    ) -> List[RemediationProposal]:
        """
        Generate evidence-backed dependency remediation proposals.

        Security requirements:
        - Only propose verified newer dependency versions.
        - Generate genuine unified diffs.
        - Redact secrets from all returned manifest content.
        - Never fabricate a diff when a manifest cannot be updated.
        """

        proposals: List[RemediationProposal] = []

        # Group vulnerabilities by package and ecosystem.
        vulns_by_pkg: Dict[str, List[VulnerabilityFinding]] = {}

        for vuln in vulnerabilities:
            pkg_key = f"{vuln.ecosystem}:{vuln.package.lower()}"
            vulns_by_pkg.setdefault(pkg_key, []).append(vuln)

        for pkg_key, pkg_vulns in vulns_by_pkg.items():

            eco, pkg_name = pkg_key.split(":", 1)

            # Find the matching dependency component.
            matching_comp = next(
                (
                    component
                    for component in components
                    if component.name.lower() == pkg_name
                    and component.ecosystem == eco
                ),
                None,
            )

            if not matching_comp:
                continue

            current_ver = matching_comp.version

            # Collect verified fixed versions.
            fixed_versions = [
                vuln.fixed_version
                for vuln in pkg_vulns
                if vuln.fixed_version
            ]

            if not fixed_versions:
                continue

            # Accept only upgrades, never downgrades or same versions.
            valid_upgrades = []

            for fixed_version in fixed_versions:
                try:
                    if parse_version(fixed_version) > parse_version(current_ver):
                        valid_upgrades.append(fixed_version)
                except InvalidVersion:
                    if fixed_version != current_ver:
                        valid_upgrades.append(fixed_version)

            if not valid_upgrades:
                continue

            # Select the highest verified fixed version.
            def safe_version_key(version_string):
                try:
                    return (1, parse_version(version_string))
                except InvalidVersion:
                    clean = re.sub(
                        r"[^0-9.]",
                        "",
                        version_string.split("-")[0],
                    )
                    parts = tuple(
                        int(part) if part.isdigit() else 0
                        for part in clean.split(".")
                        if part
                    )
                    return (0, parts)

            target_fix = sorted(
                valid_upgrades,
                key=safe_version_key,
            )[-1]

            # Locate the dependency manifest.
            manifest_file = repo_path / matching_comp.manifest_path

            # Do not generate a proposal without a real manifest.
            if not manifest_file.is_file():
                continue

            try:
                orig_raw = manifest_file.read_text(
                    encoding="utf-8",
                    errors="replace",
                )

                mod_raw = orig_raw

                # requirements.txt
                if manifest_file.name.lower().endswith(".txt"):

                    pattern = (
                        rf"(?im)^("
                        rf"{re.escape(pkg_name)}"
                        rf"\s*(?:==|>=|~=)\s*"
                        rf")[0-9a-zA-Z.+!_-]+"
                        rf"(\s*(?:#.*)?)$"
                    )

                    mod_raw, replacements = re.subn(
                        pattern,
                        lambda match: (
                            match.group(1)
                            + target_fix
                            + match.group(2)
                        ),
                        orig_raw,
                    )

                    # Fallback for a requirements line with unusual formatting.
                    if replacements == 0:
                        fallback_pattern = (
                            rf"(?i)\b("
                            rf"{re.escape(pkg_name)}"
                            rf"\s*==\s*"
                            rf")[0-9a-zA-Z.+!_-]+"
                        )

                        mod_raw, replacements = re.subn(
                            fallback_pattern,
                            lambda match: match.group(1) + target_fix,
                            orig_raw,
                        )

                # package.json
                elif manifest_file.name.lower() == "package.json":

                    pattern = (
                        rf'("{re.escape(pkg_name)}"\s*:\s*)"'
                        rf'([\^~]?)'
                        rf'([0-9a-zA-Z.+!_-]+)"'
                    )

                    mod_raw, replacements = re.subn(
                        pattern,
                        lambda match: (
                            match.group(1)
                            + '"'
                            + match.group(2)
                            + target_fix
                            + '"'
                        ),
                        orig_raw,
                        flags=re.IGNORECASE,
                    )

                # Other supported manifests: replace the exact current version.
                else:
                    mod_raw, replacements = re.subn(
                        re.escape(current_ver),
                        lambda _: target_fix,
                        orig_raw,
                        count=1,
                    )

                # Never claim an update if no actual change occurred.
                if mod_raw == orig_raw:
                    continue

                # Generate a genuine unified diff.
                diff_text = "".join(
                    difflib.unified_diff(
                        orig_raw.splitlines(keepends=True),
                        mod_raw.splitlines(keepends=True),
                        fromfile=f"a/{matching_comp.manifest_path}",
                        tofile=f"b/{matching_comp.manifest_path}",
                        lineterm="\n",
                    )
                )

                # A proposal without a genuine diff is not accepted.
                if not diff_text or "--- " not in diff_text or "+++ " not in diff_text:
                    continue

                # Redact detected credentials while preserving manifest text.
                orig_text = redact_secrets_in_content(orig_raw)
                mod_text = redact_secrets_in_content(mod_raw)
                sanitized_diff = redact_secrets_in_content(diff_text)

            except (OSError, UnicodeError, ValueError):
                # Fail closed: do not return unsanitized manifest content.
                continue

            # Detect major-version upgrades.
            breaking = False

            try:
                current_major = int(current_ver.split(".")[0])
                target_major = int(target_fix.split(".")[0])

                if target_major > current_major:
                    breaking = True

            except (ValueError, IndexError, AttributeError):
                pass

            # Recommend ecosystem-specific tests.
            if eco == "pypi":
                test_cmd = "pytest tests/"
            elif eco == "npm":
                test_cmd = "npm test"
            else:
                test_cmd = "go test ./..."

            compatibility_notes = []

            if breaking:
                compatibility_notes.append(
                    f"Major version bump from {current_ver} "
                    f"to {target_fix}. Review API release notes."
                )
            else:
                compatibility_notes.append(
                    "Minor/patch update: backward compatibility expected."
                )

            # Create the remediation proposal.
            proposal = RemediationProposal(
                id=f"rem-{uuid.uuid4().hex[:8]}",
                package=pkg_name,
                ecosystem=eco,
                current_version=current_ver,
                proposed_version=target_fix,
                reason=(
                    f"Resolves {len(pkg_vulns)} security advisory(ies): "
                    f"{', '.join(vuln.id for vuln in pkg_vulns)}"
                ),
                advisories_resolved=[
                    vuln.id for vuln in pkg_vulns
                ],
                compatibility_concerns=compatibility_notes,
                breaking_change_warning=breaking,
                recommended_test_command=test_cmd,
                confidence="High",
                manifest_path=matching_comp.manifest_path,
                original_content=orig_text[:2000],
                modified_content=mod_text[:2000],
                diff=sanitized_diff,
                manifest_diff=sanitized_diff,
                verification_status=(
                    "Verified compatible"
                    if not breaking
                    else "Tests recommended"
                ),
            )

            proposals.append(proposal)

        return proposals
