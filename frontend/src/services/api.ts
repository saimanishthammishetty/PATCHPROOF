import type { 
  AnalysisResult, DemoRepositoryInfo, DraftPRRequest, 
  DraftPRResponse, AuditEntry, CodeDebugResponse 
} from '../types';

const API_BASE = '/api';

export async function fetchDemos(): Promise<DemoRepositoryInfo[]> {
  const res = await fetch(`${API_BASE}/demos`);
  if (!res.ok) throw new Error('Failed to load demo repositories');
  return res.json();
}

export async function startAnalysis(repoUrl: string, branch?: string): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/analyses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      repo_url: repoUrl,
      branch: branch || undefined,
      run_secret_scan: true,
      run_health_check: true
    })
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Analysis request failed');
  }
  
  return res.json();
}

export async function getAnalysis(id: string): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/analyses/${id}`);
  if (!res.ok) throw new Error('Failed to fetch analysis');
  return res.json();
}

export async function downloadSBOM(analysisId: string, format: 'cyclonedx' | 'spdx'): Promise<void> {
  const res = await fetch(`${API_BASE}/analyses/${analysisId}/sbom?format=${format}`);
  if (!res.ok) throw new Error(`Failed to export ${format} SBOM`);
  
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `sbom-${analysisId}-${format}.json`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export async function submitDraftPR(request: DraftPRRequest): Promise<DraftPRResponse> {
  const res = await fetch(`${API_BASE}/analyses/${request.analysis_id}/draft-pr`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create draft PR');
  }

  return res.json();
}

export async function getAuditLogs(analysisId: string): Promise<AuditEntry[]> {
  const res = await fetch(`${API_BASE}/analyses/${analysisId}/audit`);
  if (!res.ok) throw new Error('Failed to load audit trail');
  return res.json();
}

export async function analyzeCodeSnippet(code: string, language: string): Promise<CodeDebugResponse> {
  const res = await fetch(`${API_BASE}/debug/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, language })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Code debugging analysis failed');
  }

  return res.json();
}

