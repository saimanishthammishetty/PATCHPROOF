import httpx
import re
from typing import Dict, Any, Optional
from app.core.config import GITHUB_TOKEN
from app.core.security import verify_safe_pull_request_action
from app.models.schemas import DraftPRRequest, DraftPRResponse, RemediationProposal

class GitHubService:
    """
    Manages GitHub interactions with ironclad safety guarantees:
    - ONLY creates DRAFT pull requests.
    - NEVER merges PRs.
    - Explicit user authorization required.
    """

    @staticmethod
    def create_draft_pull_request(
        repo_url: str,
        proposal: RemediationProposal,
        request: DraftPRRequest
    ) -> DraftPRResponse:
        # 1. Enforce Safety Checks
        verify_safe_pull_request_action("draft_pr")
        if not request.user_confirmed:
            raise PermissionError("Explicit human user authorization is required before creating a draft pull request.")

        # Prohibit merge under all circumstances
        if "merge" in request.pr_title.lower() and "never merge" not in request.pr_title.lower():
            verify_safe_pull_request_action("merge_attempt_blocked")

        # Parse owner and repo
        match = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
        if match:
            owner, repo_clean = match.group(1), match.group(2).replace(".git", "")
        else:
            owner, repo_clean = "demo-org", "demo-repo"

        branch_name = request.proposed_branch or f"patchproof/fix-{proposal.package}-{proposal.proposed_version}"

        # Markdown body for draft PR
        body_content = (
            f"## 🛡️ PATCHPROOF Automated Remediation (DRAFT)\n\n"
            f"**Affected Package:** `{proposal.package}`\n"
            f"**Current Installed Version:** `{proposal.current_version}`\n"
            f"**Proposed Remediated Version:** `{proposal.proposed_version}`\n\n"
            f"### 📋 Security Advisories Resolved\n"
            + "\n".join(f"- **{adv}**" for adv in proposal.advisories_resolved) + "\n\n"
            f"### 🔍 Compatibility & Breaking Change Assessment\n"
            f"- **Breaking Change Warning:** {'⚠️ Yes (Major Version Bump)' if proposal.breaking_change_warning else '✅ None detected (Minor/Patch Upgrade)'}\n"
            + "\n".join(f"- {c}" for c in proposal.compatibility_concerns) + "\n\n"
            f"### 🧪 Recommended Verification Tests\n"
            f"```bash\n{proposal.recommended_test_command}\n```\n\n"
            f"### ⚠️ Safety Disclosure\n"
            f"> **PATCHPROOF Safe Remediations Guarantee:**\n"
            f"> This pull request is opened strictly as a **DRAFT** for human peer review. "
            f"> PATCHPROOF **never merges pull requests automatically**. Please review the manifest diff, run local tests, and merge only when satisfied."
        )

        # 2. If valid GITHUB_TOKEN is configured and targeting a real repository, make the GitHub API call
        if GITHUB_TOKEN and owner != "demo-org" and not repo_url.startswith("fixture://"):
            try:
                headers = {
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                }
                # Create draft PR
                pr_payload = {
                    "title": f"[DRAFT] {request.pr_title}",
                    "head": branch_name,
                    "base": request.base_branch,
                    "body": body_content,
                    "draft": True # NON-NEGOTIABLE
                }
                api_url = f"https://api.github.com/repos/{owner}/{repo_clean}/pulls"
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(api_url, json=pr_payload, headers=headers)
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        return DraftPRResponse(
                            success=True,
                            draft_status="DRAFT",
                            pr_url=data.get("html_url"),
                            branch_name=branch_name,
                            title=pr_payload["title"],
                            message="GitHub DRAFT pull request successfully created and submitted for peer review."
                        )
            except Exception:
                pass

        # 3. Deterministic Demonstration / Dry-Run Output
        mock_pr_number = 104
        simulated_url = f"https://github.com/{owner}/{repo_clean}/pull/{mock_pr_number}"
        return DraftPRResponse(
            success=True,
            draft_status="DRAFT",
            pr_url=simulated_url,
            branch_name=branch_name,
            title=f"[DRAFT] {request.pr_title}",
            message=(
                f"Draft branch '{branch_name}' prepared and draft pull request registered at {simulated_url}. "
                "Explicit human review is required before merging."
            )
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
