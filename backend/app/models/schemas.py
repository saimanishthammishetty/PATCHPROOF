from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

class AnalysisRequest(BaseModel):
    repo_url: str = Field(..., description="Target repository URL (e.g. https://github.com/owner/repo or fixture://vulnerable-python)")
    branch: Optional[str] = Field(None, description="Optional branch or commit SHA to pin analysis")
    run_secret_scan: bool = True
    run_health_check: bool = True

class Component(BaseModel):
    name: str
    version: str
    ecosystem: str # pypi, npm, maven, golang
    purl: str
    direct: bool = True
    license: Optional[str] = "Unknown"
    manifest_path: str
    reachability: str = "unknown" # reachable, not_reachable, unknown
    vulnerability_count: int = 0
    risk_score: float = 0.0
    dependencies: List[str] = Field(default_factory=list)
    scope: str = "production" # production, development, test, fixture

class VulnerabilityFinding(BaseModel):
    id: str # GHSA-..., CVE-...
    aliases: List[str] = Field(default_factory=list)
    package: str
    ecosystem: str
    affected_version: str
    fixed_version: Optional[str] = None
    severity: str # CRITICAL, HIGH, MEDIUM, LOW
    cvss_score: Optional[float] = None
    epss_probability: Optional[float] = None
    cisa_kev: bool = False
    affected_range: str = ""
    source_links: List[str] = Field(default_factory=list)
    dependency_path: List[str] = Field(default_factory=list)
    reachability: str = "unknown" # reachable, not_reachable, unknown
    recommended_action: str
    explanation: str
    confidence: str # High, Medium, Low
    confidence_reason: str = ""
    scope: str = "production" # production, development, test, fixture

class SecretFinding(BaseModel):
    secret_type: str
    file_path: str
    line_number: Optional[int] = None
    commit_sha: Optional[str] = None
    detection_source: str = "Regex & Entropy Pattern Engine"
    confidence: str = "High"
    masked_value: str
    remediation_instructions: str
    is_synthetic: bool = False
    synthetic_reason: Optional[str] = None
    scope: str = "production" # production, development, test, documentation

class DependencyHealthFinding(BaseModel):
    package: str
    ecosystem: str
    health_score: float = 10.0 # 0-10
    is_suspicious: bool = False
    suspicious_reasons: List[str] = Field(default_factory=list)
    signals: Dict[str, Any] = Field(default_factory=dict)
    maintenance_status: str = "active"

class RemediationProposal(BaseModel):
    id: str
    package: str
    ecosystem: str
    current_version: str
    proposed_version: str
    reason: str
    advisories_resolved: List[str] = Field(default_factory=list)
    compatibility_concerns: List[str] = Field(default_factory=list)
    breaking_change_warning: bool = False
    recommended_test_command: str
    confidence: str # High, Medium, Low
    manifest_path: str
    original_content: str
    modified_content: str
    diff: str
    manifest_diff: Optional[str] = None  # Alias for backward compatibility
    verification_status: str # "Verified compatible", "Tests recommended", "No verified remediation found"

class DraftPRRequest(BaseModel):
    analysis_id: str
    remediation_id: str
    base_branch: str = "main"
    proposed_branch: Optional[str] = None
    pr_title: str
    pr_body: str = Field(default="", description="Optional human description or automated summary")
    user_confirmed: bool = Field(..., description="Explicit human authorization confirmation")

class DraftPRResponse(BaseModel):
    success: bool
    draft_status: str = "DRAFT"
    pr_url: Optional[str] = None
    branch_name: str
    title: str
    message: str
    safety_notice: str = "PATCHPROOF creates draft pull requests for human review only and will never automatically merge changes."

class AuditEntry(BaseModel):
    timestamp: str
    event_type: str
    repository: str
    commit_sha: str
    details: str
    actor: str = "User"
    integrity_hash: str

class RiskOverview(BaseModel):
    score: float # 0 - 100 (Total repository composite risk)
    label: str # Critical, High, Medium, Low
    production_score: float = 0.0 # 0 - 100 (Isolated production scope risk)
    production_label: str = "Low" # Critical, High, Medium, Low
    breakdown: Dict[str, Any]
    summary_explanation: str

class AnalysisResult(BaseModel):
    id: str
    repo_url: str
    repo_name: str
    commit_sha: str
    analyzed_at: str
    status: str # queued, running, completed, failed
    stage: str
    progress_percent: int = 0
    error_message: Optional[str] = None
    
    total_components: int = 0
    vulnerabilities_by_severity: Dict[str, int] = Field(default_factory=dict)
    critical_findings_count: int = 0
    secret_findings_count: int = 0
    suspicious_dependency_count: int = 0
    
    risk_overview: RiskOverview
    components: List[Component] = Field(default_factory=list)
    vulnerabilities: List[VulnerabilityFinding] = Field(default_factory=list)
    secrets: List[SecretFinding] = Field(default_factory=list)
    health_findings: List[DependencyHealthFinding] = Field(default_factory=list)
    remediations: List[RemediationProposal] = Field(default_factory=list)
    audit_logs: List[AuditEntry] = Field(default_factory=list)

class DemoRepositoryInfo(BaseModel):
    id: str
    name: str
    url: str
    ecosystem: str
    description: str
    expected_findings: str

class CodeDebugRequest(BaseModel):
    code: str = Field(..., description="Source code snippet to analyze")
    language: str = Field(..., description="Programming language (e.g. python, javascript, c, java, go)")

class CodeDebugResponse(BaseModel):
    issue_detected: bool
    predicted_category: str
    category_label: str
    confidence_score: float
    severity: str
    faulty_line_number: Optional[int] = None
    faulty_line_content: Optional[str] = None
    suggested_fix: Optional[str] = None
    diff: Optional[str] = None
    explanation: str
    limitations_notice: str
    supported_languages: List[str] = Field(default_factory=lambda: ["python", "javascript", "c", "cpp", "java", "go", "typescript"])

    # Backward-compatible integration fields
    detected_archetype: Optional[str] = None
    confidence: Optional[float] = None
    proposed_fixes: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_compatibility_fields(self) -> "CodeDebugResponse":
        if self.detected_archetype is None:
            self.detected_archetype = self.predicted_category
        if self.confidence is None:
            self.confidence = self.confidence_score
        if not self.proposed_fixes and self.suggested_fix:
            self.proposed_fixes = [self.suggested_fix]
        return self


