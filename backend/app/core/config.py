import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
WORKSPACE_DIR = BASE_DIR.parent
FIXTURES_DIR = WORKSPACE_DIR / "fixtures"
TEMP_DIR = Path(os.environ.get("TEMP", "/tmp")) / "patchproof_repos"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

OSV_QUERY_BATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns"
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
FIRST_EPSS_URL = "https://api.first.org/data/v1/epss"
DEPS_DEV_URL = "https://api.deps.dev/v3"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Prohibit merge operations globally
NEVER_MERGE = True
