import os
import re
import json
import base64
import uuid
import logging
from typing import Dict, Any, Optional, Tuple, List
import httpx

from app.core.config import get_github_token, NEVER_MERGE
from app.core.security import (
    verify_safe_pull_request_action,
    redact_secrets_in_content,
    redact_secret_string,
    validate_repository_url
)
from app.models.schemas import DraftPRRequest, DraftPRResponse, RemediationProposal

logger = logging.getLogger("GitHubService")


def _sanitize_error_message(msg: str, token: Optional[str] = None) -> str:
    """Removes sensitive authorization tokens and secrets from exception messages."""
    sanitized = str(msg)
    if token and len(token) > 4:
        sanitized = sanitized.replace(token, "[REDACTED_TOKEN]")
    # Redact common token formats
    sanitized = re.sub(r"(ghp_[A-Za-z0-9]{20,40}|github_pat_[A-Za-z0-9_]{82})", "[REDACTED_TOKEN]", sanitized)
    sanitized = re.sub(r"Bearer\s+[A-Za-z0-9._\-]+", "Bearer [REDACTED_TOKEN]", sanitized)
    return sanitized


class GitHubService:
    """
    Manages GitHub interactions with ironclad safety guarantees:
    - ONLY creates DRAFT pull requests (`draft: True`).
    - NEVER merges PRs under any circumstances (`NEVER_MERGE = True`).
    - Explicit human user authorization is mandatory.
    - Accurately reports whether a PR is verified live on GitHub or dry-run simulated.
    - Never exposes authentication credentials to frontend, logs, or error responses.
    """

    @staticmethod
    def parse_github_repo_url(repo_url: str) -> Tuple[bool, str, str, str]:
        """
        Parses and validates a GitHub repository URL.
        Returns: (is_valid, owner, repo_name, error_message)
        """
        if not repo_url or not isinstance(repo_url, str):
            return False, "", "", "Repository URL cannot be empty."

        repo_url = repo_url.strip()
        if repo_url.startswith("fixture://") or repo_url.startswith("demo://"):
            return False, "local-fixture", repo_url.split("://")[-1], "Local test fixture repository"

        match = re.search(r"github\.com[/:]([^/]+)/([^/.]+)(?:\.git)?", repo_url, re.IGNORECASE)
        if not match:
            return False, "", "", f"Invalid or unsupported GitHub repository URL: '{repo_url}'"

        owner = match.group(1).strip()
        repo = match.group(2).strip()
        if not owner or not repo:
            return False, "", "", "Repository URL must specify both owner and repository name."

        return True, owner, repo, ""

    @staticmethod
    def _build_headers(token: str) -> Dict[str, str]:
        """Constructs secure, standard GitHub REST API v3 headers."""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PATCHPROOF-Security-Platform",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    @classmethod
    def create_draft_pull_request(
        cls,
        repo_url: str,
        proposal: RemediationProposal,
        request: DraftPRRequest,
        client: Optional[httpx.Client] = None
    ) -> DraftPRResponse:
        """
        Executes end-to-end Draft Pull Request generation:
        1. Validates human confirmation and prohibits all merge actions.
        2. Validates repository identifier and verifies permissions.
        3. If no token configured or local fixture: returns transparent verified simulation.
        4. When live token is available:
           a. Discovers default branch via GitHub API.
           b. Fetches remote manifest file and validates content / SHA (rejects stale/conflicted content).
           c. Rejects display-only diffs and secret-leaking patches.
           d. Applies patch to exact remote content.
           e. Creates Git Blob -> Git Tree -> Git Commit -> Unique Branch.
           f. Calls Pull Requests API with `draft: True`.
           g. Independently verifies PR on GitHub (draft status, branches, commit SHA, changed files).
        """
        # 1. Enforce Safety Checks
        verify_safe_pull_request_action("draft_pr")
        if not request.user_confirmed:
            raise PermissionError("Explicit human user authorization is required before creating a draft pull request.")

        # Prohibit merge under all circumstances
        if "merge" in request.pr_title.lower() and "never merge" not in request.pr_title.lower():
            verify_safe_pull_request_action("merge_attempt_blocked")

        # Validate Remediation Proposal Upfront: Reject Redacted / Display-Only Diff
        if "display preview only" in proposal.verification_status.lower() or "[display preview only" in proposal.reason.lower():
            raise ValueError("Remediation rejected: Proposal contains redacted secrets and is marked display preview only. It cannot be applied as a commit.")

        if proposal.proposed_version == proposal.current_version:
            raise ValueError(f"Remediation rejected: Proposed version '{proposal.proposed_version}' is identical to installed version.")

        is_valid_github, owner, repo_clean, parse_err = cls.parse_github_repo_url(repo_url)
        token = get_github_token()

        # Generate unique proposed branch name with collision-resistant suffix
        base_branch_default = request.base_branch or "main"
        clean_pkg = re.sub(r"[^a-zA-Z0-9._-]", "-", proposal.package)
        clean_ver = re.sub(r"[^a-zA-Z0-9._-]", "-", proposal.proposed_version)
        unique_suffix = uuid.uuid4().hex[:8]
        proposed_branch = request.proposed_branch or f"patchproof/security-fix-{clean_pkg}-{unique_suffix}"

        # 2. Check for simulation mode (fixture or no token)
        if not token or not is_valid_github or repo_url.startswith("fixture://"):
            sim_url = f"https://github.com/{owner or 'demo-org'}/{repo_clean or 'demo-repo'}/pull/104"
            sim_message = (
                f"[DRY RUN / SIMULATION] Draft pull request preview prepared for branch '{proposed_branch}'. "
                "No live GitHub API write was executed because "
                + ("no GITHUB_TOKEN is configured in environment." if not token else "repository is a local fixture.")
                + " Human code review is mandatory."
            )
            return DraftPRResponse(
                success=True,
                draft_status="DRAFT (DRY RUN / SIMULATION)",
                pr_url=f"{sim_url} (Dry Run Preview)",
                pr_number=104,
                branch_name=proposed_branch,
                base_branch=base_branch_default,
                head_branch=proposed_branch,
                commit_sha=f"sim-{uuid.uuid4().hex[:12]}",
                changed_files=[proposal.manifest_path],
                repo_owner=owner or "demo-org",
                repo_name=repo_clean or "demo-repo",
                title=f"[DRAFT] {request.pr_title}",
                message=sim_message,
                is_simulation=True,
                verified_on_github=False
            )

        # 3. Live GitHub Integration Workflow
        headers = cls._build_headers(token)
        close_client = False
        if client is None:
            client = httpx.Client(timeout=15.0)
            close_client = True

        try:
            # Step A: Validate Repository Access and Discover Default Branch
            repo_api_url = f"https://api.github.com/repos/{owner}/{repo_clean}"
            repo_resp = client.get(repo_api_url, headers=headers)

            if repo_resp.status_code == 401:
                raise PermissionError("GitHub authentication failed: Provided token is invalid or expired. Check GITHUB_TOKEN.")
            elif repo_resp.status_code == 404:
                raise PermissionError(f"GitHub repository '{owner}/{repo_clean}' not found or token lacks access permissions.")
            elif repo_resp.status_code == 403:
                err_text = repo_resp.text
                if "rate limit" in err_text.lower():
                    raise RuntimeError("GitHub API rate limit exceeded. Please retry later.")
                raise PermissionError(f"GitHub access forbidden: Insufficient permissions for repository '{owner}/{repo_clean}'.")
            elif repo_resp.status_code != 200:
                raise RuntimeError(f"GitHub API returned unexpected status {repo_resp.status_code} accessing repository.")

            repo_meta = repo_resp.json()
            discovered_default_branch = repo_meta.get("default_branch", "main")

            # Determine actual base branch (use user preference if explicitly non-default, else discovered default)
            actual_base_branch = request.base_branch if request.base_branch and request.base_branch != "main" else discovered_default_branch

            # Step B: Validate Remediation & Reject Redacted / Display-Only Diff
            if "display preview only" in proposal.verification_status.lower() or "[display preview only" in proposal.reason.lower():
                raise ValueError("Remediation rejected: Proposal contains redacted secrets and is marked display preview only. It cannot be applied as a commit.")

            if proposal.proposed_version == proposal.current_version:
                raise ValueError(f"Remediation rejected: Proposed version '{proposal.proposed_version}' is identical to installed version.")

            # Step C: Fetch Current Remote Manifest File and Validate Content & SHA
            manifest_norm = proposal.manifest_path.replace("\\", "/").lstrip("/")
            file_api_url = f"https://api.github.com/repos/{owner}/{repo_clean}/contents/{manifest_norm}"
            file_resp = client.get(file_api_url, params={"ref": actual_base_branch}, headers=headers)

            if file_resp.status_code == 404:
                raise FileNotFoundError(f"Manifest file '{manifest_norm}' was not found on remote branch '{actual_base_branch}'.")
            elif file_resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch manifest file '{manifest_norm}' from GitHub: {file_resp.status_code}")

            file_data = file_resp.json()
            raw_content_b64 = file_data.get("content", "")
            try:
                remote_content = base64.b64decode(raw_content_b64).decode("utf-8")
            except Exception as e:
                raise ValueError(f"Unable to decode remote manifest content: {str(e)}")

            # Check for stale content: ensure current_version is actually in the file
            if proposal.current_version not in remote_content:
                raise ValueError(
                    f"Stale content detected on GitHub {actual_base_branch}: {proposal.package} is no longer at "
                    f"version {proposal.current_version}. Pull request aborted to prevent overwrite conflict."
                )

            # Step D: Apply Patch to Exact Original File
            updated_content, replacement_count = cls._apply_version_patch(
                content=remote_content,
                manifest_path=manifest_norm,
                package=proposal.package,
                current_version=proposal.current_version,
                proposed_version=proposal.proposed_version
            )

            if replacement_count == 0 or updated_content == remote_content:
                raise ValueError(f"Patch application failed: unable to update {proposal.package} in {manifest_norm}.")

            # Safety check: Verify no secrets exist in modified content
            sanitized_check = redact_secrets_in_content(updated_content)
            if sanitized_check != updated_content:
                raise ValueError("Safety violation: Modified content contains unredacted credentials. Commit rejected.")

            # Step E: Create Real GitHub Branch and Commit using Git Data API
            branch_name, commit_sha = cls._create_git_commit_and_branch(
                owner=owner,
                repo=repo_clean,
                base_branch=actual_base_branch,
                proposed_branch=proposed_branch,
                file_path=manifest_norm,
                new_content=updated_content,
                proposal=proposal,
                client=client,
                headers=headers
            )

            # Step F: Construct Comprehensive Structured PR Body
            pr_body = cls._format_pr_body(
                owner=owner,
                repo=repo_clean,
                proposal=proposal,
                branch_name=branch_name,
                base_branch=actual_base_branch
            )

            # Step G: Call Pull Requests API with draft: True
            pr_api_url = f"https://api.github.com/repos/{owner}/{repo_clean}/pulls"
            pr_payload = {
                "title": f"Security remediation — PATCHPROOF: Upgrade {proposal.package} to {proposal.proposed_version}",
                "head": branch_name,
                "base": actual_base_branch,
                "body": pr_body,
                "draft": True  # NON-NEGOTIABLE SAFETY GUARANTEE
            }

            pr_resp = client.post(pr_api_url, json=pr_payload, headers=headers)
            if pr_resp.status_code not in (200, 201):
                err_text = _sanitize_error_message(pr_resp.text[:300], token)
                raise RuntimeError(f"GitHub Pull Request creation failed ({pr_resp.status_code}): {err_text}")

            pr_json = pr_resp.json()
            created_pr_number = pr_json.get("number")
            created_pr_url = pr_json.get("html_url")

            # Step H: Phase 7 — Independently Verify the Actual PR from GitHub
            verified_pr = cls._verify_pr_on_github(
                owner=owner,
                repo=repo_clean,
                pr_number=created_pr_number,
                expected_commit_sha=commit_sha,
                expected_branch=branch_name,
                expected_base=actual_base_branch,
                expected_file=manifest_norm,
                client=client,
                headers=headers
            )

            return DraftPRResponse(
                success=True,
                draft_status="DRAFT (VERIFIED)",
                pr_url=verified_pr["html_url"],
                pr_number=created_pr_number,
                branch_name=branch_name,
                base_branch=actual_base_branch,
                head_branch=branch_name,
                commit_sha=commit_sha,
                changed_files=verified_pr.get("files", [manifest_norm]),
                repo_owner=owner,
                repo_name=repo_clean,
                title=pr_payload["title"],
                message=(
                    f"Live GitHub DRAFT pull request #{created_pr_number} successfully created on branch '{branch_name}' "
                    f"and independently verified on GitHub. Architectural NEVER_MERGE safety guard active."
                ),
                is_simulation=False,
                verified_on_github=True
            )

        except Exception as e:
            sanitized_err = _sanitize_error_message(str(e), token)
            logger.error("Draft PR creation failed: %s", sanitized_err)
            return DraftPRResponse(
                success=False,
                draft_status="DRAFT (FAILED)",
                pr_url=None,
                pr_number=None,
                branch_name=proposed_branch,
                base_branch=base_branch_default,
                head_branch=proposed_branch,
                commit_sha=None,
                changed_files=[],
                repo_owner=owner,
                repo_name=repo_clean,
                title=f"[DRAFT] {request.pr_title}",
                message=f"Failed to create live GitHub Draft PR: {sanitized_err}",
                is_simulation=False,
                verified_on_github=False
            )
        finally:
            if close_client:
                client.close()

    @classmethod
    def _apply_version_patch(
        cls,
        content: str,
        manifest_path: str,
        package: str,
        current_version: str,
        proposed_version: str
    ) -> Tuple[str, int]:
        """Applies exact dependency version replacement based on manifest file type."""
        manifest_lower = manifest_path.lower()

        if manifest_lower.endswith("requirements.txt") or manifest_lower.endswith(".pip"):
            # Requirements.txt syntax: package==1.2.3
            pattern = rf"(?i)\b({re.escape(package)}\s*==\s*)[0-9a-zA-Z.+!_-]+"
            mod, count = re.subn(pattern, rf"\g<1>{proposed_version}", content)
            if count > 0:
                return mod, count

        elif manifest_lower.endswith("package.json"):
            # package.json syntax: "lodash": "^4.17.15"
            pattern = rf'("{re.escape(package)}"\s*:\s*)"([\^~]?)[0-9a-zA-Z.+!_-]+"'
            mod, count = re.subn(pattern, rf'\g<1>"\g<2>{proposed_version}"', content)
            if count > 0:
                return mod, count

        # Fallback exact current_version string replacement
        mod, count = re.subn(re.escape(current_version), proposed_version, content, count=1)
        return mod, count

    @classmethod
    def _create_git_commit_and_branch(
        cls,
        owner: str,
        repo: str,
        base_branch: str,
        proposed_branch: str,
        file_path: str,
        new_content: str,
        proposal: RemediationProposal,
        client: httpx.Client,
        headers: Dict[str, str]
    ) -> Tuple[str, str]:
        """
        Creates blob, tree, commit, and branch reference using the GitHub Git Data API.
        Guarantees that the default base branch is NEVER modified directly.
        """
        # Step 1: Get base branch latest commit SHA
        ref_api = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{base_branch}"
        ref_resp = client.get(ref_api, headers=headers)
        if ref_resp.status_code != 200:
            raise RuntimeError(f"Base branch '{base_branch}' not found in repository {owner}/{repo}.")
        base_commit_sha = ref_resp.json()["object"]["sha"]

        # Step 2: Get base tree SHA from base commit
        commit_api = f"https://api.github.com/repos/{owner}/{repo}/git/commits/{base_commit_sha}"
        commit_resp = client.get(commit_api, headers=headers)
        if commit_resp.status_code != 200:
            raise RuntimeError(f"Could not retrieve base commit tree for {base_commit_sha}.")
        base_tree_sha = commit_resp.json()["tree"]["sha"]

        # Step 3: Handle branch name collision safely
        final_branch = proposed_branch
        while True:
            chk_resp = client.get(f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{final_branch}", headers=headers)
            if chk_resp.status_code == 404:
                break  # Branch name is free
            final_branch = f"{proposed_branch}-{uuid.uuid4().hex[:6]}"

        # Step 4: Create Blob for the updated manifest file
        blob_api = f"https://api.github.com/repos/{owner}/{repo}/git/blobs"
        blob_resp = client.post(blob_api, json={"content": new_content, "encoding": "utf-8"}, headers=headers)
        if blob_resp.status_code not in (200, 201):
            raise RuntimeError(f"Git blob creation failed ({blob_resp.status_code}): {blob_resp.text[:200]}")
        new_blob_sha = blob_resp.json()["sha"]

        # Step 5: Create Tree preserving all unchanged files
        tree_api = f"https://api.github.com/repos/{owner}/{repo}/git/trees"
        tree_payload = {
            "base_tree": base_tree_sha,
            "tree": [
                {
                    "path": file_path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": new_blob_sha
                }
            ]
        }
        tree_resp = client.post(tree_api, json=tree_payload, headers=headers)
        if tree_resp.status_code not in (200, 201):
            raise RuntimeError(f"Git tree creation failed ({tree_resp.status_code}): {tree_resp.text[:200]}")
        new_tree_sha = tree_resp.json()["sha"]

        # Step 6: Create Commit
        commit_msg = (
            f"fix(security): upgrade {proposal.package} from {proposal.current_version} to {proposal.proposed_version}\n\n"
            f"Resolves security advisories: {', '.join(proposal.advisories_resolved)}.\n"
            f"Automated safe remediation generated by PATCHPROOF.\n"
            f"NEVER_MERGE safety active: Requires human peer review before merge."
        )
        new_commit_payload = {
            "message": commit_msg,
            "tree": new_tree_sha,
            "parents": [base_commit_sha]
        }
        new_commit_resp = client.post(f"https://api.github.com/repos/{owner}/{repo}/git/commits", json=new_commit_payload, headers=headers)
        if new_commit_resp.status_code not in (200, 201):
            raise RuntimeError(f"Git commit creation failed ({new_commit_resp.status_code}): {new_commit_resp.text[:200]}")
        new_commit_sha = new_commit_resp.json()["sha"]

        # Step 7: Create New Branch Reference (NEVER modify base branch ref!)
        create_ref_api = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
        create_ref_payload = {
            "ref": f"refs/heads/{final_branch}",
            "sha": new_commit_sha
        }
        create_ref_resp = client.post(create_ref_api, json=create_ref_payload, headers=headers)
        if create_ref_resp.status_code not in (200, 201):
            raise RuntimeError(f"Branch reference creation failed for '{final_branch}' ({create_ref_resp.status_code}): {create_ref_resp.text[:200]}")

        return final_branch, new_commit_sha

    @classmethod
    def _verify_pr_on_github(
        cls,
        owner: str,
        repo: str,
        pr_number: int,
        expected_commit_sha: str,
        expected_branch: str,
        expected_base: str,
        expected_file: str,
        client: httpx.Client,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Independently retrieves and verifies the newly created Pull Request from GitHub.
        Validates draft status, branches, commit SHA, and changed files.
        """
        verify_api = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        resp = client.get(verify_api, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"PR independent verification failed: GitHub returned {resp.status_code} for PR #{pr_number}.")

        pr_data = resp.json()

        # 1. Verify Draft Status
        if not pr_data.get("draft", False):
            raise RuntimeError(f"CRITICAL SAFETY VIOLATION: Pull request #{pr_number} was not created in DRAFT mode.")

        # 2. Verify Head and Base Branches
        head_ref = pr_data.get("head", {}).get("ref")
        base_ref = pr_data.get("base", {}).get("ref")
        if head_ref != expected_branch:
            raise RuntimeError(f"PR verification mismatch: Expected head branch '{expected_branch}', found '{head_ref}'.")
        if base_ref != expected_base:
            raise RuntimeError(f"PR verification mismatch: Expected base branch '{expected_base}', found '{base_ref}'.")

        # 3. Verify Commit SHA
        head_sha = pr_data.get("head", {}).get("sha")
        if head_sha != expected_commit_sha:
            raise RuntimeError(f"PR verification mismatch: Expected commit SHA '{expected_commit_sha}', found '{head_sha}'.")

        # 4. Verify Changed Files
        files_api = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        files_resp = client.get(files_api, headers=headers)
        changed_files = []
        if files_resp.status_code == 200:
            changed_files = [f.get("filename") for f in files_resp.json() if f.get("filename")]
            if expected_file not in changed_files:
                raise RuntimeError(f"PR verification mismatch: Expected changed file '{expected_file}' not found in PR files.")

        pr_data["files"] = changed_files
        return pr_data

    @staticmethod
    def _format_pr_body(
        owner: str,
        repo: str,
        proposal: RemediationProposal,
        branch_name: str,
        base_branch: str
    ) -> str:
        """Constructs a comprehensive, transparent Markdown Pull Request body."""
        cves_formatted = (
            "\n".join(f"- **{adv}**" for adv in proposal.advisories_resolved)
            if proposal.advisories_resolved
            else "- (Advisory resolved via dependency upgrade)"
        )
        concerns_formatted = (
            "\n".join(f"- {c}" for c in proposal.compatibility_concerns)
            if proposal.compatibility_concerns
            else "- No breaking changes or compatibility concerns identified."
        )

        return (
            f"## 🛡️ PATCHPROOF Automated Remediation (DRAFT)\n\n"
            f"**Target Repository:** `{owner}/{repo}`  \n"
            f"**Target Manifest:** `{proposal.manifest_path}`  \n"
            f"**Package Upgrade:** `{proposal.package}` (`{proposal.current_version}` → `{proposal.proposed_version}`)  \n"
            f"**Remediation Branch:** `{branch_name}` → `{base_branch}`  \n\n"
            f"### 📋 Security Advisories & CVEs Resolved\n"
            f"{cves_formatted}\n\n"
            f"### 🔍 Security Analysis & Risk Rationale\n"
            f"{proposal.reason}\n\n"
            f"### ⚠️ Compatibility & Breaking Change Assessment\n"
            f"- **Breaking Change Warning:** {'⚠️ Yes (Major Version Bump)' if proposal.breaking_change_warning else '✅ None detected (Minor/Patch Upgrade)'}\n"
            f"{concerns_formatted}\n\n"
            f"### 🧪 Recommended Verification Tests\n"
            f"```bash\n{proposal.recommended_test_command}\n```\n\n"
            f"### 👤 Human Review & Merge Instructions\n"
            f"1. Review the proposed dependency manifest diff on this branch (`{branch_name}`).\n"
            f"2. Execute the recommended test command in your local test environment or CI pipeline.\n"
            f"3. Verify that your application's test suite passes and no functional regressions occur.\n"
            f"4. Once human code review approval is obtained, you may manually merge this pull request.\n\n"
            f"---\n"
            f"> **🔒 Architectural Safety Guarantee (NEVER_MERGE Active):**\n"
            f"> PATCHPROOF creates pull requests strictly in **DRAFT** mode for human peer review. "
            f"Automated merging is permanently disabled in the backend. PATCHPROOF will never automatically merge or close this pull request."
        )

    @staticmethod
    def merge_pull_request(*args, **kwargs):
        """
        Absolute architectural safeguard:
        Attempts to call merge_pull_request are strictly denied at compile/runtime.
        """
        raise NotImplementedError(
            "CRITICAL SECURITY RESTRICTION: PATCHPROOF is strictly prohibited from merging pull requests. "
            "All remediations must be reviewed and merged manually by repository maintainers."
        )
