import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import httpx
from app.core.config import CISA_KEV_URL, FIRST_EPSS_URL, PATCHPROOF_OFFLINE, OSV_TIMEOUT

logger = logging.getLogger("ThreatIntelService")

CACHE_DIR = Path(__file__).resolve().parent.parent / "core"
KEV_CACHE_FILE = CACHE_DIR / "cisa_kev_cache.json"
EPSS_CACHE_FILE = CACHE_DIR / "epss_cache.json"

class ThreatIntelService:
    _kev_catalog: Optional[Dict[str, Any]] = None # Mapping of cve_id -> record
    _kev_metadata: Dict[str, Any] = {}
    _epss_cache: Dict[str, Dict[str, Any]] = {}
    _initialized: bool = False

    @classmethod
    def initialize(cls):
        """Loads cached KEV and EPSS intelligence from local disk safely."""
        if cls._initialized:
            return

        # 1. Load CISA KEV local cache
        if KEV_CACHE_FILE.is_file():
            try:
                raw = json.loads(KEV_CACHE_FILE.read_text(encoding="utf-8", errors="ignore"))
                cls._kev_catalog = {}
                for v in raw.get("vulnerabilities", []):
                    cve = v.get("cveID", "").strip().upper()
                    if cve:
                        cls._kev_catalog[cve] = v
                cls._kev_metadata = {
                    "catalog_version": raw.get("catalogVersion", "Unknown"),
                    "count": len(cls._kev_catalog),
                    "source": f"CISA KEV Catalog ({raw.get('catalogVersion', 'Cached')})",
                    "cached": True
                }
                logger.info("Loaded %d CISA KEV entries from local cache.", len(cls._kev_catalog))
            except Exception as e:
                logger.warning("Failed to load local CISA KEV cache: %s", e)
                cls._kev_catalog = {}
        else:
            cls._kev_catalog = {}

        # 2. Load EPSS local cache
        if EPSS_CACHE_FILE.is_file():
            try:
                cls._epss_cache = json.loads(EPSS_CACHE_FILE.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                cls._epss_cache = {}

        cls._initialized = True

    @classmethod
    async def refresh_cisa_kev(cls, client: Optional[httpx.AsyncClient] = None) -> bool:
        """Fetches live official CISA KEV catalog if online."""
        cls.initialize()
        if PATCHPROOF_OFFLINE or os.environ.get("PATCHPROOF_OFFLINE", "").strip().lower() in ("1", "true", "yes"):
            return False

        try:
            close_client = False
            if client is None:
                client = httpx.AsyncClient(timeout=OSV_TIMEOUT * 2)
                close_client = True
            try:
                resp = await client.get(CISA_KEV_URL)
                if resp.status_code == 200:
                    raw = resp.json()
                    catalog = {}
                    for v in raw.get("vulnerabilities", []):
                        cve = v.get("cveID", "").strip().upper()
                        if cve:
                            catalog[cve] = v
                    cls._kev_catalog = catalog
                    cls._kev_metadata = {
                        "catalog_version": raw.get("catalogVersion", "Live"),
                        "count": len(catalog),
                        "source": f"Official CISA KEV Catalog ({raw.get('catalogVersion', 'Live')})",
                        "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                        "cached": False
                    }
                    # Persist cache safely
                    try:
                        KEV_CACHE_FILE.write_text(json.dumps(raw, indent=2), encoding="utf-8")
                    except Exception:
                        pass
                    return True
            finally:
                if close_client:
                    await client.aclose()
        except Exception as e:
            logger.warning("CISA KEV catalog live fetch failed: %s. Using local cache.", e)
        return False

    @classmethod
    def get_cisa_kev_status(cls, cve_id: Optional[str], aliases: Optional[List[str]] = None) -> Tuple[bool, str, Optional[str], str]:
        """
        Determines CISA KEV status based on exact matching against the authoritative catalog.
        Returns: (is_kev: bool, status: str, date_added: Optional[str], source: str)
          status: 'confirmed_exploited' | 'not_listed' | 'unavailable'
        """
        cls.initialize()

        all_cves = []
        if cve_id and cve_id.upper().startswith("CVE-"):
            all_cves.append(cve_id.strip().upper())
        for a in aliases or []:
            if a and a.upper().startswith("CVE-"):
                clean = a.strip().upper()
                if clean not in all_cves:
                    all_cves.append(clean)

        if not all_cves:
            return False, "not_listed", None, "No CVE assigned to correlate with CISA KEV"

        if cls._kev_catalog is None or (not cls._kev_catalog and cls._kev_metadata.get("status") == "unavailable"):
            return False, "unavailable", None, "CISA KEV catalog data unavailable"

        for cve in all_cves:
            if cve in cls._kev_catalog:
                entry = cls._kev_catalog[cve]
                source = cls._kev_metadata.get("source", "CISA KEV Catalog")
                return True, "confirmed_exploited", entry.get("dateAdded"), source

        source = cls._kev_metadata.get("source", "CISA KEV Catalog")
        return False, "not_listed", None, f"Verified not listed in {source}"

    @classmethod
    async def fetch_epss_scores(cls, cve_ids: List[str], client: Optional[httpx.AsyncClient] = None) -> Dict[str, Dict[str, Any]]:
        """
        Retrieves authentic EPSS probability and percentile from the FIRST EPSS API.
        Validates numeric ranges: 0.0 <= epss <= 1.0, 0.0 <= percentile <= 1.0.
        Returns unavailable when the source cannot be reached and no valid cache exists.
        Never fabricates invented probabilities.
        """
        cls.initialize()
        results: Dict[str, Dict[str, Any]] = {}
        missing_cves = []

        for cve in cve_ids:
            cve_clean = cve.strip().upper()
            if cve_clean in cls._epss_cache:
                results[cve_clean] = cls._epss_cache[cve_clean]
            else:
                missing_cves.append(cve_clean)

        is_offline = PATCHPROOF_OFFLINE or os.environ.get("PATCHPROOF_OFFLINE", "").strip().lower() in ("1", "true", "yes")

        if missing_cves and not is_offline:
            try:
                close_client = False
                if client is None:
                    client = httpx.AsyncClient(timeout=OSV_TIMEOUT)
                    close_client = True

                try:
                    # Query up to 30 CVEs at a time
                    cve_query = ",".join(missing_cves[:30])
                    url = f"{FIRST_EPSS_URL}?cve={cve_query}"
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        now_iso = datetime.now(timezone.utc).isoformat()
                        for item in data.get("data", []):
                            c_id = item.get("cve", "").strip().upper()
                            try:
                                prob = float(item.get("epss", 0.0))
                                perc = float(item.get("percentile", 0.0))
                                # Validate numeric ranges strictly
                                if 0.0 <= prob <= 1.0 and 0.0 <= perc <= 1.0:
                                    entry = {
                                        "epss": prob,
                                        "percentile": perc,
                                        "date": item.get("date"),
                                        "source": "FIRST EPSS API",
                                        "status": "live",
                                        "retrieved_at": now_iso
                                    }
                                    cls._epss_cache[c_id] = entry
                                    results[c_id] = entry
                            except (ValueError, TypeError):
                                pass

                        # Persist updated cache
                        try:
                            EPSS_CACHE_FILE.write_text(json.dumps(cls._epss_cache, indent=2), encoding="utf-8")
                        except Exception:
                            pass
                finally:
                    if close_client:
                        await client.aclose()
            except Exception as e:
                logger.warning("FIRST EPSS API query failed: %s", e)

        # For any CVE still not in results, return explicit unavailable state
        for cve in cve_ids:
            cve_clean = cve.strip().upper()
            if cve_clean not in results:
                results[cve_clean] = {
                    "epss": None,
                    "percentile": None,
                    "date": None,
                    "source": "Unavailable",
                    "status": "unavailable",
                    "retrieved_at": None
                }

        return results
