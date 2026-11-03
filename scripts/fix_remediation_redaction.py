from pathlib import Path
import re

security_path = Path("backend/app/core/security.py")
remediation_path = Path("backend/app/services/remediation_service.py")

security = security_path.read_text(encoding="utf-8")
remediation = remediation_path.read_text(encoding="utf-8")

# Widen GitHub token matching to include shortened test tokens.
lines = security.splitlines(keepends=True)
found = False

for i, line in enumerate(lines):
    if '"GitHub Personal Access Token":' in line:
        lines[i] = (
            '    "GitHub Personal Access Token": '
            're.compile(r"\\b(ghp_[A-Za-z0-9]{20,40}|'
            'github_pat_[A-Za-z0-9_]{82})\\b"),\n'
        )
        found = True
        break

if not found:
    raise RuntimeError("GitHub token pattern not found.")

security = "".join(lines)

# Add content-aware redaction helper.
if "def redact_secrets_in_content(" not in security:
    helper = '''

def redact_secrets_in_content(content: str) -> str:
    """Redact credential matches without altering surrounding text."""
    if not content:
        return ""

    sanitized = str(content)

    # Redact complete PEM private-key blocks.
    pem = re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
        r".*?"
        r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.DOTALL,
    )
    sanitized = pem.sub("[REDACTED PRIVATE KEY]", sanitized)

    for name, pattern in SECRET_PATTERNS.items():
        if name == "RSA / Private Key Block":
            continue

        def replace_match(match):
            token = match.group(1) if match.groups() else match.group(0)
            return match.group(0).replace(
                token, redact_secret_string(token), 1
            )

        sanitized = pattern.sub(replace_match, sanitized)

    return sanitized

'''

    marker = "\ndef validate_repository_url("
    if marker not in security:
        raise RuntimeError("Security helper insertion point not found.")
    security = security.replace(marker, helper + marker, 1)

# Update remediation import.
old_import = "from app.core.security import redact_secret_string"
new_import = "from app.core.security import redact_secrets_in_content"

if old_import not in remediation:
    raise RuntimeError("Remediation import not found.")

remediation = remediation.replace(old_import, new_import, 1)

# Locate and replace the actual redaction block by its boundaries.
start_marker = "                # Redact secrets in original and modified manifest contents."
end_marker = '                sanitized_diff = "".join(sanitized_diff_lines)'

start = remediation.find(start_marker)
if start == -1:
    raise RuntimeError("Redaction block start not found.")

end = remediation.find(end_marker, start)
if end == -1:
    raise RuntimeError("Redaction block end not found.")

end += len(end_marker)

replacement = '''                # Redact detected credentials while preserving manifest text.
                orig_text = redact_secrets_in_content(orig_raw)
                mod_text = redact_secrets_in_content(mod_raw)
                sanitized_diff = redact_secrets_in_content(diff_text)'''

remediation = remediation[:start] + replacement + remediation[end:]

# Write only after every validation succeeds.
security_path.write_text(security, encoding="utf-8")
remediation_path.write_text(remediation, encoding="utf-8")

print("PATCH APPLIED SUCCESSFULLY.")
print("Updated security.py and remediation_service.py")