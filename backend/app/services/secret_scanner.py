import os
import subprocess
from pathlib import Path
from typing import List, Optional
from app.models.schemas import SecretFinding
from app.core.security import SECRET_PATTERNS, redact_secret_string

ROTATION_GUIDES = {
    "AWS Access Key ID": "Revoke IAM User access key in AWS IAM console, generate new credentials, and store in AWS Secrets Manager.",
    "AWS Secret Access Key": "Rotate associated AWS secret key immediately. Review CloudTrail logs for unauthorized API activity.",
    "GitHub Personal Access Token": "Revoke token immediately at github.com/settings/tokens. Check audit log for anomalous repository commits or access.",
    "GitHub OAuth Token": "Revoke OAuth token from GitHub Settings -> Applications and trigger re-authentication.",
    "Slack Bot Token": "Revoke bot token in Slack API app portal (api.slack.com/apps) and reissue new bot token.",
    "OpenAI API Key": "Delete compromised key on platform.openai.com/api-keys and provision a scoped project key.",
    "Stripe Secret Key": "Roll the secret key in the Stripe Dashboard (Developers -> API Keys) with immediate expiration.",
    "Google Cloud API Key": "Restrict and delete API key in Google Cloud Console -> APIs & Services -> Credentials.",
    "RSA / Private Key Block": "De-authorize and remove compromised private key from all authorized_keys files and generate a new key pair.",
    "Generic High-Entropy Secret": "Revoke key at vendor dashboard, rotate application configuration, and verify secrets are stored in environment variables.",
    "JWT Bearer Token": "Invalidate token signing key or revoke active sessions in authentication provider."
}

class SecretScanner:
    @staticmethod
    def classify_secret(raw_token: str, file_path: str, sec_name: str, line: str = "") -> dict:
        norm_path = file_path.replace("\\", "/").lower()
        parts = norm_path.split("/")
        filename = parts[-1]

        # Scope determination
        if any(p in ("fixtures", "fixture") for p in parts[:-1]):
            scope = "fixture"
        elif any(p in ("tests", "test", "__tests__") for p in parts[:-1]) or filename.startswith("test_") or filename.endswith(("_test.py", ".spec.ts", ".test.js")):
            scope = "test"
        elif any(p in ("docs", "documentation") for p in parts[:-1]) or filename.endswith((".md", ".rst", ".adoc", ".txt")):
            scope = "documentation"
        else:
            scope = "production"

        token_lower = raw_token.lower()
        line_lower = line.lower()

        # Explicit known synthetic markers
        is_known_synthetic = (
            raw_token == "AKIAIOSFODNN7EXAMPLE"
            or any(k in token_lower for k in ("example", "testdummy", "testsecret", "testsample", "faketoken", "dummytoken", "mocktoken", "samplekey", "placeholder", "changeme"))
            or "1234567890abcdef" in token_lower
            or "abcdef123456" in token_lower
            or "0123456789" in token_lower
            or "xxxxxx" in token_lower
            or "00000000" in token_lower
            or "11111111" in token_lower
            or "# example:" in line_lower
            or "// example:" in line_lower
        )

        clean_sec_name = sec_name.replace(" (Git History)", "")
        rotation_guide = ROTATION_GUIDES.get(
            clean_sec_name,
            "Immediately revoke and rotate the secret. Update CI/CD secrets store and invalidate active credentials."
        )

        if is_known_synthetic:
            is_synthetic = True
            if scope == "test":
                category = "Test credential"
                reason = f"Explicit test placeholder token containing mock marker in {file_path}"
                synth_reason = f"Test placeholder matching known dummy/mock pattern for {sec_name}"
            elif scope == "documentation":
                category = "Documentation example"
                reason = f"Documentation placeholder matching known synthetic example pattern in {file_path}"
                synth_reason = f"Synthetically constructed placeholder used in documentation for {sec_name}"
            elif scope == "fixture":
                category = "Synthetic/example credential"
                reason = f"Test fixture placeholder token with synthetic marker in {file_path}"
                synth_reason = f"Fixture example credential for {sec_name}"
            else:
                category = "Synthetic/example credential"
                reason = f"Source code comment/docstring placeholder matching synthetic example pattern in {file_path}"
                synth_reason = f"Synthetic placeholder matching recognized dummy pattern for {sec_name}"
        else:
            # Unknown or high-entropy credential
            # Conservative treatment: NEVER classify as fake solely because it is in a test directory!
            is_synthetic = False
            synth_reason = None
            if scope == "test":
                category = "Potential real credential"
                reason = f"High-entropy token detected in test file without placeholder markers; treated conservatively as potential real credential in {file_path}"
            elif scope == "documentation":
                category = "Potential real credential"
                reason = f"High-entropy token detected in documentation without placeholder markers; treated conservatively in {file_path}"
            elif scope == "fixture":
                category = "Potential real credential"
                reason = f"Credential detected in fixture without synthetic markers; treated conservatively in {file_path}"
            else:
                category = "Potential real credential"
                reason = f"Active high-entropy credential discovered in repository codebase: {file_path}"

        return {
            "is_synthetic": is_synthetic,
            "synthetic_reason": synth_reason,
            "scope": scope,
            "secret_category": category,
            "classification_reason": reason,
            "rotation_guidance": rotation_guide
        }

    @staticmethod
    def scan_repository(repo_path: Path, commit_sha: str = "HEAD") -> List[SecretFinding]:
        """
        Scans files in repository and git history commits for leaked secrets and credentials.
        Strictly redacts all secret values before returning.
        """
        findings: List[SecretFinding] = []
        
        # 1. Scan working tree files
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", ".venv", "vendor", "dist", "build")]
            
            for file_name in files:
                # Skip binary files or lockfiles
                if file_name.endswith((".png", ".jpg", ".zip", ".tar", ".gz", ".exe", ".bin")):
                    continue
                
                full_path = Path(root) / file_name
                try:
                    rel_path = str(full_path.relative_to(repo_path)).replace("\\", "/")
                except ValueError:
                    rel_path = file_name
                
                try:
                    # Limit file read size to 1MB
                    if full_path.stat().st_size > 1024 * 1024:
                        continue
                    
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    
                    for line_idx, line in enumerate(lines, 1):
                        for sec_name, pattern in SECRET_PATTERNS.items():
                            match = pattern.search(line)
                            if match:
                                # Extract token value: prefer group 1 if captured, otherwise full match
                                raw_token = match.group(1) if match.groups() else match.group(0)
                                # Redact immediately - NEVER expose raw secret
                                masked = redact_secret_string(raw_token)
                                info = SecretScanner.classify_secret(raw_token, rel_path, sec_name, line)
                                
                                findings.append(SecretFinding(
                                    secret_type=sec_name,
                                    file_path=rel_path,
                                    line_number=line_idx,
                                    commit_sha=commit_sha[:8] if commit_sha else "HEAD",
                                    detection_source="Pattern & High-Entropy Matcher",
                                    confidence="High",
                                    masked_value=masked,
                                    remediation_instructions=info["rotation_guidance"],
                                    is_synthetic=info["is_synthetic"],
                                    synthetic_reason=info["synthetic_reason"],
                                    scope=info["scope"],
                                    secret_category=info["secret_category"],
                                    classification_reason=info["classification_reason"],
                                    rotation_guidance=info["rotation_guidance"]
                                ))
                except Exception:
                    continue

        # 2. Check git history for secrets committed in previous commits (up to last 10 commits)
        if (repo_path / ".git").exists():
            try:
                git_log = subprocess.run(
                    ["git", "-C", str(repo_path), "log", "-p", "-n", "10", "--unified=0"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False
                )
                if git_log.returncode == 0:
                    current_commit = commit_sha[:8] if commit_sha else "HEAD"
                    current_file = "git_history"
                    for line in git_log.stdout.splitlines():
                        if line.startswith("commit "):
                            current_commit = line.split()[1][:8]
                        elif line.startswith("+++ b/"):
                            current_file = line.replace("+++ b/", "").strip()
                        elif line.startswith("+") and not line.startswith("+++"):
                            added_line = line[1:].strip()
                            for sec_name, pattern in SECRET_PATTERNS.items():
                                match = pattern.search(added_line)
                                if match:
                                    raw_token = match.group(1) if match.groups() else match.group(0)
                                    masked = redact_secret_string(raw_token)
                                    # Avoid duplicate findings for same file/secret
                                    if not any(f.masked_value == masked and f.file_path == current_file for f in findings):
                                        info = SecretScanner.classify_secret(raw_token, current_file, sec_name, added_line)
                                        findings.append(SecretFinding(
                                            secret_type=f"{sec_name} (Git History)",
                                            file_path=current_file,
                                            line_number=None,
                                            commit_sha=current_commit,
                                            detection_source="Git Commit Log Scanner",
                                            confidence="High",
                                            masked_value=masked,
                                            remediation_instructions=info["rotation_guidance"],
                                            is_synthetic=info["is_synthetic"],
                                            synthetic_reason=info["synthetic_reason"],
                                            scope=info["scope"],
                                            secret_category=info["secret_category"],
                                            classification_reason=info["classification_reason"],
                                            rotation_guidance=info["rotation_guidance"]
                                        ))
            except Exception:
                pass

        return findings
