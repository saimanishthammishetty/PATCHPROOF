import json
import base64
import pytest
import httpx
from unittest.mock import MagicMock

from app.services.github_service import GitHubService, _sanitize_error_message
from app.models.schemas import DraftPRRequest, RemediationProposal, DraftPRResponse


@pytest.fixture
def sample_proposal():
    return RemediationProposal(
        id="rem-sample-1",
        package="requests",
        ecosystem="pypi",
        current_version="2.19.1",
        proposed_version="2.20.0",
        reason="Resolves CVE-2018-18074 credential leakage vulnerability.",
        advisories_resolved=["CVE-2018-18074", "GHSA-79v4-hx79-jx7p"],
        compatibility_concerns=["Minor version bump: backward compatible."],
        breaking_change_warning=False,
        recommended_test_command="pytest tests/",
        confidence="High",
        manifest_path="requirements.txt",
        original_content="requests==2.19.1\nurllib3==1.24.1\n",
        modified_content="requests==2.20.0\nurllib3==1.24.1\n",
        diff="--- a/requirements.txt\n+++ b/requirements.txt\n@@ -1,2 +1,2 @@\n-requests==2.19.1\n+requests==2.20.0\n",
        verification_status="Verified compatible"
    )


@pytest.fixture
def sample_request():
    return DraftPRRequest(
        analysis_id="scan-test-1",
        remediation_id="rem-sample-1",
        base_branch="main",
        proposed_branch="patchproof/fix-requests-2.20.0",
        pr_title="Security remediation: Upgrade requests to 2.20.0",
        pr_body="Automated PR",
        user_confirmed=True
    )


# 1. Unconfirmed request must be rejected
def test_draft_pr_unconfirmed_rejected(sample_proposal):
    unconfirmed = DraftPRRequest(
        analysis_id="scan-test-1",
        remediation_id="rem-sample-1",
        base_branch="main",
        pr_title="Fix requests",
        user_confirmed=False
    )
    with pytest.raises(PermissionError) as exc_info:
        GitHubService.create_draft_pull_request(
            repo_url="https://github.com/acme-org/secure-app",
            proposal=sample_proposal,
            request=unconfirmed
        )
    assert "Explicit human user authorization is required" in str(exc_info.value)


# 2. Never merge prohibition preserved
def test_never_merge_prohibition_preserved():
    with pytest.raises(NotImplementedError) as exc_info:
        GitHubService.merge_pull_request(repo="acme/repo", pr_number=10)
    assert "strictly prohibited from merging pull requests" in str(exc_info.value)


# 3. Transparent dry-run when no token is present
def test_dry_run_simulation_mode_without_token(sample_proposal, sample_request, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("PATCHPROOF_GITHUB_TOKEN", "")

    resp = GitHubService.create_draft_pull_request(
        repo_url="https://github.com/acme-org/secure-app",
        proposal=sample_proposal,
        request=sample_request
    )
    assert resp.success is True
    assert resp.is_simulation is True
    assert "SIMULATION" in resp.draft_status or "DRY RUN" in resp.draft_status
    assert "No live GitHub API write was executed" in resp.message
    assert resp.verified_on_github is False


# 4. Token sanitization ensures no credential leak in error messages
def test_token_sanitization():
    token = "ghp_superSecretToken1234567890abcdef"
    msg = f"Failed to connect using Bearer {token} to https://api.github.com"
    clean = _sanitize_error_message(msg, token)
    assert token not in clean
    assert "[REDACTED_TOKEN]" in clean


# 5. Authentication failure (401 Unauthorized)
def test_auth_failure_invalid_token(sample_proposal, sample_request, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_invalidToken1234567890")

    def mock_handler(request: httpx.Request):
        return httpx.Response(401, json={"message": "Bad credentials"})

    transport = httpx.MockTransport(mock_handler)
    with httpx.Client(transport=transport) as client:
        resp = GitHubService.create_draft_pull_request(
            repo_url="https://github.com/acme-org/secure-app",
            proposal=sample_proposal,
            request=sample_request,
            client=client
        )
        assert resp.success is False
        assert resp.draft_status == "DRAFT (FAILED)"
        assert "authentication failed" in resp.message.lower()
        assert "ghp_invalidToken" not in resp.message


# 6. Repository not found or access forbidden (404 / 403)
def test_repo_access_forbidden(sample_proposal, sample_request, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_validToken1234567890")

    def mock_handler(request: httpx.Request):
        if request.url.path == "/repos/acme-org/secure-app":
            return httpx.Response(403, json={"message": "Resource not accessible by personal access token"})
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    with httpx.Client(transport=transport) as client:
        resp = GitHubService.create_draft_pull_request(
            repo_url="https://github.com/acme-org/secure-app",
            proposal=sample_proposal,
            request=sample_request,
            client=client
        )
        assert resp.success is False
        assert "insufficient permissions" in resp.message.lower() or "forbidden" in resp.message.lower()


# 7. Stale content rejection: remote file no longer contains installed version
def test_stale_remote_content_rejection(sample_proposal, sample_request, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_validToken1234567890")

    # Remote content has requests==2.25.0 already!
    remote_file = base64.b64encode(b"requests==2.25.0\nurllib3==1.24.1\n").decode("utf-8")

    def mock_handler(request: httpx.Request):
        path = request.url.path
        if path == "/repos/acme-org/secure-app":
            return httpx.Response(200, json={"default_branch": "main"})
        if path == "/repos/acme-org/secure-app/contents/requirements.txt":
            return httpx.Response(200, json={"content": remote_file, "sha": "file_sha_123"})
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    with httpx.Client(transport=transport) as client:
        resp = GitHubService.create_draft_pull_request(
            repo_url="https://github.com/acme-org/secure-app",
            proposal=sample_proposal,
            request=sample_request,
            client=client
        )
        assert resp.success is False
        assert "stale content detected" in resp.message.lower()


# 8. Rejection of display-only remediation proposals
def test_display_only_proposal_rejected(sample_request, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_validToken1234567890")
    display_proposal = RemediationProposal(
        id="rem-disp-1",
        package="requests",
        ecosystem="pypi",
        current_version="2.19.1",
        proposed_version="2.20.0",
        reason="[Display Preview Only - Redacted Secrets]",
        advisories_resolved=["CVE-2018-18074"],
        recommended_test_command="pytest",
        confidence="High",
        manifest_path="requirements.txt",
        original_content="requests==2.19.1",
        modified_content="requests==2.20.0",
        diff="--- a\n+++ b",
        verification_status="Display preview only (contains redacted secrets)"
    )

    with pytest.raises(ValueError) as exc_info:
        GitHubService.create_draft_pull_request(
            repo_url="https://github.com/acme-org/secure-app",
            proposal=display_proposal,
            request=sample_request
        )
    assert "redacted secrets" in str(exc_info.value).lower() or "display preview only" in str(exc_info.value).lower()


# 9. Complete End-to-End Git Data API & Draft PR Flow with Independent Verification
def test_complete_git_data_api_and_draft_pr_flow(sample_proposal, sample_request, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_mockValidTokenForTesting123456")

    remote_file_content = "requests==2.19.1\nurllib3==1.24.1\n"
    remote_b64 = base64.b64encode(remote_file_content.encode("utf-8")).decode("utf-8")

    captured_calls = []

    def mock_handler(request: httpx.Request):
        method = request.method
        path = request.url.path
        body = json.loads(request.content) if request.content else {}
        captured_calls.append((method, path, body))

        # Repo metadata
        if method == "GET" and path == "/repos/acme-org/secure-app":
            return httpx.Response(200, json={"default_branch": "develop"})

        # Fetch remote file
        if method == "GET" and path == "/repos/acme-org/secure-app/contents/requirements.txt":
            return httpx.Response(200, json={"content": remote_b64, "sha": "orig_file_blob_sha"})

        # Git ref base branch
        if method == "GET" and path == "/repos/acme-org/secure-app/git/ref/heads/develop":
            return httpx.Response(200, json={"object": {"sha": "base_commit_sha_111"}})

        # Base commit tree
        if method == "GET" and path == "/repos/acme-org/secure-app/git/commits/base_commit_sha_111":
            return httpx.Response(200, json={"tree": {"sha": "base_tree_sha_222"}})

        # Branch collision check (returns 404 = available)
        if method == "GET" and "/git/ref/heads/patchproof/" in path:
            return httpx.Response(404, json={"message": "Not Found"})

        # Create Blob
        if method == "POST" and path == "/repos/acme-org/secure-app/git/blobs":
            assert "requests==2.20.0" in body["content"]
            return httpx.Response(201, json={"sha": "new_blob_sha_333"})

        # Create Tree
        if method == "POST" and path == "/repos/acme-org/secure-app/git/trees":
            assert body["base_tree"] == "base_tree_sha_222"
            assert body["tree"][0]["path"] == "requirements.txt"
            assert body["tree"][0]["sha"] == "new_blob_sha_333"
            return httpx.Response(201, json={"sha": "new_tree_sha_444"})

        # Create Commit
        if method == "POST" and path == "/repos/acme-org/secure-app/git/commits":
            assert body["tree"] == "new_tree_sha_444"
            assert body["parents"] == ["base_commit_sha_111"]
            return httpx.Response(201, json={"sha": "new_commit_sha_555"})

        # Create Branch Ref
        if method == "POST" and path == "/repos/acme-org/secure-app/git/refs":
            assert body["sha"] == "new_commit_sha_555"
            assert body["ref"].startswith("refs/heads/patchproof/fix-requests-2.20.0")
            return httpx.Response(201, json={"ref": body["ref"], "object": {"sha": "new_commit_sha_555"}})

        # Create Pull Request
        if method == "POST" and path == "/repos/acme-org/secure-app/pulls":
            assert body["draft"] is True  # Non-negotiable safety invariant
            assert body["base"] == "develop"  # Discovered default branch used
            return httpx.Response(201, json={
                "number": 88,
                "html_url": "https://github.com/acme-org/secure-app/pull/88",
                "draft": True
            })

        # Independent PR Verification
        if method == "GET" and path == "/repos/acme-org/secure-app/pulls/88":
            return httpx.Response(200, json={
                "number": 88,
                "html_url": "https://github.com/acme-org/secure-app/pull/88",
                "draft": True,
                "head": {"ref": "patchproof/fix-requests-2.20.0", "sha": "new_commit_sha_555"},
                "base": {"ref": "develop", "repo": {"owner": {"login": "acme-org"}, "name": "secure-app"}}
            })

        # Verify PR Files
        if method == "GET" and path == "/repos/acme-org/secure-app/pulls/88/files":
            return httpx.Response(200, json=[{"filename": "requirements.txt"}])

        return httpx.Response(404, json={"message": f"Unhandled route {method} {path}"})

    transport = httpx.MockTransport(mock_handler)
    with httpx.Client(transport=transport) as client:
        req = DraftPRRequest(
            analysis_id="scan-test-1",
            remediation_id="rem-sample-1",
            base_branch="develop",
            proposed_branch="patchproof/fix-requests-2.20.0",
            pr_title="Upgrade requests",
            user_confirmed=True
        )
        resp = GitHubService.create_draft_pull_request(
            repo_url="https://github.com/acme-org/secure-app",
            proposal=sample_proposal,
            request=req,
            client=client
        )

        assert resp.success is True
        assert resp.draft_status == "DRAFT (VERIFIED)"
        assert resp.verified_on_github is True
        assert resp.pr_number == 88
        assert resp.pr_url == "https://github.com/acme-org/secure-app/pull/88"
        assert resp.commit_sha == "new_commit_sha_555"
        assert resp.branch_name == "patchproof/fix-requests-2.20.0"
        assert resp.base_branch == "develop"
        assert resp.changed_files == ["requirements.txt"]

        # Ensure base branch was NEVER modified
        for method, path, body in captured_calls:
            if "git/refs" in path and method == "POST":
                assert "refs/heads/develop" != body["ref"]


# 10. Safety invariant: If PR is not draft on GitHub, verification raises exception
def test_pr_verification_rejects_non_draft(sample_proposal, sample_request, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_validToken1234567890")

    remote_file_content = "requests==2.19.1\n"
    remote_b64 = base64.b64encode(remote_file_content.encode("utf-8")).decode("utf-8")

    def mock_handler(request: httpx.Request):
        method = request.method
        path = request.url.path

        if method == "GET" and path == "/repos/acme-org/secure-app":
            return httpx.Response(200, json={"default_branch": "main"})
        if method == "GET" and path == "/repos/acme-org/secure-app/contents/requirements.txt":
            return httpx.Response(200, json={"content": remote_b64, "sha": "blob1"})
        if method == "GET" and path == "/repos/acme-org/secure-app/git/ref/heads/main":
            return httpx.Response(200, json={"object": {"sha": "c1"}})
        if method == "GET" and path == "/repos/acme-org/secure-app/git/commits/c1":
            return httpx.Response(200, json={"tree": {"sha": "t1"}})
        if method == "GET" and "/git/ref/heads/patchproof/" in path:
            return httpx.Response(404)
        if method == "POST" and path == "/repos/acme-org/secure-app/git/blobs":
            return httpx.Response(201, json={"sha": "b2"})
        if method == "POST" and path == "/repos/acme-org/secure-app/git/trees":
            return httpx.Response(201, json={"sha": "t2"})
        if method == "POST" and path == "/repos/acme-org/secure-app/git/commits":
            return httpx.Response(201, json={"sha": "c2"})
        if method == "POST" and path == "/repos/acme-org/secure-app/git/refs":
            return httpx.Response(201, json={"ref": "refs/heads/test", "object": {"sha": "c2"}})
        if method == "POST" and path == "/repos/acme-org/secure-app/pulls":
            return httpx.Response(201, json={"number": 99, "html_url": "http://pr/99", "draft": False})
        if method == "GET" and path == "/repos/acme-org/secure-app/pulls/99":
            # Buggy GitHub returned draft=False!
            return httpx.Response(200, json={"number": 99, "draft": False, "head": {}, "base": {}})
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    with httpx.Client(transport=transport) as client:
        resp = GitHubService.create_draft_pull_request(
            repo_url="https://github.com/acme-org/secure-app",
            proposal=sample_proposal,
            request=sample_request,
            client=client
        )
        assert resp.success is False
        assert "critical safety violation" in resp.message.lower() or "draft mode" in resp.message.lower()
