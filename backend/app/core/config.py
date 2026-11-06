import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
WORKSPACE_DIR = BASE_DIR.parent
FIXTURES_DIR = WORKSPACE_DIR / "fixtures"
TEMP_DIR = Path(os.environ.get("TEMP", "/tmp")) / "patchproof_repos"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Load .env file from project root if present
load_dotenv(BASE_DIR / ".env")

OSV_QUERY_BATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns"
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
FIRST_EPSS_URL = "https://api.first.org/data/v1/epss"
DEPS_DEV_URL = "https://api.deps.dev/v3"

GITHUB_TOKEN = (os.environ.get("PATCHPROOF_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN", "")).strip()

def get_github_token() -> str:
    """Safely retrieves the configured GitHub token without logging or exposing it."""
    load_dotenv(BASE_DIR / ".env", override=False)
    return (os.environ.get("PATCHPROOF_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN", "")).strip()

# Prohibit merge operations globally
NEVER_MERGE = True

# Offline mode and OSV query network timeout
PATCHPROOF_OFFLINE = os.environ.get("PATCHPROOF_OFFLINE", "").strip().lower() in ("1", "true", "yes")
try:
    OSV_TIMEOUT = float(os.environ.get("PATCHPROOF_OSV_TIMEOUT", "2.0"))
    if OSV_TIMEOUT <= 0:
        OSV_TIMEOUT = 2.0
except (ValueError, TypeError):
    OSV_TIMEOUT = 2.0



