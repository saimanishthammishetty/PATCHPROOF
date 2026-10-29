import re
import ipaddress
from urllib.parse import urlparse
from typing import Tuple, List, Dict, Any

# Regular expressions for credential scanning
SECRET_PATTERNS: Dict[str, re.Pattern] = {
    "AWS Access Key ID": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
    "AWS Secret Access Key": re.compile(r"(?i)\baws_secret_access_key\s*=\s*([A-Za-z0-9/+=]{40})\b"),
    "GitHub Personal Access Token": re.compile(r"\b(ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82})\b"),
    "GitHub OAuth Token": re.compile(r"\b(gho_[A-Za-z0-9]{36})\b"),
    "Slack Bot Token": re.compile(r"\b(xoxb-[0-9]{11,13}-[0-9]{11,13}-[A-Za-z0-9]{24})\b"),
    "Slack User Token": re.compile(r"\b(xoxp-[0-9]{11,13}-[0-9]{11,13}-[A-Za-z0-9]{24})\b"),
    "OpenAI API Key": re.compile(r"\b(sk-[A-Za-z0-9]{32,64})\b"),
    "Stripe Secret Key": re.compile(r"\b(sk_live_[0-9a-zA-Z]{24,34})\b"),
    "Google Cloud API Key": re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b"),
    "RSA / Private Key Block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Generic High-Entropy Secret": re.compile(r"(?i)(?:api[_-]?key|secret|access[_-]?token|auth[_-]?token)\s*[:=]\s*['\"]([a-zA-Z0-9_\-\.]{20,})['\"]"),
    "JWT Bearer Token": re.compile(r"\b(eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b"),
}

DISALLOWED_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal",
    "169.254.169.254"
}

def redact_secret_string(val: str, visible_prefix: int = 4, visible_suffix: int = 4) -> str:
    """
    Safely redacts a sensitive string so that raw values are never printed in UI, logs, or API responses.
    Example: 'ghp_1234567890abcdef1234567890abcdef' -> 'ghp_****************************cdef'
    """
    if not val:
        return ""
    val_str = str(val).strip()
    length = len(val_str)
    if length <= 6:
        return "******"
    if length <= visible_prefix + visible_suffix:
        return val_str[:2] + ("*" * (length - 4)) + val_str[-2:]
    
    prefix = val_str[:visible_prefix]
    suffix = val_str[-visible_suffix:]
    mask_length = max(6, length - (visible_prefix + visible_suffix))
    return f"{prefix}{'*' * mask_length}{suffix}"

def validate_repository_url(url: str) -> Tuple[bool, str]:
    """
    Validates a repository URL, preventing SSRF, localhost scanning, and invalid schemes.
    Supports public GitHub repositories and local test fixtures (explicitly marked).
    """
    if not url or not isinstance(url, str):
        return False, "Repository URL cannot be empty."
    
    url = url.strip()
    
    # Allow local fixture or sample identifiers for demonstration and testing
    if url.startswith("fixture://") or url.startswith("demo://"):
        return True, "Valid test fixture URL"
    
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        return False, f"Invalid URL scheme '{parsed.scheme}'. Only https:// GitHub repositories are permitted."
    
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "Invalid repository URL: host is missing."
    
    if host in DISALLOWED_HOSTS:
        return False, f"Scanning internal host '{host}' is forbidden."
    
    # Check IP addresses (prevent RFC 1918 private networking)
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            return False, f"Access to private/local IP '{host}' is strictly prohibited."
    except ValueError:
        pass
    
    # Check domain
    if host != "github.com" and not host.endswith(".github.com"):
        return False, "PATCHPROOF currently analyzes GitHub repositories (https://github.com/owner/repo)."
    
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) < 2:
        return False, "GitHub URL must specify both owner and repository (e.g., https://github.com/owner/repo)."
    
    return True, "Valid GitHub repository URL"

def sanitize_untrusted_content(content: str) -> str:
    """
    Shields LLM prompts and audit messages from prompt injection or instruction hijacking
    contained in untrusted repo content (READMEs, commit messages, dependencies).
    """
    if not content:
        return ""
    # Strip potential prompt injection delimiter hacks
    sanitized = re.sub(r"(?i)(ignore (all )?previous instructions|system prompt|you are now|override instructions)", "[FILTERED_INSTRUCTION_OVERRIDE]", content)
    return sanitized[:5000]

def verify_safe_pull_request_action(action: str) -> None:
    """
    Safety guarantee: Ensures PATCHPROOF never merges or bypasses human review.
    Raises RuntimeError if a merge action is requested.
    """
    forbidden_actions = {"merge", "auto_merge", "bypass_review", "force_push", "direct_commit_to_main"}
    if action.lower() in forbidden_actions:
        raise RuntimeError(f"CRITICAL SAFETY VIOLATION: PATCHPROOF is prohibited from performing '{action}'. Human review is strictly required.")

