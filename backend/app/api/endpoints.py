import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from app.models.schemas import (
    AnalysisRequest, AnalysisResult, Component, VulnerabilityFinding,
    SecretFinding, DependencyHealthFinding, RemediationProposal,
    DraftPRRequest, DraftPRResponse, AuditEntry, RiskOverview,
    DemoRepositoryInfo, CodeDebugRequest, CodeDebugResponse
)
from app.services.repository_service import RepositoryService
from app.services.dependency_parser import DependencyParser
from app.services.sbom_service import SBOMService
from app.services.vulnerability_service import VulnerabilityService
from app.services.secret_scanner import SecretScanner
from app.services.dependency_health import DependencyHealthService
from app.services.risk_engine import RiskEngine
from app.services.remediation_service import RemediationService
from app.services.github_service import GitHubService
from app.services.audit_service import audit_logger
from app.services.debug_service import DebugService

router = APIRouter(prefix="/api", tags=["Analyses"])

@router.get("/health")
def api_health_check():
    return {
        "status": "healthy",
        "safety_guard": "NEVER_MERGE_ACTIVE"
    }

# Store active analysis results in memory
ANALYSES_STORE: Dict[str, AnalysisResult] = {}
REPO_PATHS_STORE: Dict[str, str] = {}

DEMO_REPOSITORIES: List[DemoRepositoryInfo] = [
    DemoRepositoryInfo(
        id="vulnerable-python",
        name="Vulnerable Python Microservice",
        url="fixture://vulnerable-python-repo",
        ecosystem="Python / PyPI",
        description="Python repository with outdated requests 2.19.1 (CVE-2018-18074), urllib3 1.24.1 (CVE-2019-11324), and PyYAML 5.2 (CVE-2020-14343).",
        expected_findings="3 Critical/High CVEs (1 Critical PyYAML, High requests & urllib3), 1 Safe Remediation proposal."
    ),
    DemoRepositoryInfo(
        id="vulnerable-node",
        name="Compromised Node.js / React App",
        url="fixture://vulnerable-node-repo",
        ecosystem="Node.js / npm",
        description="Node app with prototype pollution in lodash 4.17.15 (CVE-2020-8203) and SSRF in axios 0.21.1.",
        expected_findings="2 High severity CVEs, npm-lockfile dependencies, safe version bump to 4.17.19."
    ),
    DemoRepositoryInfo(
        id="secret-leak",
        name="Git History Secret Leaks Fixture",
        url="fixture://secret-leak-repo",
        ecosystem="Multi-language",
        description="Repository containing simulated AWS, GitHub, and OpenAI credentials committed to historical commits.",
        expected_findings="3 High-confidence credential leaks with strict automated redaction and rotation playbooks."
    ),
    DemoRepositoryInfo(
        id="secure-go",
        name="Hardened Go Cloud Microservice",
        url="fixture://secure-go-repo",
        ecosystem="Golang",
        description="Clean Go project using up-to-date modules with clean SBOM and zero detected CVEs.",
        expected_findings="0 Vulnerabilities, 10/10 Health Score, Low Risk (0/100)."
    )
]

@router.get("/demos", response_model=List[DemoRepositoryInfo])
def get_demo_repositories():
    """Returns available demonstration and test fixture repositories."""
    return DEMO_REPOSITORIES

@router.post("/analyses", response_model=AnalysisResult)
async def start_analysis(request: AnalysisRequest):
    """
    Executes the real end-to-end PATCHPROOF analysis pipeline:
    Repository retrieval -> Dependency parsing -> SBOM generation ->
    OSV.dev vulnerability lookup -> Secret detection -> Health inspection ->
    Transparent risk scoring -> Safe remediation diff computation.
    """
    analysis_id = f"scan-{uuid.uuid4().hex[:8]}"
    
    # 1. Setup repository
    try:
        repo_path, repo_name, commit_sha, branch = RepositoryService.setup_repository(
            request.repo_url,
            request.branch
        )
        REPO_PATHS_STORE[analysis_id] = str(repo_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    audit_logger.record_event(
        event_type="ANALYSIS_INITIALIZED",
        repository=repo_name,
        commit_sha=commit_sha,
        details=f"Analysis initiated for repository {request.repo_url} on commit {commit_sha[:8]}"
    )

    # 2. Dependency parsing
    components = DependencyParser.parse_repository(repo_path)
    audit_logger.record_event(
        event_type="DEPENDENCIES_PARSED",
        repository=repo_name,
        commit_sha=commit_sha,
        details=f"Identified {len(components)} package dependencies across manifests"
    )

    # 3. Vulnerability lookup
    vulnerabilities = await VulnerabilityService.scan_components(components)
    scan_source = (
        "Live OSV.dev" if VulnerabilityService.last_scan_mode == "live_osv"
        else ("Local Offline Advisory Database" if VulnerabilityService.last_scan_mode == "offline"
              else "Local Fallback Advisory Database (Network Fallback)")
    )
    audit_logger.record_event(
        event_type="VULNERABILITY_SCAN_COMPLETED",
        repository=repo_name,
        commit_sha=commit_sha,
        details=f"{scan_source} scan identified {len(vulnerabilities)} unique security vulnerabilities"
    )

    # 4. Secret scanning
    secrets: List[SecretFinding] = []
    if request.run_secret_scan:
        secrets = SecretScanner.scan_repository(repo_path, commit_sha)
        if secrets:
            audit_logger.record_event(
                event_type="SECRETS_IDENTIFIED",
                repository=repo_name,
                commit_sha=commit_sha,
                details=f"Detected {len(secrets)} credential leak(s). All values redacted immediately."
            )

    # 5. Dependency health & suspicious package analysis
    health_findings: List[DependencyHealthFinding] = []
    if request.run_health_check:
        health_findings = DependencyHealthService.analyze_health(repo_path, components)

    # 6. Transparent deterministic risk scoring
    risk_overview = RiskEngine.calculate_overall_risk(
        components=components,
        vulnerabilities=vulnerabilities,
        secrets=secrets,
        health_findings=health_findings
    )
    audit_logger.record_event(
        event_type="RISK_SCORING_FINALIZED",
        repository=repo_name,
        commit_sha=commit_sha,
        details=f"Risk Score computed: {risk_overview.score}/100 ({risk_overview.label})"
    )

    # 7. Safe remediation proposals
    remediations = RemediationService.generate_remediations(
        repo_path=repo_path,
        vulnerabilities=vulnerabilities,
        components=components
    )
    if remediations:
        audit_logger.record_event(
            event_type="REMEDIATION_PLANNED",
            repository=repo_name,
            commit_sha=commit_sha,
            details=f"Constructed {len(remediations)} verified safe upgrade proposals with manifest diffs"
        )

    # Severity counts
    vulns_by_sev = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for v in vulnerabilities:
        sev = v.severity.upper()
        if sev in vulns_by_sev:
            vulns_by_sev[sev] += 1

    result = AnalysisResult(
        id=analysis_id,
        repo_url=request.repo_url,
        repo_name=repo_name,
        commit_sha=commit_sha,
        analyzed_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        status="completed",
        stage="Analysis Complete",
        progress_percent=100,
        total_components=len(components),
        vulnerabilities_by_severity=vulns_by_sev,
        critical_findings_count=vulns_by_sev["CRITICAL"],
        secret_findings_count=len(secrets),
        suspicious_dependency_count=sum(1 for h in health_findings if h.is_suspicious),
        risk_overview=risk_overview,
        components=components,
        vulnerabilities=vulnerabilities,
        secrets=secrets,
        health_findings=health_findings,
        remediations=remediations,
        audit_logs=audit_logger.get_logs()
    )

    ANALYSES_STORE[analysis_id] = result
    return result

@router.get("/analyses/{analysis_id}", response_model=AnalysisResult)
def get_analysis(analysis_id: str):
    """Retrieves full analysis results by ID."""
    if analysis_id not in ANALYSES_STORE:
        raise HTTPException(status_code=404, detail="Analysis not found")
    result = ANALYSES_STORE[analysis_id]
    # Update latest audit logs
    result.audit_logs = audit_logger.get_logs()
    return result

@router.get("/analyses/{analysis_id}/sbom")
def get_sbom(
    analysis_id: str,
    format: str = Query("cyclonedx", pattern="^(cyclonedx|spdx)$")
):
    """
    Exports the Software Bill of Materials (SBOM) in machine-readable CycloneDX 1.5 JSON or SPDX 2.3 JSON.
    """
    if analysis_id not in ANALYSES_STORE:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis = ANALYSES_STORE[analysis_id]
    if format == "cyclonedx":
        bom_data = SBOMService.generate_cyclonedx_json(
            repo_name=analysis.repo_name,
            commit_sha=analysis.commit_sha,
            components=analysis.components
        )
        return Response(
            content=json.dumps(bom_data, indent=2),
            media_type="application/vnd.cyclonedx+json",
            headers={"Content-Disposition": f'attachment; filename="sbom-{analysis.repo_name}-cyclonedx.json"'}
        )
    else:
        spdx_data = SBOMService.generate_spdx_json(
            repo_name=analysis.repo_name,
            commit_sha=analysis.commit_sha,
            components=analysis.components
        )
        return Response(
            content=json.dumps(spdx_data, indent=2),
            media_type="application/spdx+json",
            headers={"Content-Disposition": f'attachment; filename="sbom-{analysis.repo_name}-spdx.json"'}
        )

@router.get("/analyses/{analysis_id}/findings", response_model=List[VulnerabilityFinding])
def get_findings(
    analysis_id: str,
    severity: Optional[str] = None,
    ecosystem: Optional[str] = None,
    search: Optional[str] = None
):
    """Retrieves filtered vulnerability findings."""
    if analysis_id not in ANALYSES_STORE:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    findings = ANALYSES_STORE[analysis_id].vulnerabilities
    if severity:
        findings = [f for f in findings if f.severity.upper() == severity.upper()]
    if ecosystem:
        findings = [f for f in findings if f.ecosystem.lower() == ecosystem.lower()]
    if search:
        s = search.lower()
        findings = [
            f for f in findings
            if s in f.id.lower() or s in f.package.lower() or any(s in a.lower() for a in f.aliases)
        ]
    return findings

@router.get("/analyses/{analysis_id}/dependencies", response_model=List[Component])
def get_dependencies(
    analysis_id: str,
    ecosystem: Optional[str] = None,
    direct_only: bool = False,
    search: Optional[str] = None
):
    """Retrieves component dependency inventory with filters."""
    if analysis_id not in ANALYSES_STORE:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    comps = ANALYSES_STORE[analysis_id].components
    if ecosystem:
        comps = [c for c in comps if c.ecosystem.lower() == ecosystem.lower()]
    if direct_only:
        comps = [c for c in comps if c.direct]
    if search:
        s = search.lower()
        comps = [c for c in comps if s in c.name.lower() or s in c.version.lower()]
    return comps

@router.post("/analyses/{analysis_id}/draft-pr", response_model=DraftPRResponse)
def create_draft_pull_request(request: DraftPRRequest):
    """
    Submits a human-reviewed DRAFT pull request with proposed remediation.
    NON-NEGOTIABLE SAFETY: NEVER MERGES PULL REQUESTS.
    """
    if request.analysis_id not in ANALYSES_STORE:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    analysis = ANALYSES_STORE[request.analysis_id]
    proposal = next((p for p in analysis.remediations if p.id == request.remediation_id), None)
    if not proposal:
        raise HTTPException(status_code=404, detail="Remediation proposal not found")

    if not request.user_confirmed:
        raise HTTPException(status_code=400, detail="Explicit user confirmation is mandatory before creating a draft PR.")

    resp = GitHubService.create_draft_pull_request(
        repo_url=analysis.repo_url,
        proposal=proposal,
        request=request
    )

    if resp.success:
        audit_logger.record_event(
            event_type="DRAFT_PULL_REQUEST_CREATED",
            repository=analysis.repo_name,
            commit_sha=analysis.commit_sha,
            details=f"Opened DRAFT pull request #{resp.pr_number or 'preview'} on branch '{resp.branch_name}' ({resp.draft_status}): '{resp.title}' at {resp.pr_url}. Action verified as DRAFT only.",
            actor="Human Reviewer"
        )
    else:
        audit_logger.record_event(
            event_type="DRAFT_PULL_REQUEST_FAILED",
            repository=analysis.repo_name,
            commit_sha=analysis.commit_sha,
            details=f"Draft pull request creation failed for '{resp.branch_name}': {resp.message}",
            actor="Human Reviewer"
        )

    return resp

@router.get("/analyses/{analysis_id}/audit", response_model=List[AuditEntry])
def get_audit_trail(analysis_id: str):
    """Retrieves immutable audit trail with cryptographic integrity hashes."""
    if analysis_id not in ANALYSES_STORE:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return audit_logger.get_logs()

@router.post("/debug/analyze", response_model=CodeDebugResponse)
def analyze_code_snippet(request: CodeDebugRequest):
    """
    Analyzes a source code snippet using the trained archetype classifier
    and performs validated defect localization and fix generation.
    Strictly static analysis; no user code is executed.
    """
    try:
        return DebugService.analyze_code(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"ML debugging engine unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

