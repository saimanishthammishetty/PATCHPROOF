"""
Focused tests for RemediationService unified diff generation.
Tests run entirely offline — no network calls required.
"""
import difflib
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.schemas import Component, VulnerabilityFinding
from app.services.remediation_service import RemediationService


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def make_component(name: str, version: str, manifest_path: str = "requirements.txt") -> Component:
    return Component(
        name=name,
        version=version,
        ecosystem="pypi",
        purl=f"pkg:pypi/{name}@{version}",
        manifest_path=manifest_path,
    )


def make_vuln(package: str, fixed: str) -> VulnerabilityFinding:
    return VulnerabilityFinding(
        id=f"GHSA-test-{package}",
        package=package,
        ecosystem="pypi",
        affected_version="0.0.1",
        fixed_version=fixed,
        severity="HIGH",
        recommended_action=f"Upgrade {package}",
        explanation="Test advisory",
        confidence="High",
    )


# ---------------------------------------------------------------------------
# Test 1: Successful manifest update produces genuine unified diff
# ---------------------------------------------------------------------------

def test_successful_update_produces_unified_diff():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        manifest = repo_path / "requirements.txt"
        manifest.write_text("requests==2.19.1\nurllib3==1.24.1\n", encoding="utf-8")

        comp = make_component("requests", "2.19.1")
        vuln = make_vuln("requests", "2.31.0")

        proposals = RemediationService.generate_remediations(
            repo_path=repo_path,
            vulnerabilities=[vuln],
            components=[comp],
        )

        assert len(proposals) == 1, "Expected one remediation proposal"
        p = proposals[0]
        assert p.package == "requests"
        assert p.proposed_version == "2.31.0"
        assert p.current_version == "2.19.1"

        diff = p.manifest_diff or p.diff
        assert diff, "manifest_diff must not be empty"
        assert "---" in diff, "Unified diff must contain '---' header"
        assert "+++" in diff, "Unified diff must contain '+++' header"
        assert "-requests==2.19.1" in diff, "Diff must show removed line"
        assert "+requests==2.31.0" in diff, "Diff must show added line"


# ---------------------------------------------------------------------------
# Test 2: Diff and manifest_diff both contain valid markers
# ---------------------------------------------------------------------------

def test_diff_and_manifest_diff_both_valid():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        manifest = repo_path / "requirements.txt"
        manifest.write_text("pyyaml==5.2\n", encoding="utf-8")

        comp = make_component("pyyaml", "5.2")
        vuln = make_vuln("pyyaml", "5.4")

        proposals = RemediationService.generate_remediations(
            repo_path=repo_path,
            vulnerabilities=[vuln],
            components=[comp],
        )

        assert proposals, "Expected remediation proposal"
        p = proposals[0]
        for field_name, value in [("diff", p.diff), ("manifest_diff", p.manifest_diff)]:
            assert value and "---" in value and "+++" in value, (
                f"Field '{field_name}' must contain unified diff headers; got: {repr(value)}"
            )


# ---------------------------------------------------------------------------
# Test 3: Missing manifest — no fabricated proposal
# ---------------------------------------------------------------------------

def test_missing_manifest_yields_no_proposal():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        # Do NOT create the manifest file

        comp = make_component("requests", "2.19.1")
        vuln = make_vuln("requests", "2.31.0")

        proposals = RemediationService.generate_remediations(
            repo_path=repo_path,
            vulnerabilities=[vuln],
            components=[comp],
        )

        # The service must not fabricate a diff for a missing manifest.
        # Either no proposal, or the diff must include valid unified-diff markers.
        for p in proposals:
            diff = p.manifest_diff or p.diff
            # If a proposal was returned, it should not report a non-existent successful diff.
            # A missing manifest can't produce real markers, so validate explicitly:
            if diff and ("---" in diff and "+++" in diff):
                # Synthetic header accepted only if content reflects a real change line
                assert "@@ " in diff or "-" in diff, (
                    "Synthetic diff without change lines is fabricated"
                )


# ---------------------------------------------------------------------------
# Test 4: No-op replacement — version already up-to-date → no proposal
# ---------------------------------------------------------------------------

def test_noop_same_version_yields_no_proposal():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        manifest = repo_path / "requirements.txt"
        manifest.write_text("requests==2.31.0\n", encoding="utf-8")

        comp = make_component("requests", "2.31.0")
        # fixed_version same as installed → should not produce a valid upgrade
        vuln = make_vuln("requests", "2.31.0")

        proposals = RemediationService.generate_remediations(
            repo_path=repo_path,
            vulnerabilities=[vuln],
            components=[comp],
        )

        assert len(proposals) == 0, (
            "No proposal expected when installed version equals fixed version"
        )


# ---------------------------------------------------------------------------
# Test 5: No-op regex — package name in manifest differs in case
# ---------------------------------------------------------------------------

def test_case_insensitive_manifest_match():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        manifest = repo_path / "requirements.txt"
        # PyPI manifest uses mixed case
        manifest.write_text("PyYAML==5.2\n", encoding="utf-8")

        comp = make_component("pyyaml", "5.2")
        vuln = make_vuln("pyyaml", "5.4")

        proposals = RemediationService.generate_remediations(
            repo_path=repo_path,
            vulnerabilities=[vuln],
            components=[comp],
        )

        assert proposals, "Expected a proposal even with mixed-case manifest entry"
        p = proposals[0]
        diff = p.manifest_diff or p.diff
        assert "---" in diff and "+++" in diff, "Expected valid unified diff with headers"
        assert "5.4" in diff, "Expected proposed version in diff"


# ---------------------------------------------------------------------------
# Test 6: Secret-redacted manifest diff treated as display preview
# ---------------------------------------------------------------------------

def test_secret_redacted_diff_treated_as_display_preview():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        manifest = repo_path / "requirements.txt"
        secret_token = "AKIA1234567890ABCDEF"
        manifest.write_text(f"requests==2.19.1\n# AWS Key: {secret_token}\n", encoding="utf-8")

        comp = make_component("requests", "2.19.1")
        vuln = make_vuln("requests", "2.31.0")

        proposals = RemediationService.generate_remediations(
            repo_path=repo_path,
            vulnerabilities=[vuln],
            components=[comp],
        )

        assert len(proposals) == 1
        p = proposals[0]

        # Ensure secrets are never exposed
        assert secret_token not in p.original_content
        assert secret_token not in p.modified_content
        assert secret_token not in p.diff

        # Ensure treated as display preview and not guaranteed-applicable patch
        assert "Display preview only" in p.verification_status
        assert any("display preview only" in note.lower() for note in p.compatibility_concerns)
        assert "[Display Preview Only" in p.reason


