import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.models.schemas import Component

class SBOMService:
    @staticmethod
    def generate_cyclonedx_json(
        repo_name: str,
        commit_sha: str,
        components: List[Component]
    ) -> Dict[str, Any]:
        """
        Generates a valid CycloneDX 1.5 JSON Software Bill of Materials (SBOM).
        """
        bom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "version": 1,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tools": [
                    {
                        "vendor": "PATCHPROOF",
                        "name": "patchproof-sbom-engine",
                        "version": "1.0.0"
                    }
                ],
                "component": {
                    "type": "application",
                    "name": repo_name,
                    "version": commit_sha[:8] if commit_sha else "latest",
                    "description": f"Analyzed repository: {repo_name} (commit {commit_sha})"
                }
            },
            "components": [],
            "dependencies": []
        }

        dep_map: Dict[str, List[str]] = {}

        for c in components:
            comp_entry: Dict[str, Any] = {
                "type": "library",
                "bom-ref": c.purl,
                "name": c.name,
                "version": c.version,
                "purl": c.purl,
                "scope": "required" if c.direct else "optional",
                "properties": [
                    {"name": "patchproof:ecosystem", "value": c.ecosystem},
                    {"name": "patchproof:direct", "value": str(c.direct).lower()},
                    {"name": "patchproof:manifest", "value": c.manifest_path},
                    {"name": "patchproof:reachability", "value": c.reachability}
                ]
            }
            if c.license and c.license != "Unknown":
                comp_entry["licenses"] = [{"license": {"id": c.license}}]

            bom["components"].append(comp_entry)
            
            # Map dependency tree
            if c.direct:
                if repo_name not in dep_map:
                    dep_map[repo_name] = []
                dep_map[repo_name].append(c.purl)

        # Root dependency node
        bom["dependencies"].append({
            "ref": repo_name,
            "dependsOn": dep_map.get(repo_name, [])
        })

        return bom

    @staticmethod
    def generate_spdx_json(
        repo_name: str,
        commit_sha: str,
        components: List[Component]
    ) -> Dict[str, Any]:
        """
        Generates an SPDX 2.3 JSON SBOM.
        """
        doc = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": f"SBOM-{repo_name}",
            "documentNamespace": f"https://patchproof.dev/spdx/{repo_name}/{commit_sha}",
            "creationInfo": {
                "creators": ["Tool: PATCHPROOF-1.0.0"],
                "created": datetime.now(timezone.utc).isoformat()
            },
            "packages": [],
            "relationships": []
        }

        for idx, c in enumerate(components):
            spdx_id = f"SPDXRef-Package-{idx+1}-{c.name.replace('/', '-')}"
            doc["packages"].append({
                "SPDXID": spdx_id,
                "name": c.name,
                "versionInfo": c.version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": c.license or "NOASSERTION",
                "licenseDeclared": c.license or "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": c.purl
                    }
                ]
            })
            doc["relationships"].append({
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": spdx_id
            })

        return doc
