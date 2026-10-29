export interface Component {
  name: string;
  version: string;
  ecosystem: string;
  purl: string;
  direct: boolean;
  license: string;
  manifest_path: string;
  reachability: 'reachable' | 'not_reachable' | 'unknown';
  vulnerability_count: number;
  risk_score: number;
  dependencies: string[];
}

export interface VulnerabilityFinding {
  id: string;
  aliases: string[];
  package: string;
  ecosystem: string;
  affected_version: string;
  fixed_version?: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  cvss_score?: number;
  epss_probability?: number;
  cisa_kev: boolean;
  affected_range: string;
  source_links: string[];
  dependency_path: string[];
  reachability: string;
  recommended_action: string;
  explanation: string;
  confidence: string;
  confidence_reason: string;
}

export interface SecretFinding {
  secret_type: string;
  file_path: string;
  line_number?: number;
  commit_sha?: string;
  detection_source: string;
  confidence: string;
  masked_value: string;
  remediation_instructions: string;
}

export interface DependencyHealthFinding {
  package: string;
  ecosystem: string;
  health_score: number;
  is_suspicious: boolean;
  suspicious_reasons: string[];
  signals: Record<string, any>;
  maintenance_status: string;
}

export interface RemediationProposal {
  id: string;
  package: string;
  ecosystem: string;
  current_version: string;
  proposed_version: string;
  reason: string;
  advisories_resolved: string[];
  compatibility_concerns: string[];
  breaking_change_warning: boolean;
  recommended_test_command: string;
  confidence: string;
  manifest_path: string;
  original_content: string;
  modified_content: string;
  diff: string;
  verification_status: string;
}

export interface DraftPRRequest {
  analysis_id: string;
  remediation_id: string;
  base_branch: string;
  proposed_branch?: string;
  pr_title: string;
  pr_body: string;
  user_confirmed: boolean;
}

export interface DraftPRResponse {
  success: boolean;
  draft_status: string;
  pr_url?: string;
  branch_name: string;
  title: string;
  message: string;
  safety_notice: string;
}

export interface AuditEntry {
  timestamp: string;
  event_type: string;
  repository: string;
  commit_sha: string;
  details: string;
  actor: string;
  integrity_hash: string;
}

export interface RiskOverview {
  score: number;
  label: 'Critical' | 'High' | 'Medium' | 'Low';
  breakdown: Record<string, number>;
  summary_explanation: string;
}

export interface AnalysisResult {
  id: string;
  repo_url: string;
  repo_name: string;
  commit_sha: string;
  analyzed_at: string;
  status: string;
  stage: string;
  progress_percent: number;
  error_message?: string;
  
  total_components: number;
  vulnerabilities_by_severity: Record<string, number>;
  critical_findings_count: number;
  secret_findings_count: number;
  suspicious_dependency_count: number;
  
  risk_overview: RiskOverview;
  components: Component[];
  vulnerabilities: VulnerabilityFinding[];
  secrets: SecretFinding[];
  health_findings: DependencyHealthFinding[];
  remediations: RemediationProposal[];
  audit_logs: AuditEntry[];
}

export interface DemoRepositoryInfo {
  id: string;
  name: string;
  url: string;
  ecosystem: string;
  description: string;
  expected_findings: string;
}

export const ECOSYSTEM_LIST = ['pypi', 'npm', 'golang', 'maven'];

