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
                                
                                findings.append(SecretFinding(
                                    secret_type=sec_name,
                                    file_path=rel_path,
                                    line_number=line_idx,
                                    commit_sha=commit_sha[:8] if commit_sha else "HEAD",
                                    detection_source="Pattern & High-Entropy Matcher",
                                    confidence="High",
                                    masked_value=masked,
                                    remediation_instructions=ROTATION_GUIDES.get(
                                        sec_name,
                                        "Immediately revoke and rotate the secret. Update CI/CD secrets store."
                                    )
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
                                        findings.append(SecretFinding(
                                            secret_type=f"{sec_name} (Git History)",
                                            file_path=current_file,
                                            line_number=None,
                                            commit_sha=current_commit,
                                            detection_source="Git Commit Log Scanner",
                                            confidence="High",
                                            masked_value=masked,
                                            remediation_instructions=ROTATION_GUIDES.get(
                                                sec_name,
                                                "Secret was found in Git history. Purge commit with git-filter-repo or BFG and revoke the key immediately."
                                            )
                                        ))
            except Exception:
                pass

        return findings
